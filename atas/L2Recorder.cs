// ATAS.DataFeedsCore is deliberately NOT imported: it declares its own
// TradeDirection and MarketDataType alongside the ones in ATAS.Indicators,
// and importing both makes every use of those names ambiguous (CS0104).
// MarketDataArg comes from ATAS.Indicators, so its enums are the right ones.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Threading;

using ATAS.Indicators;

namespace Claude1.Recorders
{
    /// <summary>
    /// Writes Level 2 depth snapshots and aggressor-tagged tape to CSV.
    ///
    ///     L2_{symbol}_{yyyyMMdd}.csv     depth ladder, throttled snapshots
    ///     TAPE_{symbol}_{yyyyMMdd}.csv   every trade, with aggressor side
    ///     _status.txt                    what this recorder is actually doing
    ///
    /// The status file is the point of this version. An earlier build swallowed
    /// every exception and only created the data files from inside the market
    /// data handlers, so when nothing arrived there was no output at all and no
    /// way to tell whether the handlers were silent, the writes were failing, or
    /// the indicator was not running. _status.txt is written from OnCalculate,
    /// which always runs, and reports the counters and the last error.
    ///
    /// Reading it:
    ///   trades and depth both 0  -> the platform is sending neither; in Market
    ///                               Replay this means the replay mode has no
    ///                               tick or DOM data (use Ticks + DOM)
    ///   trades above 0, rows 0   -> writing is failing; "last error" says why
    ///   file does not exist      -> the indicator is not on the chart, or
    ///                               cannot create the output folder at all
    /// </summary>
    [DisplayName("L2 Recorder (CSV)")]
    public partial class L2Recorder : Indicator
    {
        /// <summary>
        /// Bumped on every change. It is printed into _status.txt so a stale DLL
        /// left behind by a failed build is visible rather than mistaken for the
        /// current one.
        /// </summary>
        private const string BuildTag = "2026-09-16.p";

        private readonly object _sync = new object();

        private StreamWriter _depthWriter;
        private StreamWriter _tapeWriter;
        private StreamWriter _cumWriter;
        private StreamWriter _bboWriter;

        // Per-stream sequence numbers, written as the first column of every
        // data row. A recording can then prove its own completeness: the
        // sequence is dense by construction, so any gap in a file is a row
        // that was lost after this process wrote it, and no gap means none
        // were. Without this a truncated or partially-copied file is
        // indistinguishable from a quiet market, which is the position every
        // recording so far has been in.
        private long _seqDepth, _seqTape, _seqCum, _seqBbo, _seqMbo;

        // Received / written / rejected, per stream. _trades and _depthEvents
        // count what the platform handed us; these count what happened to it.
        // The difference is the only thing that can distinguish "the market
        // was quiet" from "we threw it away".
        private long _tapeWritten, _depthWritten, _bboEvents, _bboWritten;
        private long _depthThrottled;
#pragma warning disable 0649   // assigned only in the optional ByOrder part
        private long _mboEvents, _mboWritten;
#pragma warning restore 0649
#pragma warning disable 0649   // assigned only in the optional Cumulative part
        private long _cumTrades;
#pragma warning restore 0649
        private string _openDate = "";
        private DateTime _lastSnapshot = DateTime.MinValue;
        private DateTime _lastStatus = DateTime.MinValue;
        private int _pending;

        private long _calcs, _trades, _depthEvents, _rows;
        private string _lastError = "(none)";
        private string _files = "(none yet)";

        private string _resolved;
        private string _folderNotes = "";

        // Last written resting size per "side|price", so an unchanged level can
        // be skipped. _seen and _gone are reused across snapshots rather than
        // reallocated: this runs on every book update, thousands of times a
        // minute, and the garbage would be the dominant cost.
        private readonly Dictionary<string, decimal> _book =
            new Dictionary<string, decimal>();
        private readonly HashSet<string> _seen = new HashSet<string>();
        private readonly List<string> _gone = new List<string>();
        private DateTime _lastKeyframe = DateTime.MinValue;
        private DateTime _lastData = DateTime.MinValue;
        private Timer _idleTimer;
        private string _pathDate = "";
        private string _dPath, _tPath, _bPath;
        private long _skippedOutOfSession;

        // The actual clock on the data, recorded before any session gate sees
        // it. A run once discarded 969 of 969 depth updates as "off-session"
        // and wrote nothing, and the status file could not say why because it
        // never reported what time the data claimed to be. Now it can.
        private DateTime _dataFirst = DateTime.MinValue;
        private DateTime _dataLast = DateTime.MinValue;
        private long _inWindow, _outWindow;

        private void NoteDataTime(DateTime t)
        {
            if (_dataFirst == DateTime.MinValue || t < _dataFirst)
                _dataFirst = t;
            if (t > _dataLast)
                _dataLast = t;
            if (InSession(t))
                _inWindow++;
            else
                _outWindow++;
        }

        // The price grid the data actually uses.
        //
        // Every recording so far prints on whole multiples of 5.00 -- tape,
        // cumulative trades and the depth ladder alike, with level 0 and level
        // 1 of the book five points apart. NQ trades in 0.25, so the feed is
        // delivering prices twenty steps coarser than the instrument, and a
        // footprint drawn on it is not a footprint: one row of the ladder
        // holds twenty real prices, which is the whole quantity a cluster
        // chart exists to separate.
        //
        // That was found in the data months after it started being recorded,
        // because nothing ever checked. This checks: the smallest non-zero gap
        // between consecutive distinct prices is tracked as the data arrives
        // and reported beside whatever the platform SAYS the step is. If the
        // two disagree, the status file says so in as many words.
        private DateTime _lastBboWrite = DateTime.MinValue;

        private decimal _lastSeenPrice;
        private decimal _minGap;
        private long _priceSamples;

        private void NotePrice(decimal p)
        {
            if (p <= 0m)
                return;
            _priceSamples++;
            if (_lastSeenPrice > 0m)
            {
                var gap = Math.Abs(p - _lastSeenPrice);
                if (gap > 0m && (_minGap == 0m || gap < _minGap))
                    _minGap = gap;
            }
            _lastSeenPrice = p;
        }

