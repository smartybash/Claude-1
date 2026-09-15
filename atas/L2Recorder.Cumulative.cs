// Cumulative trades: the aggressive ORDER, not the individual fills.
//
// The recorded tape is 96.5% single-lot prints, because a market order for 50
// contracts matches against fifty resting one-lots and the exchange reports
// each fill separately. That makes order size invisible: a patient
// one-lot-at-a-time buyer and a single 50-lot sweep look identical on the tape,
// and the earlier "big trades" study failed for exactly this reason -- the top
// 0.1% of prints was size 9.
//
// ATAS reassembles the fills belonging to one aggressive order into a
// CumulativeTrade. That is the field that makes "someone just lifted 200
// contracts" distinguishable from "two hundred people bought one".
//
// THIS FILE IS OPTIONAL. It is compiled out with -p:NoCumulative=true, and
// build.bat retries that way automatically if it fails to compile, so a wrong
// guess about this part of the API costs a rebuild rather than the recorder.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

using ATAS.Indicators;

namespace Claude1.Recorders
{
    public partial class L2Recorder
    {
        private string _cPath;

        partial void AddCumFile(List<string> paths)
        {
            if (_cPath != null)
                paths.Add(_cPath);
        }

        partial void ClearCumPath()
        {
            _cPath = null;
        }

        /// <summary>
        /// ATAS builds a cumulative trade incrementally, and this build's own
        /// API dump settled how:
        ///
        ///     OnCumulativeTrade(CumulativeTrade)         a new order starts
        ///     OnUpdateCumulativeTrade(CumulativeTrade)   more fills join it
        ///     Decimal Lastprice                          note the lowercase p
        ///
        /// Both were guessed wrong twice before and cost builds. They are no
        /// longer guesses: the recorder reflects over the installed assembly
        /// and prints this into _status.txt, and the names above are copied
        /// from that output.
        ///
        /// Writing inside OnCumulativeTrade alone caught every order at
        /// exactly one fill -- 177,133 orders sharing 177,133 fills, no
        /// sweeps, a size distribution identical to the raw tape. The stream
        /// was the tape again with three constant columns.
        ///
        /// So the order in flight is held, refreshed on every update, and
        /// written when the NEXT one begins, by which point it is complete.
        /// The last order of a session is flushed by FlushPendingCumulative
        /// from CloseFiles.
        /// </summary>
        private CumulativeTrade _pendingCum;

        protected override void OnCumulativeTrade(CumulativeTrade trade)
        {
            if (trade == null)
                return;
            CumulativeTrade ready;
            lock (_sync)
            {
                ready = _pendingCum;
                _pendingCum = trade;
            }
            if (ready != null)
                Record(ready);
        }

        /// <summary>
        /// Further fills joined the order already in flight. Keeping the
        /// reference fresh means the row written later reflects the whole
        /// aggressive order rather than its first print.
        /// </summary>
        protected override void OnUpdateCumulativeTrade(CumulativeTrade trade)
        {
            if (trade == null)
                return;
            lock (_sync)
                _pendingCum = trade;
        }

        /// <summary>
        /// Write the order still being accumulated, so the last one of a
        /// session is not lost when the files close.
        /// </summary>
        partial void FlushPendingCumulative()
        {
            CumulativeTrade ready;
            lock (_sync)
            {
                ready = _pendingCum;
                _pendingCum = null;
            }
            if (ready != null)
                Record(ready);
        }

        private void Record(CumulativeTrade trade)
        {
            if (trade == null)
                return;
            _cumTrades++;
            if (!RecordTape)
                return;

            var when = trade.Time;
            if (!InSession(when))
            {
                _skippedOutOfSession++;
                return;
            }

            lock (_sync)
            {
                try
                {
                    EnsureCumOpen(when);

                    var side = trade.Direction == TradeDirection.Buy ? "B"
                             : trade.Direction == TradeDirection.Sell ? "S"
                             : "?";

                    // Lastprice, not LastPrice -- the lowercase p is why two
                    // earlier builds failed. Ticks is still walked, but only
                    // for the fill count, which has no property of its own.
                    var lastPrice = trade.Lastprice;
                    var fills = 0;
                    if (trade.Ticks != null)
                    {
                        foreach (var tick in trade.Ticks)
                            fills++;
                    }

                    _cumWriter.WriteLine(
                        when.ToString("yyyy-MM-dd HH:mm:ss.fff",
                                      CultureInfo.InvariantCulture) + "," +
                        side + "," +
                        trade.FirstPrice.ToString(CultureInfo.InvariantCulture) + "," +
                        lastPrice.ToString(CultureInfo.InvariantCulture) + "," +
                        trade.Volume.ToString(CultureInfo.InvariantCulture) + "," +
                        fills);
                    _rows++;
                    _pending++;
                    FlushIfDue(false);
                }
                catch (Exception ex)
                {
                    _lastError = "cumulative: " + ex.Message;
                }
            }
        }

        /// <summary>Caller must hold _sync.</summary>
        private void EnsureCumOpen(DateTime stamp)
        {
            if (_cumWriter != null)
                return;

            var dir = ResolveFolder();
            if (dir == null)
                throw new IOException("no writable output folder");

            var date = stamp.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
            if (_cPath == null)
            {
                var ext = Gzip ? ".csv.gz" : ".csv";
                var stem = "CUM_" + Clean(SymbolName()) + "_" + date;
                for (var run = 1; run < 100; run++)
                {
                    var cand = RunPath(dir, stem, run, ext);
                    if (!File.Exists(cand))
                    {
                        _cPath = cand;
                        break;
                    }
                }
            }

            var isNew = !File.Exists(_cPath);
            _cumWriter = OpenWriter(_cPath);
            _cumWriter.AutoFlush = false;
            if (isNew)
                _cumWriter.WriteLine(
                    "time,aggressor,first_price,last_price,volume,fills");
        }
    }
}
