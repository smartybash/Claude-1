// ATAS.DataFeedsCore is deliberately NOT imported: it declares its own
// TradeDirection and MarketDataType alongside the ones in ATAS.Indicators,
// and importing both makes every use of those names ambiguous (CS0104).
// MarketDataArg comes from ATAS.Indicators, so its enums are the right ones.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.IO;
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
        private const string BuildTag = "2026-09-13.c";

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

        private int _depthLevels = 10;
        private int _snapshotMs = 250;

        [DisplayName("Output folder")]
        public string OutputFolder { get; set; } =
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
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

        public L2Recorder()
        {
            try { DataSeries[0].IsHidden = true; } catch { }

            // Written here, before any market data exists, so the status file
            // appears the moment the indicator is added to a chart. That makes
            // "no status file" mean one thing only: it is not on the chart.
            WriteStatus(true);
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
                Directory.CreateDirectory(OutputFolder);
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
                sb.AppendLine("record tape:        " + RecordTape);
                sb.AppendLine("record depth:       " + RecordDepth);
                sb.AppendLine("output folder:      " + OutputFolder);
                sb.AppendLine("data files:         " + _files);
                sb.AppendLine("last error:         " + _lastError);
                sb.AppendLine();
                sb.AppendLine("If trades and depth updates are both 0, the platform is");
                sb.AppendLine("sending neither. In Market Replay, switch the replay mode");
                sb.AppendLine("to Ticks + DOM -- the other modes carry no tick or depth");
                sb.AppendLine("data and there is nothing for this to record.");
                File.WriteAllText(Path.Combine(OutputFolder, "_status.txt"),
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
            Directory.CreateDirectory(OutputFolder);

            var sym = Clean(SymbolName());
            var dPath = Path.Combine(OutputFolder, "L2_" + sym + "_" + date + ".csv");
            var tPath = Path.Combine(OutputFolder, "TAPE_" + sym + "_" + date + ".csv");

            var dNew = !File.Exists(dPath);
            var tNew = !File.Exists(tPath);

            _depthWriter = new StreamWriter(dPath, true, Encoding.UTF8);
            _tapeWriter = new StreamWriter(tPath, true, Encoding.UTF8);
            _depthWriter.AutoFlush = false;
            _tapeWriter.AutoFlush = false;

            if (dNew)
                _depthWriter.WriteLine("time,side,level,price,volume");
            if (tNew)
                _tapeWriter.WriteLine("time,price,volume,aggressor");

            _openDate = date;
            _files = Path.GetFileName(dPath) + " + " + Path.GetFileName(tPath);
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
                    var n = Math.Min(DepthLevels, bids.Count);
                    for (var i = 0; i < n; i++)
                    {
                        _depthWriter.WriteLine(
                            stamp + ",B," + i + "," + Num(bids[i].Price) + "," +
                            Num(bids[i].Volume));
                        _rows++;
                    }

                    n = Math.Min(DepthLevels, asks.Count);
                    for (var i = 0; i < n; i++)
                    {
                        _depthWriter.WriteLine(
                            stamp + ",A," + i + "," + Num(asks[i].Price) + "," +
                            Num(asks[i].Volume));
                        _rows++;
                    }

                    _pending += DepthLevels * 2;
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