        /// <summary>What the platform says the price step is, by any name it
        /// might use. Reflected rather than named directly because the
        /// property differs between ATAS versions and a wrong guess would not
        /// compile.</summary>
        private string DescribeTickSize()
        {
            var sb = new StringBuilder();
            try
            {
                var info = (object)InstrumentInfo;
                if (info == null)
                    return "  InstrumentInfo is null; no step reported\n";
                foreach (var p in info.GetType().GetProperties(
                             BindingFlags.Instance | BindingFlags.Public))
                {
                    var n = p.Name;
                    if (n.IndexOf("Tick", StringComparison.OrdinalIgnoreCase) < 0 &&
                        n.IndexOf("Step", StringComparison.OrdinalIgnoreCase) < 0 &&
                        n.IndexOf("Precision", StringComparison.OrdinalIgnoreCase) < 0 &&
                        n.IndexOf("Decimal", StringComparison.OrdinalIgnoreCase) < 0)
                        continue;
                    object v;
                    try { v = p.GetValue(info); }
                    catch { continue; }
                    sb.AppendLine("  " + n + " = " +
                        Convert.ToString(v, CultureInfo.InvariantCulture));
                }
            }
            catch (Exception e)
            {
                sb.AppendLine("  could not read InstrumentInfo: " + e.Message);
            }
            return sb.Length == 0 ? "  no step-like property found\n" : sb.ToString();
        }

        private int _depthLevels = 50;
        private int _snapshotMs = 250;

        /// <summary>
        /// Defaults to the Desktop, not Documents. "Documents" is routinely
        /// redirected to OneDrive, so the literal path C:\Users\name\Documents
        /// may not be the folder this process actually writes into -- which is
        /// how an earlier build appeared to produce nothing at all. A folder
        /// appearing on the Desktop cannot be missed or looked for in the wrong
        /// place. If this one is not writable, ResolveFolder falls back.
        /// </summary>
        [DisplayName("Output folder")]
        public string OutputFolder { get; set; } =
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                "ATAS_Export");

        [DisplayName("Depth levels per side")]
        public int DepthLevels
        {
            get { return _depthLevels; }
            set { _depthLevels = value < 1 ? 1 : (value > 200 ? 200 : value); }
        }

        [DisplayName("Snapshot interval (ms)")]
        public int SnapshotMs
        {
            get { return _snapshotMs; }
            set { _snapshotMs = value < 50 ? 50 : value; }
        }

        [DisplayName("Record tape")]
        public bool RecordTape { get; set; } = true;

        /// <summary>
        /// Order book depth. DEFAULT CHANGED TO OFF, and this is a judgement
        /// call rather than a bug fix -- depth recording works.
        ///
        /// The reason is what the two streams have returned. Depth is 223 MB of
        /// the captured data against the tape's 45 MB, five times the disk for
        /// the smaller half of the archive, and nothing tested on it has
        /// produced a finding: book imbalance was flat, and so was every
        /// pull-versus-fill measure. Meanwhile every question still open needs
        /// MORE SESSIONS of tape -- the gap-plus-flow split rests on six of
        /// them and wants roughly forty.
        ///
        /// Off, a session is small enough to record indefinitely without
        /// thinking about disk. Turn it back on for a specific depth question;
        /// do not leave it on by default to keep options open, because the cost
        /// is paid every session and the option has not been worth anything
        /// yet.
        /// </summary>
        [DisplayName("Record depth")]
        public bool RecordDepth { get; set; } = false;

        /// <summary>Record the market-by-order event stream when the feed
        /// supplies one. Costs nothing when it does not: the callback simply
        /// never fires and the status file reports zero, which is itself the
        /// answer to whether this route carries order-by-order data.</summary>
        [DisplayName("Record market by order")]
        public bool RecordByOrder { get; set; } = true;

        /// <summary>Write one row per individual fill of each aggressive
        /// order, alongside the order row. This is the shape of a sweep --
        /// how much went at each level and in what order -- which the
        /// first-price/last-price/count summary destroys. Roughly doubles the
        /// cumulative file.</summary>
        [DisplayName("Record individual fills")]
        public bool RecordFills { get; set; } = true;

        /// <summary>Write a per-row sequence number on the tape and depth
        /// streams.
        ///
        /// Off by default, and the reason is measured rather than assumed. On
        /// 18 June the column cost 6.2 MB of a 13.3 MB depth file -- the most
        /// expensive column in the recording -- because a dense counter is
        /// unique on every row and compresses badly.
        ///
        /// It also buys nothing that the row COUNT does not. The count is
        /// written to the status file and bundled with the data, so a
        /// truncated or partially copied file is detected either way. A
        /// per-row sequence localises the loss as well, which matters only if
        /// rows can go missing from the middle of a file -- and gzip fails
        /// loudly on corruption rather than silently dropping a line.
        ///
        /// The cumulative stream keeps its sequence regardless: there it is
        /// not redundant, because parent_seq is how a fill is joined to its
        /// order.</summary>
        [DisplayName("Write per-row sequence numbers")]
        public bool WriteSequence { get; set; } = false;

        /// <summary>Throttle the best bid/offer stream, in milliseconds. Zero
        /// records every change.
        ///
        /// Unthrottled is the right default and the size is genuinely unknown:
        /// it cannot be estimated from any existing recording, because the
        /// 250 ms depth poll aliases the quote badly -- 88% of consecutive
        /// samples differ, which means the true rate is far above four a
        /// second but says nothing about how far. Measure it on the first
        /// session and set this if it is too large.</summary>
        [DisplayName("BBO throttle ms (0 = every change)")]
        public int BboMs { get; set; } = 0;

        /// <summary>
        /// Record only the cash session. The recorder writes the ATAS platform
        /// clock, which on this install is UTC, so RTH is 13:30-20:00 there
        /// rather than 09:30-16:00. Overnight was two thirds of the first
        /// recording and none of it is analysed.
        /// </summary>
        [DisplayName("RTH only")]
        public bool RthOnly { get; set; } = true;

        /// <summary>
        /// Record the tape around the clock even when depth is restricted to
        /// the cash session. The overnight session sets levels that are traded
        /// during RTH -- the overnight high and low above all -- and those have
        /// never been testable here because only RTH was ever recorded. The
        /// tape is small enough that keeping all of it is nearly free, while
        /// overnight depth is bulky and will not be traded.
        /// </summary>
        [DisplayName("Record tape around the clock")]
        public bool TapeAllHours { get; set; } = true;

