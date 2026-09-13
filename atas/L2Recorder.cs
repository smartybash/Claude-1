using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Text;

using ATAS.DataFeedsCore;
using ATAS.Indicators;

namespace Claude1.Recorders
{
    /// <summary>
    /// Writes Level 2 depth snapshots and aggressor-tagged tape to CSV.
    ///
    /// Two files per instrument per day, in OutputFolder:
    ///     L2_{symbol}_{yyyyMMdd}.csv     depth ladder, throttled snapshots
    ///     TAPE_{symbol}_{yyyyMMdd}.csv   every trade, with aggressor side
    ///
    /// The depth book updates far faster than anything worth recording, so
    /// snapshots are throttled to SnapshotMs and truncated to DepthLevels per
    /// side. At the defaults (250ms, 10 levels) a full RTH session is roughly
    /// 1.9M depth rows -- large but workable. Raising either setting multiplies
    /// the file size directly.
    ///
    /// Trades are never throttled: the aggressor tag is the whole point and
    /// dropping trades would bias delta.
    ///
    /// Only [DisplayName] is used for the settings labels, so the build needs
    /// no attribute package beyond System.ComponentModel.
    /// </summary>
    [DisplayName("L2 Recorder (CSV)")]
    public class L2Recorder : Indicator
    {
        private readonly object _sync = new object();

        private StreamWriter _depthWriter;
        private StreamWriter _tapeWriter;
        private string _openDate = "";
        private DateTime _lastSnapshot = DateTime.MinValue;
        private int _pending;

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
            // Nothing is drawn. This runs often enough to serve as a flush
            // heartbeat, so a session that ends without OnDispose still lands
            // its rows on disk.
            if (bar == CurrentBar - 1)
            {
                lock (_sync)
                    FlushIfDue(true);
            }
        }

        protected override void OnNewTrade(MarketDataArg arg)
        {
            if (!RecordTape || arg == null)
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
                    _pending++;
                    FlushIfDue(false);
                }
                catch { /* never let a disk hiccup kill the feed thread */ }
            }
        }

        protected override void MarketDepthChanged(MarketDataArg arg)
        {
            if (!RecordDepth || arg == null)
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
                        return;

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
                        _depthWriter.WriteLine(
                            stamp + ",B," + i + "," + Num(bids[i].Price) + "," +
                            Num(bids[i].Volume));

                    n = Math.Min(DepthLevels, asks.Count);
                    for (var i = 0; i < n; i++)
                        _depthWriter.WriteLine(
                            stamp + ",A," + i + "," + Num(asks[i].Price) + "," +
                            Num(asks[i].Volume));

                    _pending += DepthLevels * 2;
                    FlushIfDue(false);
                }
                catch { }
            }
        }

        protected override void OnDispose()
        {
            lock (_sync)
            {
                FlushIfDue(true);
                CloseFiles();
            }
            base.OnDispose();
        }
    }
}
