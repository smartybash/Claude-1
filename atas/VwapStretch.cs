// VWAP Stretch — the one hypothesis still alive, shown live while it is tested.
//
// READ THIS BEFORE TRADING FROM IT: the rule below is NOT confirmed. On the
// 46-session discovery set it returns +9.73 points a trade exiting at 17:00
// UTC (t = +1.55) and +21.70 holding to the close (t = +2.14). Neither clears
// the bar that was set in advance -- t >= 2.4 on sessions the rule has never
// seen -- and seven earlier findings in this project looked at least this good
// before dying. The holdout is being collected now.
//
// So this draws the SIGNAL STATE and no orders. Its job until the test
// finishes is to let the live numbers be checked against the backtest: if the
// z-score on your chart disagrees with the study's numbers, one of them is wrong
// and it is better to find that out now.
//
// WHAT IT COMPUTES
//
//   vwap        session volume-weighted average price, from ticks
//   stretch     (price - vwap) divided by a rolling standard deviation of
//               price, so it means the same thing on a quiet day and a wild one
//   z           stretch standardised against THE SESSION SO FAR -- an expanding
//               mean and standard deviation, never the whole day
//
// The expanding window is the whole point. An earlier version standardised
// against the full session, which at 10:00 uses statistics that have not
// happened yet. That lookahead was worth 8.75 points a trade -- it WAS the
// result. Everything here is computed from bars already closed.
//
// THE RULE, as pre-registered
//
//   z above +1.45  ->  the stretch is extended upward, the tested trade is SHORT
//   z below -1.27  ->  extended downward, the tested trade is LONG
//   in between     ->  nothing
//
// Those cuts are the 80th and 20th percentiles of z across the discovery set.
// Exit is by CLOCK, not by target: 17:00, 19:00 or the close. There is no stop
// in the tested rule, which is a real risk and is stated rather than hidden.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;

using ATAS.Indicators;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;

namespace Claude1.Recorders
{
    [DisplayName("VWAP Stretch (under test)")]
    public class VwapStretch : Indicator
    {
        private const string BuildTag = "2026-09-15.stretch.a";

        private static readonly Color LongInk = Color.FromArgb(56, 190, 130);
        private static readonly Color ShortInk = Color.FromArgb(228, 106, 82);
        private static readonly Color VwapInk = Color.FromArgb(200, 238, 186, 88);
        private static readonly Color FlatInk = Color.FromArgb(150, 160, 172);
        private static readonly Color PanelFill = Color.FromArgb(232, 16, 18, 22);
        private static readonly Color PanelEdge = Color.FromArgb(150, 110, 120, 136);
        private static readonly Color PanelInk = Color.FromArgb(236, 240, 245);
        private static readonly Color WarnInk = Color.FromArgb(238, 186, 88);

        private readonly RenderFont _fBig = new RenderFont("Segoe UI", 16);
        private readonly RenderFont _fMid = new RenderFont("Segoe UI", 12);
        private readonly RenderFont _fTiny = new RenderFont("Segoe UI", 10);

        private readonly object _sync = new object();

        /// <summary>Short above this. The 80th percentile of z on the
        /// 46-session discovery set.</summary>
        [DisplayName("Short above z")]
        public decimal ShortZ { get; set; } = 1.45m;

        /// <summary>Long below this. The 20th percentile.</summary>
        [DisplayName("Long below z")]
        public decimal LongZ { get; set; } = -1.27m;

        [DisplayName("Session start hour (platform clock)")]
        public int SessionHour { get; set; } = 13;

        [DisplayName("Session start minute")]
        public int SessionMinute { get; set; } = 30;

        [DisplayName("Exit hour (platform clock)")]
        public int ExitHour { get; set; } = 17;

        [DisplayName("Bars for the price deviation")]
        public int DevBars { get; set; } = 30;

        [DisplayName("Draw the VWAP line")]
        public bool ShowVwap { get; set; } = true;

        // session state, all from closed bars
        private decimal _pv, _vol;                 // for VWAP
        private readonly List<decimal> _closes = new List<decimal>();
        private double _zSum, _zSumSq;             // expanding stats of stretch
        private int _zN;
        private decimal _vwap, _stretch;
        private double _z;
        private bool _ready;
        private int _sessionStart = -1;
        private int _lastBar = -1;

        public VwapStretch()
        {
            try { DataSeries[0].IsHidden = true; } catch { }
            EnableCustomDrawing = true;
            SubscribeToDrawingEvents(DrawingLayouts.Final | DrawingLayouts.LatestBar);
        }

        private bool IsSessionOpen(int i)
        {
            if (i == 0)
                return true;
            var a = GetCandle(i - 1).Time;
            var b = GetCandle(i).Time;
            if (a.Date != b.Date)
                return true;
            var open = SessionHour * 60 + SessionMinute;
            return (a.Hour * 60 + a.Minute) < open && (b.Hour * 60 + b.Minute) >= open;
        }

