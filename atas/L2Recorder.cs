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
        private const string BuildTag = "2026-09-16.n";

        private readonly object _sync = new object();

        private StreamWriter _depthWriter;
        private StreamWriter _tapeWriter;
        private StreamWriter _cumWriter;
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
        private string _dPath, _tPath;
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
                sb.AppendLine("trades received:    " + _trades);
                sb.AppendLine("aggressive orders:  " + _cumTrades
                    + (_cumTrades == 0
                       ? "  (cumulative trades not supplied)" : ""));
                sb.AppendLine("depth updates:      " + _depthEvents);
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
                sb.AppendLine("record tape:        " + RecordTape);
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
                _pathDate = date;
            }
            var dPath = _dPath;
            var tPath = _tPath;

            var dNew = !File.Exists(dPath);
            var tNew = !File.Exists(tPath);

            _depthWriter = OpenWriter(dPath);
            _tapeWriter = OpenWriter(tPath);
            _depthWriter.AutoFlush = false;
            _tapeWriter.AutoFlush = false;

            if (dNew)
                _depthWriter.WriteLine("time,side,level,price,volume");
            if (tNew)
                _tapeWriter.WriteLine("time,price,volume,aggressor");

            _openDate = date;
            _files = Path.GetFileName(dPath) + " + " + Path.GetFileName(tPath);
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
                if (!File.Exists(d) && !File.Exists(t))
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
            var gz = new GZipStream(fs, CompressionLevel.Optimal, false);
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

        private void CloseFiles()
        {
            FlushPendingCumulative();

            try { if (_depthWriter != null) { _depthWriter.Flush(); _depthWriter.Dispose(); } } catch { }
            try { if (_tapeWriter != null) { _tapeWriter.Flush(); _tapeWriter.Dispose(); } } catch { }
            try { if (_cumWriter != null) { _cumWriter.Flush(); _cumWriter.Dispose(); } } catch { }
            _depthWriter = null;
            _tapeWriter = null;
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
                AddCumFile(parts);

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

                _depthWriter.WriteLine(
                    stamp + "," + side + "," + i + "," + Num(price) + "," +
                    Num(vol));
                _rows++;
                _pending++;
            }
        }

        private static string Ts(DateTime t)
        {
            return t.ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture);
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
                    _tapeWriter.WriteLine(
                        Ts(arg.Time) + "," + Num(arg.Price) + "," +
                        Num(arg.Volume) + "," + side);
                    _rows++;
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
                    return;
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
                        _depthWriter.WriteLine(
                            stamp + "," + key.Substring(0, 1) + ",-1," +
                            key.Substring(2) + ",0");
                        _book.Remove(key);
                        _rows++;
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
