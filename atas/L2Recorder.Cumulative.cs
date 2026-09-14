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
using System.Globalization;
using System.IO;
using System.Text;

using ATAS.Indicators;

namespace Claude1.Recorders
{
    public partial class L2Recorder
    {
        private string _cPath;

        /// <summary>
        /// ATAS builds a cumulative trade incrementally: OnCumulativeTrade
        /// fires when the aggressive order starts filling, and updates arrive
        /// as further fills join it. Recording only the first event captured
        /// every order at one fill -- 171,193 orders with exactly 171,193 fills
        /// between them, no sweeps at all, and an order-size distribution
        /// identical to the raw tape. In other words it added nothing.
        ///
        /// Both events are now written, so a trade appears several times with a
        /// growing fill count. Analysis keeps the row with the most fills for
        /// each (time, first_price, aggressor); the earlier rows are that same
        /// order part-filled. This is deliberate: a stateful merge inside the
        /// recorder could lose the final update if a replay ends mid-order,
        /// whereas append-and-reduce cannot lose anything.
        /// </summary>
        protected override void OnCumulativeTradesUpdate(CumulativeTrade trade)
        {
            Record(trade);
        }

        protected override void OnCumulativeTrade(CumulativeTrade trade)
        {
            Record(trade);
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