        [DisplayName("RTH start hour (platform clock)")]
        public int RthStartHour { get; set; } = 13;

        [DisplayName("RTH start minute")]
        public int RthStartMinute { get; set; } = 30;

        [DisplayName("RTH end hour (platform clock)")]
        public int RthEndHour { get; set; } = 20;

        [DisplayName("RTH end minute")]
        public int RthEndMinute { get; set; } = 0;

        /// <summary>
        /// Write a depth row only when that price's resting size actually
        /// changed. In the first recording, consecutive snapshots were
        /// byte-identical: twenty rows per snapshot, most of them repeating the
        /// previous twenty. A full ladder is still written every
        /// KeyframeSeconds so the book can be rebuilt from any point without
        /// replaying the file from the start.
        /// </summary>
        [DisplayName("Only write changed levels")]
        public bool ChangesOnly { get; set; } = true;

        [DisplayName("Full ladder every N seconds")]
        public int KeyframeSeconds { get; set; } = 60;

        /// <summary>
        /// Write .csv.gz instead of .csv. A one-tick recording is genuinely
        /// large -- 375 MB for a single day -- because at one tick the top ten
        /// levels span 2.5 points, so price walks the whole ladder constantly
        /// and skipping unchanged levels saves almost nothing. Compression is
        /// the thing that actually works on this shape of file: measured at 18x
        /// on real tape. Every reader used here opens .gz transparently.
        /// </summary>
        [DisplayName("Compress output (.csv.gz)")]
        public bool Gzip { get; set; } = true;

        /// <summary>
        /// Close the output files after this many seconds without data. When a
        /// replay finishes, the indicator stays on the chart and the handles
        /// stay open, so Windows refuses to move or delete the recordings until
        /// ATAS is shut down entirely. Releasing them when idle makes the
        /// folder tidyable straight after a run. The files reopen by themselves
        /// as soon as data resumes, appending to the same recording.
        /// </summary>
        /// <summary>
        /// Minutes of silence after which the day's files are folded into one
        /// zip and the originals deleted. Three files a day means a five-file
        /// upload carries a day and a half; one file a day carries five.
        ///
        /// This waits far longer than IdleCloseSeconds on purpose. Closing the
        /// writers happens on every quiet gap and they reopen on the next
        /// tick, so bundling on close would zip a half-recorded session. Ten
        /// minutes of nothing means the session is actually over.
        ///
        /// Set to 0 to keep the three separate files.
        /// </summary>
        [DisplayName("Bundle the day into one zip after (idle minutes)")]
        public int BundleMinutes { get; set; } = 10;

        [DisplayName("Release files after N idle seconds")]
        public int IdleCloseSeconds { get; set; } = 15;

        private bool InSession(DateTime t)
        {
            if (!RthOnly)
                return true;
            var mins = t.Hour * 60 + t.Minute;
            var from = RthStartHour * 60 + RthStartMinute;
            var to = RthEndHour * 60 + RthEndMinute;
            return from <= to ? (mins >= from && mins < to)
                              : (mins >= from || mins < to);
        }

        public L2Recorder()
        {
            try { DataSeries[0].IsHidden = true; } catch { }

            // Written here, before any market data exists, so the status file
            // appears the moment the indicator is added to a chart. That makes
            // "no status file" mean one thing only: it is not on the chart.
            WriteStatus(true);

            // Independent of the platform. OnCalculate stops being called when a
            // replay finishes, which is exactly the moment the files need to be
            // closed and their gzip tails written; three recordings arrived
            // truncated because nothing ran at that point.
            _idleTimer = new Timer(OnIdleTick, null, 5000, 5000);
        }

