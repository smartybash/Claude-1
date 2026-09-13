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
using System.Text;

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
    public class L2Recorder : Indicator
    {
        /// <summary>
        /// Bumped on every change. It is printed into _status.txt so a stale DLL
        /// left behind by a failed build is visible rather than mistaken for the
        /// current one.
        /// </summary>
        private const string BuildTag = "2026-09-13.g";

        private readonly object _sync = new object();

        private StreamWriter _depthWriter;
        private StreamWriter _tapeWriter;
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
        private long _skippedOutOfSession;

        private int _depthLevels = 10;
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
            set { _depthLevels = value < 1 ? 1 : (value > 50 ? 50 : value); }
        }

        [DisplayName("Snapshot interval (ms)")]
        public int SnapshotMs
        {
            get { return _snapshotMs; }
            set { _snapshotMs = value < 50 ? 50 : value; }
        }

        [DisplayName("Record tape")]
        public bool RecordTape { get; set; } = true;

        [DisplayName("Record depth")]
        public bool RecordDepth { get; set; } = true;

        /// <summary>
        /// Record only the cash session. The recorder writes the ATAS platform
        /// clock, which on this install is UTC, so RTH is 13:30-20:00 there
        /// rather than 09:30-16:00. Overnight was two thirds of the first
        /// recording and none of it is analysed.
        /// </summary>
        [DisplayName("RTH only")]
        public bool RthOnly { get; set; } = true;

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
                sb.AppendLine("depth updates:      " + _depthEvents);
                sb.AppendLine("rows written:       " + _rows);
                sb.AppendLine();
                sb.AppendLine("skipped, off-session " + _skippedOutOfSession);
                sb.AppendLine();
                sb.AppendLine("record tape:        " + RecordTape);
                sb.AppendLine("record depth:       " + RecordDepth);
                sb.AppendLine("RTH only:           " + RthOnly + "  ("
                    + RthStartHour.ToString("00") + ":"
                    + RthStartMinute.ToString("00") + " to "
                    + RthEndHour.ToString("00") + ":"
                    + RthEndMinute.ToString("00") + " platform clock)");
                sb.AppendLine("compressed:         " + Gzip);
                sb.AppendLine("changed levels only:" + ChangesOnly
                    + "  (full ladder every " + KeyframeSeconds + "s)");
                sb.AppendLine("requested folder:   " + OutputFolder);
                sb.AppendLine("WRITING HERE:       " + dir);
                sb.AppendLine("folder choice:      " + _folderNotes);
                sb.AppendLine("data files:         " + _files);
                sb.AppendLine("last error:         " + _lastError);
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

            var sym = Clean(SymbolName());
            var ext = Gzip ? ".csv.gz" : ".csv";
            var run = NextRun(dir, sym, date, ext);
            var dPath = RunPath(dir, "L2_" + sym + "_" + date, run, ext);
            var tPath = RunPath(dir, "TAPE_" + sym + "_" + date, run, ext);

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
                return new StreamWriter(path, true, Encoding.UTF8);

            var fs = new FileStream(path, FileMode.Append, FileAccess.Write,
                                    FileShare.Read);
            var gz = new GZipStream(fs, CompressionLevel.Optimal, false);
            return new StreamWriter(gz, new UTF8Encoding(false));
        }

        private void CloseFiles()
        {
            try { if (_depthWriter != null) { _depthWriter.Flush(); _depthWriter.Dispose(); } } catch { }
            try { if (_tapeWriter != null) { _tapeWriter.Flush(); _tapeWriter.Dispose(); } } catch { }
            _depthWriter = null;
            _tapeWriter = null;
            _openDate = "";
        }

        private void FlushIfDue(bool force)
        {
            if (!force && _pending < 2000)
                return;
            try { if (_depthWriter != null) _depthWriter.Flush(); } catch { }
            try { if (_tapeWriter != null) _tapeWriter.Flush(); } catch { }
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
        protected override void OnCalculate(int bar, decimal value)
        {
            // Nothing is drawn. This always runs, so it carries the status file
            // and doubles as the flush heartbeat for a session that ends without
            // a clean shutdown.
            _calcs++;
            lock (_sync)
            {
                FlushIfDue(true);
                WriteStatus(false);
            }
        }

        protected override void OnNewTrade(MarketDataArg arg)
        {
            if (arg == null)
                return;
            _trades++;
            if (!RecordTape)
                return;
            if (!InSession(arg.Time))
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