        protected override void OnCalculate(int bar, decimal value)
        {
            if (bar == _lastBar)
                return;
            _lastBar = bar;

            if (IsSessionOpen(bar))
            {
                lock (_sync)
                {
                    _sessionStart = bar;
                    _pv = 0m; _vol = 0m;
                    _closes.Clear();
                    _zSum = 0.0; _zSumSq = 0.0; _zN = 0;
                    _ready = false;
                }
            }
            if (_sessionStart < 0)
                return;

            var c = GetCandle(bar);
            lock (_sync)
            {
                // VWAP from the bar's own typical price and volume. Ticks feed
                // the candle, so this is the same quantity the study computed
                // from the tape.
                var tp = (c.High + c.Low + c.Close) / 3m;
                _pv += tp * c.Volume;
                _vol += c.Volume;
                if (_vol <= 0m)
                    return;
                _vwap = _pv / _vol;

                _closes.Add(c.Close);
                if (_closes.Count > DevBars)
                    _closes.RemoveAt(0);
                if (_closes.Count < 10)
                    return;

                // rolling standard deviation of price, so the stretch is in
                // units of how much this session actually moves
                decimal mean = 0m;
                foreach (var p in _closes) mean += p;
                mean /= _closes.Count;
                double ss = 0.0;
                foreach (var p in _closes)
                {
                    var d = (double)(p - mean);
                    ss += d * d;
                }
                var sd = Math.Sqrt(ss / _closes.Count);
                if (sd <= 0.0)
                    return;

                _stretch = (decimal)((double)(c.Close - _vwap) / sd);

                // expanding standardisation: the session SO FAR, never the
                // whole day. This is the part that must not be "improved".
                var x = (double)_stretch;
                _zSum += x;
                _zSumSq += x * x;
                _zN++;
                if (_zN < 30)
                    return;
                var m = _zSum / _zN;
                var v = _zSumSq / _zN - m * m;
                if (v <= 0.0)
                    return;
                _z = (x - m) / Math.Sqrt(v);
                _ready = true;
            }
        }

        private string Verdict(double z, out Color ink)
        {
            if (!_ready) { ink = FlatInk; return "warming up"; }
            if (z >= (double)ShortZ) { ink = ShortInk; return "SHORT zone"; }
            if (z <= (double)LongZ) { ink = LongInk; return "LONG zone"; }
            ink = FlatInk;
            return "no zone";
        }

        protected override void OnRender(RenderContext context, DrawingLayouts layout)
        {
            if (ChartInfo == null || _sessionStart < 0)
                return;
            decimal vwap, stretch;
            double z;
            bool ready;
            lock (_sync)
            {
                vwap = _vwap; stretch = _stretch; z = _z; ready = _ready;
            }

            if (ShowVwap && vwap > 0m)
            {
                int y;
                try { y = ChartInfo.GetYByPrice(vwap, false); }
                catch { y = int.MinValue; }
                if (y != int.MinValue)
                {
                    context.DrawLine(new RenderPen(VwapInk, 2), 0, y,
                                     ChartArea.Width, y);
                    context.DrawString("VWAP " + vwap.ToString("N2"), _fTiny,
                                       VwapInk, 8, y - 14);
                }
            }

            Color ink;
            var verdict = Verdict(z, out ink);
            var head = ready
                ? verdict + "     z = " + z.ToString("N2")
                : "warming up  (" + _zN + "/30 bars)";
            var line2 = ready
                ? "short above " + ShortZ.ToString("N2") +
                  "     long below " + LongZ.ToString("N2") +
                  "     stretch " + stretch.ToString("N2")
                : "needs 30 closed bars after the open";
            var line3 = "exit by clock at " + ExitHour.ToString("00") +
                        ":00 — no stop in the tested rule";
            var line4 = "UNDER TEST — not confirmed. Do not size from this.";

            var wide = Math.Max(context.MeasureString(head, _fBig).Width,
                       Math.Max(context.MeasureString(line2, _fMid).Width,
                       Math.Max(context.MeasureString(line3, _fTiny).Width,
                                context.MeasureString(line4, _fTiny).Width)));
            var box = new Rectangle(10, 10, (int)wide + 28, 104);
            context.FillRectangle(PanelFill, box);
            context.DrawRectangle(new RenderPen(PanelEdge, 1), box);
            context.DrawString(head, _fBig, ink, 24, 18);
            context.DrawString(line2, _fMid, PanelInk, 24, 46);
            context.DrawString(line3, _fTiny, FlatInk, 24, 70);
            context.DrawString(line4, _fTiny, WarnInk, 24, 88);
        }
    }
}