        // ------------------------------------------------------------------
        // where to write
        // ------------------------------------------------------------------
        private IEnumerable<string> Candidates()
        {
            yield return OutputFolder;
            yield return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                "ATAS_Export");
            yield return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                "ATAS_Export");
            yield return Path.Combine(Path.GetTempPath(), "ATAS_Export");
        }

        /// <summary>
        /// First candidate folder that can actually be created and written to.
        /// Creating a directory can succeed where writing then fails (policy,
        /// antivirus, a synced folder that is offline), so each candidate is
        /// probed with a real file before it is trusted.
        /// </summary>
        private string ResolveFolder()
        {
            if (_resolved != null)
                return _resolved;

            var tried = new List<string>();
            foreach (var c in Candidates())
            {
                if (string.IsNullOrEmpty(c))
                    continue;
                try
                {
                    Directory.CreateDirectory(c);
                    var probe = Path.Combine(c, "_probe.tmp");
                    File.WriteAllText(probe, "ok");
                    File.Delete(probe);
                    _resolved = c;
                    _folderNotes = tried.Count == 0
                        ? "(first choice)"
                        : "fell back, rejected: " + string.Join(" | ", tried);
                    return _resolved;
                }
                catch (Exception ex)
                {
                    tried.Add(c + " [" + ex.GetType().Name + "]");
                }
            }

            _folderNotes = "NOTHING WRITABLE, rejected: " + string.Join(" | ", tried);
            return null;
        }

        /// <summary>
        /// Report what this ATAS build actually exposes, rather than guessing.
        ///
        /// Two compile failures came from assuming names in the cumulative
        /// trade API: OnCumulativeTradesUpdate does not exist, and
        /// CumulativeTrade has no LastPrice. Both were avoidable. The installed
        /// assembly knows the answers, so it is asked once and the result goes
        /// into the status file. Reflection compiles whatever the API turns out
        /// to be, so this cannot itself break the build.
        /// </summary>
        private static string DescribeApi()
        {
            try
            {
                var sb = new StringBuilder();
                sb.AppendLine("overridable methods mentioning trade or depth:");

                Type cumType = null;
                var t = typeof(L2Recorder).BaseType;
                while (t != null)
                {
                    foreach (var m in t.GetMethods(BindingFlags.Instance |
                                                   BindingFlags.Public |
                                                   BindingFlags.NonPublic |
                                                   BindingFlags.DeclaredOnly))
                    {
                        if (!m.IsVirtual || m.IsFinal)
                            continue;
                        var n = m.Name;
                        if (n.IndexOf("Trade", StringComparison.OrdinalIgnoreCase) < 0 &&
                            n.IndexOf("Depth", StringComparison.OrdinalIgnoreCase) < 0 &&
                            n.IndexOf("Cumulative", StringComparison.OrdinalIgnoreCase) < 0)
                            continue;

                        var ps = m.GetParameters();
                        sb.Append("    ").Append(n).Append("(");
                        for (var i = 0; i < ps.Length; i++)
                        {
                            if (i > 0)
                                sb.Append(", ");
                            sb.Append(ps[i].ParameterType.Name);
                            if (cumType == null &&
                                ps[i].ParameterType.Name.IndexOf(
                                    "Cumulative", StringComparison.Ordinal) >= 0)
                                cumType = ps[i].ParameterType;
                        }
                        sb.AppendLine(")");
                    }
                    t = t.BaseType;
                }

                if (cumType != null)
                {
                    sb.AppendLine();
                    sb.AppendLine(cumType.Name + " properties:");
                    foreach (var pr in cumType.GetProperties(
                                 BindingFlags.Instance | BindingFlags.Public))
                        sb.AppendLine("    " + pr.PropertyType.Name + " " + pr.Name);
                }
                return sb.ToString();
            }
            catch (Exception ex)
            {
                return "api reflection failed: " + ex.Message;
            }
        }

        // ------------------------------------------------------------------
        // status
        // ------------------------------------------------------------------
        /// <summary>One reconciliation line. `seq` is the last sequence number
        /// issued, so it must equal `written`; if it does not, rows were
        /// written outside the counted path and the discrepancy is real.</summary>
        private static string Line(string name, long got, long wrote,
                                   long seq, long throttled)
        {
            var s = "  " + name.PadRight(14) +
                    "recv " + got.ToString().PadLeft(9) +
                    "   wrote " + wrote.ToString().PadLeft(9) +
                    "   seq " + seq.ToString().PadLeft(9);
            if (throttled > 0)
                s += "   throttled " + throttled;
            if (seq != wrote && seq > 0 && wrote > 0)
                s += "   *** seq and written disagree ***";
            return s;
        }

        private void WriteStatus(bool force)
        {
            var now = DateTime.Now;
            if (!force && (now - _lastStatus).TotalSeconds < 2)
                return;
            _lastStatus = now;

            try
            {
                var dir = ResolveFolder();
                if (dir == null)
                    return;

                var sb = new StringBuilder();
                sb.AppendLine("L2 Recorder status");
                sb.AppendLine("==================");
                sb.AppendLine("recorder version:   " + BuildTag);
                sb.AppendLine("updated:            " +
                    now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture));
                sb.AppendLine("instrument:         " + SymbolName());
                sb.AppendLine();
                sb.AppendLine("OnCalculate calls:  " + _calcs);
                sb.AppendLine();
                sb.AppendLine("---- per stream: received / written / rejected ----");
                sb.AppendLine("A recording can now prove its own completeness.");
                sb.AppendLine("Every data row carries a dense seq, so a gap in a");
                sb.AppendLine("file is a lost row and no gap means none were lost.");
                sb.AppendLine();
                sb.AppendLine(Line("tape", _trades, _tapeWritten, _seqTape, 0));
                sb.AppendLine(Line("depth", _depthEvents, _depthWritten,
                                   _seqDepth, _depthThrottled));
                sb.AppendLine(Line("best bid/ask", _bboEvents, _bboWritten,
                                   _seqBbo, 0));
                sb.AppendLine(Line("cumulative", _cumTrades, _seqCum,
                                   _seqCum, 0));
                sb.AppendLine(Line("by order", _mboEvents, _mboWritten,
                                   _seqMbo, 0));
                if (_cumTrades == 0)
                    sb.AppendLine("  cumulative trades are not being supplied");
                if (_mboEvents == 0)
                {
                    sb.AppendLine();
                    sb.AppendLine("  NO MARKET-BY-ORDER DATA ON THIS ROUTE.");
                    sb.AppendLine("  The callback exists in this ATAS build but has");
                    sb.AppendLine("  not fired. The feed is delivering aggregated");
                    sb.AppendLine("  depth only, so the ladder poll is the best");
                    sb.AppendLine("  available and add/change/remove is not");
                    sb.AppendLine("  obtainable. That is a feed fact, not a bug.");
                }
                if (_depthEvents > 0)
                    sb.AppendLine("  depth kept " +
                        (100.0 * (_depthEvents - _depthThrottled) /
                         _depthEvents).ToString("F1",
                             CultureInfo.InvariantCulture) +
                        "% of book updates at " + SnapshotMs + " ms throttle");
                sb.AppendLine();
                sb.AppendLine("rows written:       " + _rows);
                sb.AppendLine();
                sb.AppendLine("skipped, off-session " + _skippedOutOfSession);
                sb.AppendLine();
                sb.AppendLine("---- the clock on the incoming data ----");
                if (_dataFirst == DateTime.MinValue)
                {
                    sb.AppendLine("no market data has arrived at all.");
                }
                else
                {
                    sb.AppendLine("data timestamps run " +
                        _dataFirst.ToString("yyyy-MM-dd HH:mm:ss",
                                            CultureInfo.InvariantCulture) +
                        "  to  " +
                        _dataLast.ToString("yyyy-MM-dd HH:mm:ss",
                                           CultureInfo.InvariantCulture));
                    sb.AppendLine("session window is " +
                        RthStartHour.ToString("00") + ":" +
                        RthStartMinute.ToString("00") + " to " +
                        RthEndHour.ToString("00") + ":" +
                        RthEndMinute.ToString("00") +
                        "   inside " + _inWindow + ", outside " + _outWindow);
                    if (_inWindow == 0 && _outWindow > 0)
                    {
                        sb.AppendLine();
                        sb.AppendLine("*** EVERY UPDATE FELL OUTSIDE THE WINDOW ***");
                        sb.AppendLine("Nothing will be written while that is true.");
                        sb.AppendLine("Either the replay is positioned outside the");
                        sb.AppendLine("cash session, or this platform's clock is not");
                        sb.AppendLine("the one the window assumes. Fix by either:");
                        sb.AppendLine("  - moving the replay into the cash session, or");
                        sb.AppendLine("  - setting RTH only = False to record everything,");
                        sb.AppendLine("    then telling Claude the times above.");
                    }
                }
                if (_trades == 0 && _depthEvents > 0)
                {
                    sb.AppendLine();
                    sb.AppendLine("*** DEPTH IS ARRIVING BUT NO TRADES ***");
                    sb.AppendLine("The replay is supplying DOM only. Switch the");
                    sb.AppendLine("replay mode to Ticks + DOM; without ticks there");
                    sb.AppendLine("is no tape and no cumulative trades, which is");
                    sb.AppendLine("most of what the analysis needs.");
                }
                sb.AppendLine("----------------------------------------");
                sb.AppendLine();
                sb.AppendLine("---- the price grid ----");
                sb.AppendLine("platform says the step is:");
                sb.Append(DescribeTickSize());
                sb.AppendLine("smallest gap actually seen: " +
                    (_priceSamples == 0
                     ? "no prices yet"
                     : _minGap.ToString(CultureInfo.InvariantCulture) +
                       "   over " + _priceSamples + " prints"));
                if (_minGap >= 1m && _priceSamples > 5000)
                {
                    sb.AppendLine();
                    sb.AppendLine("*** THE FEED IS COARSER THAN THE INSTRUMENT ***");
                    sb.AppendLine("NQ trades in 0.25. Every price here is a whole");
                    sb.AppendLine("multiple of " + _minGap.ToString(CultureInfo.InvariantCulture)
                        + ", so roughly " + Math.Round(_minGap / 0.25m)
                        + " real prices are being");
                    sb.AppendLine("collapsed into one. Bars, CVD and levels survive");
                    sb.AppendLine("that; a footprint does not, because separating");
                    sb.AppendLine("prices is the only thing it does.");
                    sb.AppendLine("Check, in this order:");
                    sb.AppendLine("  - the chart's instrument settings, for a Step,");
                    sb.AppendLine("    Tick size or Price scale override");
                    sb.AppendLine("  - whether the chart is a cluster/range type");
                    sb.AppendLine("    built on an aggregated step rather than ticks");
                    sb.AppendLine("  - the data source: a delayed or aggregated feed");
                    sb.AppendLine("    publishes a coarse grid and no setting fixes it");
                }
                sb.AppendLine("------------------------");
                sb.AppendLine();
                if (_dataFirst != DateTime.MinValue)
                {
                    var span = (_dataLast - _dataFirst).TotalMinutes;
                    var expect = (RthEndHour * 60 + RthEndMinute) -
                                 (RthStartHour * 60 + RthStartMinute);
                    if (expect > 0)
                        sb.AppendLine("coverage of the window: " +
                            (100.0 * span / expect).ToString("F1",
                                CultureInfo.InvariantCulture) + "%  (" +
                            span.ToString("F0", CultureInfo.InvariantCulture) +
                            " of " + expect + " minutes)");
                }
                sb.AppendLine();
                sb.AppendLine("record tape:        " + RecordTape);
                sb.AppendLine("record by order:    " + RecordByOrder);
                sb.AppendLine("record fills:       " + RecordFills);
                sb.AppendLine("per-row sequence:   " + WriteSequence
                    + (WriteSequence ? "" : "  (row counts above are the proof)"));
                sb.AppendLine("bbo throttle:       " +
                    (BboMs > 0 ? BboMs + " ms" : "every change"));
                sb.AppendLine("compression:        gzip SmallestSize");
                sb.AppendLine("record depth:       " + RecordDepth);
                sb.AppendLine("tape all hours:     " + TapeAllHours);
                sb.AppendLine("depth RTH only:     " + RthOnly + "  ("
                    + RthStartHour.ToString("00") + ":"
                    + RthStartMinute.ToString("00") + " to "
                    + RthEndHour.ToString("00") + ":"
                    + RthEndMinute.ToString("00") + " platform clock)");
                sb.AppendLine("compressed:         " + Gzip);
                sb.AppendLine("files:              "
                    + (_depthWriter == null
                       ? "CLOSED, safe to move or delete"
                       : "open, writing"));
                sb.AppendLine("release when idle:  " + IdleCloseSeconds + "s");
                sb.AppendLine("changed levels only:" + ChangesOnly
                    + "  (full ladder every " + KeyframeSeconds + "s)");
                sb.AppendLine("requested folder:   " + OutputFolder);
                sb.AppendLine("WRITING HERE:       " + dir);
                sb.AppendLine("folder choice:      " + _folderNotes);
                sb.AppendLine("data files:         " + _files);
                sb.AppendLine("last error:         " + _lastError);
                sb.AppendLine();
                sb.AppendLine("---- platform API, for Claude ----");
                sb.Append(DescribeApi());
                sb.AppendLine("---------------------------------");
                sb.AppendLine();
                sb.AppendLine("If trades and depth updates are both 0, the platform is");
                sb.AppendLine("sending neither. In Market Replay, switch the replay mode");
                sb.AppendLine("to Ticks + DOM: the other modes carry no tick or depth");
                sb.AppendLine("data and there is nothing for this to record.");
                File.WriteAllText(Path.Combine(dir, "_status.txt"),
                                  sb.ToString(), Encoding.UTF8);
            }
            catch { /* if even this fails there is nowhere to report it */ }
        }

        // ------------------------------------------------------------------
        // files
        // ------------------------------------------------------------------
        private static string Clean(string s)
        {
            if (string.IsNullOrEmpty(s))
                return "UNKNOWN";
            foreach (var c in Path.GetInvalidFileNameChars())
                s = s.Replace(c, '_');
            return s;
        }

        private string SymbolName()
        {
            try
            {
                var info = InstrumentInfo;
                if (info != null && !string.IsNullOrEmpty(info.Instrument))
                    return info.Instrument;
            }
            catch { }
            return "UNKNOWN";
        }

        /// <summary>Opens (or rolls) the day's files. Caller must hold _sync.</summary>
        private void EnsureOpen(DateTime stamp)
        {
            var date = stamp.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
            if (date == _openDate && _depthWriter != null)
                return;

            CloseFiles();

            var dir = ResolveFolder();
            if (dir == null)
                throw new IOException("no writable output folder: " + _folderNotes);

            // Only choose a run number the first time this date is opened. A
            // reopen after an idle close must resume the same files, or every
            // idle gap would start a new run and split one recording.
            if (date != _pathDate || _dPath == null)
            {
                var sym = Clean(SymbolName());
                var ext = Gzip ? ".csv.gz" : ".csv";
                var run = NextRun(dir, sym, date, ext);
                _dPath = RunPath(dir, "L2_" + sym + "_" + date, run, ext);
                _tPath = RunPath(dir, "TAPE_" + sym + "_" + date, run, ext);
                _bPath = RunPath(dir, "BBO_" + sym + "_" + date, run, ext);
                _pathDate = date;
            }
            var dPath = _dPath;
            var tPath = _tPath;

            var dNew = !File.Exists(dPath);
            var tNew = !File.Exists(tPath);
            var bNew = !File.Exists(_bPath);

            _depthWriter = OpenWriter(dPath);
            _tapeWriter = OpenWriter(tPath);
            _bboWriter = OpenWriter(_bPath);
            _depthWriter.AutoFlush = false;
            _tapeWriter.AutoFlush = false;
            _bboWriter.AutoFlush = false;

            // Every stream leads with seq. The extra tape columns are fields
            // MarketDataArg has always carried and we have never written:
            // DataType distinguishes a trade print from anything else on the
            // same callback, OpenInterest is free, and the two exchange order
            // ids are the only identity the feed offers -- they are what makes
            // a trade joinable to the order that caused it.
            var sq = WriteSequence ? "seq," : "";
            if (dNew)
                _depthWriter.WriteLine(sq + "time,side,level,price,volume");
            if (tNew)
                _tapeWriter.WriteLine(
                    sq + "time,price,volume,aggressor,datatype,oi," +
                    "aggressor_order_id,order_id");
            if (bNew)
                _bboWriter.WriteLine(sq + "time,side,price,volume");

            _openDate = date;
            _files = Path.GetFileName(dPath) + " + " + Path.GetFileName(tPath)
                   + " + " + Path.GetFileName(_bPath);
        }

        private static string RunPath(string dir, string stem, int run,
                                      string ext)
        {
            return Path.Combine(dir, run <= 1 ? stem + ext
                                              : stem + "_run" + run + ext);
        }

        /// <summary>
        /// Replaying the same session twice with the indicator attached used to
        /// append the whole day to the existing file a second time, producing a
        /// file with every row present exactly twice and every resting size
        /// silently doubled. A second run now writes _run2 alongside rather
        /// than into the first, so nothing is lost and nothing is corrupted.
        /// </summary>
        private static int NextRun(string dir, string sym, string date,
                                   string ext)
        {
            for (var run = 1; run < 100; run++)
            {
                var d = RunPath(dir, "L2_" + sym + "_" + date, run, ext);
                var t = RunPath(dir, "TAPE_" + sym + "_" + date, run, ext);
                var b = RunPath(dir, "BBO_" + sym + "_" + date, run, ext);
                if (!File.Exists(d) && !File.Exists(t) && !File.Exists(b))
                    return run;
            }
            return 1;
        }

        /// <summary>
        /// Appending to a gzip file produces a multi-member archive, which is
        /// legal and which every gzip reader concatenates transparently, so a
        /// session resumed after a restart is still one readable file. The
        /// header is only written when the file is new, so no duplicate header
        /// row appears at a member boundary.
        /// </summary>
        private StreamWriter OpenWriter(string path)
        {
            if (!Gzip)
            {
                var plain = new FileStream(path, FileMode.Append,
                                           FileAccess.Write,
                                           FileShare.ReadWrite |
                                           FileShare.Delete);
                return new StreamWriter(plain, Encoding.UTF8);
            }

            var fs = new FileStream(path, FileMode.Append, FileAccess.Write,
                                    FileShare.ReadWrite | FileShare.Delete);
            var gz = new GZipStream(fs, CompressionLevel.SmallestSize, false);
            return new StreamWriter(gz, new UTF8Encoding(false));
        }

        /// <summary>
        /// Release the handles once data has stopped arriving. Caller holds
        /// _sync. Deliberately does not reset _openDate to a sentinel: the next
        /// datum reopens the same day's file in append mode and carries on.
        /// </summary>
        private void CloseIfIdle()
        {
            if (IdleCloseSeconds <= 0 || _depthWriter == null)
                return;
            if (_lastData == DateTime.MinValue)
                return;
            if ((DateTime.Now - _lastData).TotalSeconds < IdleCloseSeconds)
                return;
            CloseFiles();
        }

        /// <summary>
        /// Implemented in L2Recorder.Cumulative.cs. Writes the aggressive
        /// order still being accumulated, which is otherwise lost when the
        /// session ends. Both the declaration and the call vanish when that
        /// file is compiled out with -p:NoCumulative=true.
        /// </summary>
        partial void FlushPendingCumulative();

        /// <summary>
        /// Implemented in L2Recorder.Cumulative.cs. Adds the cumulative file to
        /// the bundle list. A partial method because _cPath lives in that file,
        /// and naming it directly here would break the -p:NoCumulative=true
        /// fallback build.
        /// </summary>
        partial void AddCumFile(List<string> paths);

        /// <summary>Implemented in L2Recorder.ByOrder.cs when that part is
        /// compiled in. A partial method with no implementation compiles to
        /// nothing, so the recorder works identically with the market-by-order
        /// stream removed.</summary>
        partial void AddByOrderFile(List<string> paths);
        partial void FlushByOrder();
        partial void CloseByOrder();

        private void CloseFiles()
        {
            FlushPendingCumulative();

            try { if (_depthWriter != null) { _depthWriter.Flush(); _depthWriter.Dispose(); } } catch { }
            try { if (_tapeWriter != null) { _tapeWriter.Flush(); _tapeWriter.Dispose(); } } catch { }
            try { if (_cumWriter != null) { _cumWriter.Flush(); _cumWriter.Dispose(); } } catch { }
            try { if (_bboWriter != null) { _bboWriter.Flush(); _bboWriter.Dispose(); } } catch { }
            CloseByOrder();
            _depthWriter = null;
            _tapeWriter = null;
            _bboWriter = null;
            _cumWriter = null;
            _openDate = "";
        }

        private string _bundledDate = "";

        /// <summary>
        /// Fold the day's outputs into one zip once recording has stopped.
        ///
        /// Entries are stored rather than deflated: the parts are already
        /// gzipped, so a second pass costs CPU and saves nothing. If anything
        /// here throws, the originals are left exactly where they are and the
        /// day is still complete -- the bundle is a convenience, never a step
        /// that data has to survive.
        /// </summary>
        private void BundleIfDone()
        {
            if (BundleMinutes <= 0 || _pathDate.Length == 0)
                return;
            if (_depthWriter != null || _tapeWriter != null || _cumWriter != null)
                return;
            if (_lastData == DateTime.MinValue)
                return;
            if ((DateTime.Now - _lastData).TotalMinutes < BundleMinutes)
                return;
            if (_bundledDate == _pathDate)
                return;

            try
            {
                var dir = ResolveFolder();
                if (dir == null)
                    return;

                var parts = new List<string>();
                if (_dPath != null) parts.Add(_dPath);
                if (_tPath != null) parts.Add(_tPath);
                if (_bPath != null) parts.Add(_bPath);
                AddCumFile(parts);
                AddByOrderFile(parts);
                // Provenance must travel with the data. The status file holds
                // the settings, the resolution and the per-stream counts, and
                // leaving it out of the bundle is why four months of
                // recordings could not say what they were recorded at.
                WriteStatus(true);
                var statusPath = Path.Combine(dir, "_status.txt");

                var zipPath = Path.Combine(
                    dir, Clean(SymbolName()) + "_" + _pathDate + ".zip");
                var packed = new List<string>();

                using (var zip = ZipFile.Open(zipPath,
                           File.Exists(zipPath) ? ZipArchiveMode.Update
                                                : ZipArchiveMode.Create))
                {
                    foreach (var src in parts)
                    {
                        if (src == null || !File.Exists(src))
                            continue;
                        var name = Path.GetFileName(src);
                        var entry = name;
                        // A session that resumes after a bundle writes a fresh
                        // run file; never overwrite an entry already holding
                        // earlier data for the same day.
                        var n = 2;
                        while (zip.GetEntry(entry) != null)
                        {
                            entry = Path.GetFileNameWithoutExtension(
                                        Path.GetFileNameWithoutExtension(name)) +
                                    "_part" + n + ".csv.gz";
                            n++;
                        }
                        zip.CreateEntryFromFile(src, entry,
                                                CompressionLevel.NoCompression);
                        packed.Add(src);
                    }

                    // The status file goes in by copy and is NOT added to
                    // `packed`, because everything in that list is deleted
                    // afterwards and this one is live -- the user reads it
                    // while the recorder runs. It is also named per date
                    // rather than deduplicated as a .csv.gz, which the loop
                    // above would otherwise do to it.
                    if (File.Exists(statusPath))
                    {
                        var sName = "_status_" + _pathDate + ".txt";
                        var m = 2;
                        while (zip.GetEntry(sName) != null)
                        {
                            sName = "_status_" + _pathDate + "_part" + m + ".txt";
                            m++;
                        }
                        try
                        {
                            zip.CreateEntryFromFile(statusPath, sName,
                                                    CompressionLevel.Optimal);
                        }
                        catch { }
                    }
                }

                foreach (var src in packed)
                {
                    try { File.Delete(src); } catch { }
                }

                _bundledDate = _pathDate;
                _pathDate = "";
                _dPath = null;
                _tPath = null;
                ClearCumPath();
                _files = "bundled " + packed.Count + " file(s) into " +
                         Path.GetFileName(zipPath);
            }
            catch (Exception ex)
            {
                _lastError = "bundle: " + ex.Message;
            }
        }

        partial void ClearCumPath();

        private void FlushIfDue(bool force)
        {
            if (!force && _pending < 2000)
                return;
            try { if (_depthWriter != null) _depthWriter.Flush(); } catch { }
            try { if (_tapeWriter != null) _tapeWriter.Flush(); } catch { }
            try { if (_cumWriter != null) _cumWriter.Flush(); } catch { }
            try { if (_bboWriter != null) _bboWriter.Flush(); } catch { }
            FlushByOrder();
            _pending = 0;
        }

        /// <summary>
        /// Writes one side of the ladder, skipping prices whose resting size is
        /// unchanged. Caller must hold _sync and must have cleared _seen.
        /// </summary>
        private void EmitSide(string stamp, string side,
                              List<MarketDataArg> levels, bool keyframe)
        {
            var n = Math.Min(DepthLevels, levels.Count);
            for (var i = 0; i < n; i++)
            {
                var price = levels[i].Price;
                var vol = levels[i].Volume;
                var key = side + "|" + Num(price);
                _seen.Add(key);

                if (ChangesOnly && !keyframe)
                {
                    decimal prev;
                    if (_book.TryGetValue(key, out prev) && prev == vol)
                        continue;
                }
                _book[key] = vol;

                _seqDepth++;
                _depthWriter.WriteLine(
                    Seq(_seqDepth) + stamp + "," + side + "," + i + "," +
                    Num(price) + "," + Num(vol));
                _rows++;
                _depthWritten++;
                _pending++;
            }
        }

        private static string Ts(DateTime t)
        {
            return t.ToString("yyyy-MM-dd HH:mm:ss.ffffff",
                              CultureInfo.InvariantCulture);
        }

        /// <summary>A nullable exchange id as a column: empty when absent.
        ///
        /// These are the only identity the feed offers on a print. On CME they
        /// may well be null for every row, in which case the columns cost a
        /// comma each and the status file says the count was zero -- which is
        /// itself the answer to whether they are usable.</summary>
        /// <summary>The sequence prefix, or nothing when sequences are off.
        /// The counter is maintained either way so the status file can
        /// reconcile it against the rows written.</summary>
        private string Seq(long n)
        {
            return WriteSequence
                ? n.ToString(CultureInfo.InvariantCulture) + ","
                : "";
        }

        private static string IdOf(long? id)
        {
            return id.HasValue
                ? id.Value.ToString(CultureInfo.InvariantCulture)
                : "";
        }

        /// <summary>The inside quote, as its own stream.
        ///
        /// The book snapshot is throttled to SnapshotMs and always will be --
        /// it is a whole ladder and re-reading it on every change would cost
        /// more than it returns. The touch is different: it is four numbers,
        /// it changes constantly, and every quote change between two snapshots
        /// was previously lost. This writes all of them, unthrottled, so the
        /// spread and the size at the touch are exact rather than sampled.
        /// </summary>
        protected override void OnBestBidAskChanged(MarketDataArg depth)
        {
            if (depth == null)
                return;
            _bboEvents++;
            if (!RecordDepth)
                return;
            NotePrice(depth.Price);
            var now = depth.Time;
            NoteDataTime(now);
            if (!InSession(now))
            {
                _skippedOutOfSession++;
                return;
            }
            lock (_sync)
            {
                if (BboMs > 0 &&
                    (now - _lastBboWrite).TotalMilliseconds < BboMs)
                    return;
                _lastBboWrite = now;
                try
                {
                    EnsureOpen(now);
                    _lastData = DateTime.Now;
                    var side = depth.DataType == MarketDataType.Bid ? "B"
                             : depth.DataType == MarketDataType.Ask ? "A"
                             : "?";
                    _seqBbo++;
                    _bboWriter.WriteLine(
                        Seq(_seqBbo) + Ts(now) + "," + side + "," +
                        Num(depth.Price) + "," + Num(depth.Volume));
                    _rows++;
                    _bboWritten++;
                    _pending++;
                    FlushIfDue(false);
                }
                catch (Exception ex)
                {
                    _lastError = "bbo: " + ex.Message;
                }
            }
        }

        private static string Num(decimal d)
        {
            return d.ToString(CultureInfo.InvariantCulture);
        }

        // ------------------------------------------------------------------
        // ATAS hooks
        // ------------------------------------------------------------------
        private void OnIdleTick(object state)
        {
            try
            {
                lock (_sync)
                {
                    FlushIfDue(true);
                    CloseIfIdle();
                    BundleIfDone();
                    WriteStatus(false);
                }
            }
            catch (Exception ex)
            {
                _lastError = "idle timer: " + ex.Message;
            }
        }

        protected override void OnCalculate(int bar, decimal value)
        {
            // Nothing is drawn. This always runs, so it carries the status file
            // and doubles as the flush heartbeat for a session that ends without
            // a clean shutdown.
            _calcs++;
            lock (_sync)
            {
                FlushIfDue(true);
                CloseIfIdle();
                WriteStatus(false);
            }
        }

        protected override void OnNewTrade(MarketDataArg arg)
        {
            if (arg == null)
                return;
            _trades++;
            NotePrice(arg.Price);
            if (!RecordTape)
                return;
            NoteDataTime(arg.Time);
            if (!TapeAllHours && !InSession(arg.Time))
            {
                _skippedOutOfSession++;
                return;
            }

            // Direction is the aggressor: Buy lifted the offer, Sell hit the bid.
            var side = arg.Direction == TradeDirection.Buy ? "B"
                     : arg.Direction == TradeDirection.Sell ? "S"
                     : "?";

            lock (_sync)
            {
                try
                {
                    EnsureOpen(arg.Time);
                    _lastData = DateTime.Now;
                    _seqTape++;
                    _tapeWriter.WriteLine(
                        Seq(_seqTape) + Ts(arg.Time) + "," +
                        Num(arg.Price) + "," + Num(arg.Volume) + "," + side +
                        "," + (int)arg.DataType + "," + Num(arg.OpenInterest) +
                        "," + IdOf(arg.AggressorExchangeOrderId) +
                        "," + IdOf(arg.ExchangeOrderId));
                    _rows++;
                    _tapeWritten++;
                    _pending++;
                    FlushIfDue(false);
                }
                catch (Exception ex)
                {
                    _lastError = "tape: " + ex.Message;
                }
            }
        }

        protected override void MarketDepthChanged(MarketDataArg arg)
        {
            if (arg == null)
                return;
            _depthEvents++;
            if (!RecordDepth)
                return;

            var now = arg.Time;
            NoteDataTime(now);
            if (!InSession(now))
            {
                _skippedOutOfSession++;
                return;
            }
            lock (_sync)
            {
                if ((now - _lastSnapshot).TotalMilliseconds < SnapshotMs)
                {
                    _depthThrottled++;
                    return;
                }
                _lastSnapshot = now;

                try
                {
                    EnsureOpen(now);
                    _lastData = DateTime.Now;

                    var snap = MarketDepthInfo.GetMarketDepthSnapshot();
                    if (snap == null)
                    {
                        _lastError = "depth: GetMarketDepthSnapshot returned null";
                        return;
                    }

                    // The snapshot arrives unordered; walk it once and keep the
                    // DepthLevels nearest the touch on each side.
                    var bids = new List<MarketDataArg>();
                    var asks = new List<MarketDataArg>();
                    foreach (var lvl in snap)
                    {
                        if (lvl == null || lvl.Volume <= 0)
                            continue;
                        if (lvl.DataType == MarketDataType.Bid)
                            bids.Add(lvl);
                        else if (lvl.DataType == MarketDataType.Ask)
                            asks.Add(lvl);
                    }

                    bids.Sort((a, b) => b.Price.CompareTo(a.Price));   // best bid first
                    asks.Sort((a, b) => a.Price.CompareTo(b.Price));   // best ask first

                    var stamp = Ts(now);
                    var keyframe = !ChangesOnly ||
                        (now - _lastKeyframe).TotalSeconds >= KeyframeSeconds;
                    if (keyframe)
                        _lastKeyframe = now;

                    _seen.Clear();
                    EmitSide(stamp, "B", bids, keyframe);
                    EmitSide(stamp, "A", asks, keyframe);

                    // A price that has left the top of the book must be written
                    // as zero, or a reconstruction keeps resting size that is no
                    // longer there -- the exact error the recording exists to
                    // avoid making by eye. This runs on keyframes too: a
                    // keyframe rewrites the ladder but says nothing about what
                    // has left it.
                    _gone.Clear();
                    foreach (var kv in _book)
                        if (!_seen.Contains(kv.Key))
                            _gone.Add(kv.Key);
                    foreach (var key in _gone)
                    {
                        _seqDepth++;
                        _depthWriter.WriteLine(
                            Seq(_seqDepth) + stamp + "," +
                            key.Substring(0, 1) + ",-1," +
                            key.Substring(2) + ",0");
                        _book.Remove(key);
                        _rows++;
                        _depthWritten++;
                        _pending++;
                    }

                    FlushIfDue(false);
                }
                catch (Exception ex)
                {
                    _lastError = "depth: " + ex.Message;
                }
            }
        }

        protected override void OnDispose()
        {
            try
            {
                if (_idleTimer != null)
                {
                    _idleTimer.Dispose();
                    _idleTimer = null;
                }
            }
            catch { }

            lock (_sync)
            {
                FlushIfDue(true);
                CloseFiles();
                WriteStatus(true);
            }
            base.OnDispose();
        }
    }
}
