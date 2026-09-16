// MARKET BY ORDER — the true event stream, if the feed carries it.
//
// The depth recording has always been a POLL. On every book change the
// recorder looked at a clock, returned if under SnapshotMs, and otherwise
// re-read the whole ladder. It therefore captured book STATES at about four a
// second and never saw a single book EVENT: whether size appeared, was
// modified, or was pulled is not recoverable from a sequence of snapshots, and
// the "level -1, volume 0" rows in the depth file are the recorder's own
// inference about what left the top of the book, not anything the platform
// said.
//
// The API inventory shows the real thing exists:
//
//     OnMarketByOrdersChanged(IEnumerable<MarketByOrder> values)
//
//     MarketByOrder
//         DateTime               Time
//         MarketByOrderUpdateTypes Type     Snapshot=0 New=1 Change=2 Delete=3
//         MarketDataType         Side       Bid=0 Ask=1
//         Int64                  Priority              queue position
//         Int64                  ExchangeOrderId       identity
//         Decimal                Price
//         Decimal                Volume
//
// That is add / change / remove per individual order, with queue priority and
// a stable id. It is strictly more information than any ladder: the ladder is
// derivable from it and it is not derivable from the ladder.
//
// WHETHER IT ARRIVES IS A DIFFERENT QUESTION, and this file does not assume an
// answer. CME distributes order-by-order data on MDP 3.0, but many retail
// routes deliver only aggregated depth, in which case this callback never
// fires. So the stream is written if it comes, the counter is reported either
// way, and a session that produced no rows says so in the status file rather
// than silently looking like a quiet market.
//
// Compiled out with -p:NoByOrder=true if a future ATAS build drops the
// callback, exactly as the cumulative part already is.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

using ATAS.DataFeedsCore;

namespace Claude1.Recorders
{
    public partial class L2Recorder
    {
        private StreamWriter _mboWriter;
        private string _mPath;

        partial void AddByOrderFile(List<string> parts)
        {
            if (_mPath != null && File.Exists(_mPath))
                parts.Add(_mPath);
        }

        partial void FlushByOrder()
        {
            try { if (_mboWriter != null) _mboWriter.Flush(); } catch { }
        }

        partial void CloseByOrder()
        {
            try
            {
                if (_mboWriter != null)
                {
                    _mboWriter.Flush();
                    _mboWriter.Dispose();
                }
            }
            catch { }
            _mboWriter = null;
        }

        private void EnsureByOrderOpen(DateTime when)
        {
            if (_mboWriter != null)
                return;
            var dir = ResolveFolder();
            if (dir == null)
                return;
            var ext = Gzip ? ".csv.gz" : ".csv";
            var date = when.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
            _mPath = Path.Combine(dir, "MBO_" + Clean(SymbolName()) + "_" +
                                       date + ext);
            var isNew = !File.Exists(_mPath);
            _mboWriter = OpenWriter(_mPath);
            _mboWriter.AutoFlush = false;
            if (isNew)
                _mboWriter.WriteLine(
                    "seq,time,type,side,price,volume,priority,order_id");
        }

        protected override void OnMarketByOrdersChanged(
            IEnumerable<MarketByOrder> values)
        {
            if (values == null)
                return;
            if (!RecordByOrder || !RecordDepth)
                return;

            lock (_sync)
            {
                try
                {
                    foreach (var o in values)
                    {
                        if (o == null)
                            continue;
                        _mboEvents++;
                        NotePrice(o.Price);
                        NoteDataTime(o.Time);
                        if (!InSession(o.Time))
                        {
                            _skippedOutOfSession++;
                            continue;
                        }
                        EnsureByOrderOpen(o.Time);
                        if (_mboWriter == null)
                            return;
                        _lastData = DateTime.Now;
                        _mboWriter.WriteLine(
                            (++_seqMbo) + "," + Ts(o.Time) + "," +
                            (int)o.Type + "," + (int)o.Side + "," +
                            Num(o.Price) + "," + Num(o.Volume) + "," +
                            o.Priority.ToString(CultureInfo.InvariantCulture) +
                            "," +
                            o.ExchangeOrderId.ToString(CultureInfo.InvariantCulture));
                        _rows++;
                        _mboWritten++;
                        _pending++;
                    }
                    FlushIfDue(false);
                }
                catch (Exception ex)
                {
                    _lastError = "mbo: " + ex.Message;
                }
            }
        }
    }
}
