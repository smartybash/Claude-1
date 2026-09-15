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
        /// ATAS builds a cumulative trade incrementally: OnCumulativeTrade
        /// fires when the aggressive order STARTS filling, and further fills
        /// join the same object afterwards. Writing the row inside that
        /// callback therefore captured every order at exactly one fill --
        /// 177,133 orders with 177,133 fills between them, no sweeps at all,
        /// and a size distribution identical to the raw tape. The stream was a
        /// duplicate of the tape with three constant columns, which is why no
        /// test in this project could use it.
        ///
        /// THE FIX NEEDS NO NEW API. Two guesses at the name of the update
        /// event have already failed to compile, and a third would risk the
        /// build for no reason. Instead the trade is held and written when the
        /// NEXT one arrives, by which time ATAS has finished adding fills to
        /// it. The last trade of a session is flushed by CloseCum, called from
        /// the same idle path that closes the other writers.
        ///
        /// The object is read at write time rather than copied at arrival
        /// time, so if this build hands out a fresh CumulativeTrade per fill
        /// instead of mutating one, the result is no worse than before.
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
        /// Write the trade still being accumulated. Called when the files are
        /// closed so the final order of a session is not lost.
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

                    // The last price is taken from the fills rather than from a
                    // property. CumulativeTrade exposes FirstPrice, which the
                    // compiler confirmed, but not LastPrice; walking the ticks
                    // needs no further guess about the API and gives the same
                    // answer by definition.
                    var fills = 0;
                    var lastPrice = trade.FirstPrice;
                    if (trade.Ticks != null)
                    {
                        foreach (var tick in trade.Ticks)
                        {
                            lastPrice = tick.Price;
                            fills++;
                        }
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
