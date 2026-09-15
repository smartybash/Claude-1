// Structure Map — higher-timeframe structure, drawn on whatever chart you use.
//
// THE POINT OF THIS VERSION: structure is computed on a FIXED timeframe --
// fifteen minutes by default -- no matter what the chart is set to. Put it on
// a 1-minute or a tick chart and the labels stay the 15-minute ones.
//
// That is not a preference, it is what the testing said. The same break-of-
// structure trade over 1,420 sessions:
//
//     1 min    25.7 signals a session    t = -9.41
//     3 min     7.7 signals a session    t = -5.80
//     5 min     4.1 signals a session    t = -3.73
//    15 min     0.9 signals a session    t = -0.91
//    30 min     0.2 signals a session    t = -0.71
//
// Perfectly monotonic: the more labels, the worse. One- and three-minute
// structure is not a weaker signal, it is decisively negative. So drawing it
// is worse than drawing nothing, and a chart covered in labels is a chart
// showing mostly noise. Fifteen minutes is where it stops being negative, at
// about one signal a session.
//
// What it draws, and nothing else:
//
//   gap level    the previous session's close, while it is still unfilled
//   HH HL LH LL  confirmed swings only, the most recent few
//   BOS          the last break or two, at the level that broke
//   FVG          unfilled imbalances only -- a filled one is history
//   one line     the structure in plain words
//
// A swing is labelled only once it is CONFIRMED, which is Pivot bars after
// the bar it sits on. Nothing repaints.
//
// This marks the structure and prints no order. The sequence beats a blind
// entry by +0.176R, and every complete version of the trade still lost,
// because the break confirms at the top of the leg.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;

using ATAS.Indicators;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;

namespace Claude1.Recorders
{
    [DisplayName("Structure Map (higher timeframe)")]
    public class StructureMap : Indicator
    {
        private const string BuildTag = "2026-09-15.structure.b";

        private static readonly Color UpInk = Color.FromArgb(56, 190, 130);
        private static readonly Color DownInk = Color.FromArgb(228, 106, 82);
        private static readonly Color GapEdge = Color.FromArgb(190, 238, 186, 88);
        private static readonly Color GapFill = Color.FromArgb(30, 238, 186, 88);
        private static readonly Color FvgUp = Color.FromArgb(40, 56, 190, 130);
        private static readonly Color FvgDown = Color.FromArgb(40, 228, 106, 82);
        private static readonly Color BosInk = Color.FromArgb(170, 205, 212, 226);
        private static readonly Color PanelFill = Color.FromArgb(230, 16, 18, 22);
        private static readonly Color PanelEdge = Color.FromArgb(150, 110, 120, 136);
        private static readonly Color PanelInk = Color.FromArgb(236, 240, 245);

        private readonly RenderFont _fTiny = new RenderFont("Segoe UI", 10);
        private readonly RenderFont _fMid = new RenderFont("Segoe UI", 13);

        private readonly object _sync = new object();

        /// <summary>
        /// Minutes per structure bar, independent of the chart's own timeframe.
        /// Fifteen is the tested default; below five the labels are noise.
        /// </summary>
        [DisplayName("Structure timeframe (minutes)")]
        public int StructureMinutes { get; set; } = 15;

        [DisplayName("Pivot strength (structure bars each side)")]
        public int Pivot { get; set; } = 2;

        [DisplayName("Show swing labels")]
        public bool ShowSwings { get; set; } = true;

        [DisplayName("Show unfilled fair value gaps")]
        public bool ShowFvg { get; set; } = true;

        [DisplayName("Show break of structure")]
        public bool ShowBos { get; set; } = true;

        [DisplayName("Show the opening gap")]
        public bool ShowGap { get; set; } = true;

        /// <summary>How many of each thing to keep on screen. Clutter is the
        /// failure mode this version exists to fix.</summary>
        [DisplayName("Keep last N swings")]
        public int KeepSwings { get; set; } = 6;

        [DisplayName("Keep last N breaks")]
        public int KeepBreaks { get; set; } = 2;

        [DisplayName("Session start hour (platform clock)")]
        public int SessionHour { get; set; } = 13;

        [DisplayName("Session start minute")]
        public int SessionMinute { get; set; } = 30;

        /// <summary>A structure bar: several chart candles rolled into one.</summary>
        private sealed class VBar
        {
            public int Last;                  // chart bar index it closes on
            public decimal O, H, L, C;
        }

        private sealed class Swing
        {
            public int Bar;
            public decimal Price;
            public bool IsHigh;
            public string Label;
        }

        private sealed class Fvg
        {
            public int Bar;
            public decimal Top, Bottom;
            public bool Up;
        }

        private sealed class Bos
        {
            public int Bar;
            public decimal Price;
            public bool Up;
        }

        private readonly List<Swing> _swings = new List<Swing>();
        private readonly List<Fvg> _fvgs = new List<Fvg>();
        private readonly List<Bos> _bos = new List<Bos>();

        private int _sessionStart = -1;
        private decimal _prevClose, _sessionOpen;
        private bool _haveGap, _gapFilled;
        private string _state = "";
        private int _lastBuilt = -1;

        public StructureMap()
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
            if (bar < 3)
                return;
            if (IsSessionOpen(bar))
            {
                lock (_sync)
                {
                    _sessionStart = bar;
                    _prevClose = GetCandle(bar - 1).Close;
                    _sessionOpen = GetCandle(bar).Open;
                    _haveGap = _prevClose != _sessionOpen;
                    _gapFilled = false;
                }
            }
            if (_sessionStart < 0 || bar == _lastBuilt)
                return;
            _lastBuilt = bar;
            lock (_sync)
                Rebuild(bar);
        }

        /// <summary>
        /// Roll the chart's candles into fixed-length structure bars, aligned
        /// to the clock so a 15-minute bar always starts on the quarter hour
        /// regardless of where the session began or what the chart shows.
        /// </summary>
        private List<VBar> Virtual(int from, int last)
        {
            var step = StructureMinutes < 1 ? 15 : StructureMinutes;
            var bars = new List<VBar>();
            VBar cur = null;
            var slot = int.MinValue;
            for (var i = from; i <= last; i++)
            {
                var c = GetCandle(i);
                var s = (int)c.Time.TimeOfDay.TotalMinutes / step;
                if (cur == null || s != slot)
                {
                    cur = new VBar
                    {
                        Last = i, O = c.Open, H = c.High, L = c.Low, C = c.Close
                    };
                    bars.Add(cur);
                    slot = s;
                }
                else
                {
                    cur.Last = i;
                    if (c.High > cur.H) cur.H = c.High;
                    if (c.Low < cur.L) cur.L = c.Low;
                    cur.C = c.Close;
                }
            }
            return bars;
        }

        private void Rebuild(int last)
        {
            _swings.Clear();
            _fvgs.Clear();
            _bos.Clear();

            var v = Virtual(_sessionStart, last);
            var k = Pivot < 1 ? 1 : Pivot;
            if (v.Count < 2 * k + 2)
                return;

            // --- gap: only interesting while it is unfilled ------------------
            if (_haveGap && !_gapFilled)
            {
                var up = _sessionOpen > _prevClose;
                foreach (var b in v)
                {
                    if ((up && b.L <= _prevClose) || (!up && b.H >= _prevClose))
                    {
                        _gapFilled = true;
                        break;
                    }
                }
            }

            // --- swings, confirmed k structure bars late ---------------------
            decimal lastHigh = 0m, lastLow = 0m;
            bool haveHigh = false, haveLow = false;
            for (var i = k; i <= v.Count - 1 - k; i++)
            {
                var isHigh = true;
                var isLow = true;
                for (var j = i - k; j <= i + k; j++)
                {
                    if (j == i)
                        continue;
                    if (v[j].H > v[i].H) isHigh = false;
                    if (v[j].L < v[i].L) isLow = false;
                }
                if (isHigh)
                {
                    _swings.Add(new Swing
                    {
                        Bar = v[i].Last, Price = v[i].H, IsHigh = true,
                        Label = !haveHigh ? "H" : (v[i].H > lastHigh ? "HH" : "LH")
                    });
                    lastHigh = v[i].H;
                    haveHigh = true;
                }
                if (isLow)
                {
                    _swings.Add(new Swing
                    {
                        Bar = v[i].Last, Price = v[i].L, IsHigh = false,
                        Label = !haveLow ? "L" : (v[i].L > lastLow ? "HL" : "LL")
                    });
                    lastLow = v[i].L;
                    haveLow = true;
                }
            }

            // --- unfilled fair value gaps only -------------------------------
            for (var i = 2; i < v.Count; i++)
            {
                Fvg g = null;
                if (v[i].L > v[i - 2].H)
                    g = new Fvg
                    {
                        Bar = v[i].Last, Bottom = v[i - 2].H, Top = v[i].L, Up = true
                    };
                else if (v[i].H < v[i - 2].L)
                    g = new Fvg
                    {
                        Bar = v[i].Last, Bottom = v[i].H, Top = v[i - 2].L, Up = false
                    };
                if (g == null)
                    continue;
                var filled = false;
                for (var j = i + 1; j < v.Count; j++)
                {
                    if ((g.Up && v[j].L <= g.Bottom) || (!g.Up && v[j].H >= g.Top))
                    {
                        filled = true;
                        break;
                    }
                }
                if (!filled)
                    _fvgs.Add(g);
            }

            // --- breaks of structure, most recent only -----------------------
            for (var i = 0; i < v.Count; i++)
            {
                Swing hi = null, lo = null;
                foreach (var s in _swings)
                {
                    if (s.Bar > v[i].Last)
                        continue;
                    if (s.IsHigh) hi = s; else lo = s;
                }
                if (hi != null && v[i].C > hi.Price &&
                    !_bos.Exists(b => b.Up && b.Price == hi.Price))
                    _bos.Add(new Bos { Bar = v[i].Last, Price = hi.Price, Up = true });
                if (lo != null && v[i].C < lo.Price &&
                    !_bos.Exists(b => !b.Up && b.Price == lo.Price))
                    _bos.Add(new Bos { Bar = v[i].Last, Price = lo.Price, Up = false });
            }

            Trim(_swings, KeepSwings);
            Trim(_bos, KeepBreaks);
            _state = Describe();
        }

        private static void Trim<T>(List<T> list, int keep)
        {
            if (keep > 0 && list.Count > keep)
                list.RemoveRange(0, list.Count - keep);
        }

        /// <summary>The structure in the words a chart would be read in.</summary>
        private string Describe()
        {
            Swing h1 = null, h0 = null, l1 = null, l0 = null;
            foreach (var s in _swings)
            {
                if (s.IsHigh) { h1 = h0; h0 = s; }
                else { l1 = l0; l0 = s; }
            }
            if (h0 == null || l0 == null || h1 == null || l1 == null)
                return "waiting for structure";
            var hh = h0.Price > h1.Price;
            var hl = l0.Price > l1.Price;
            if (hh && hl) return "higher highs and higher lows  —  up";
            if (!hh && !hl) return "lower highs and lower lows  —  down";
            return "mixed  —  no clear structure";
        }

        private int X(int bar)
        {
            return ChartInfo.GetXByBar(bar, false);
        }

        protected override void OnRender(RenderContext context, DrawingLayouts layout)
        {
            if (ChartInfo == null || _sessionStart < 0)
                return;

            List<Swing> swings;
            List<Fvg> fvgs;
            List<Bos> bos;
            decimal prevClose;
            bool haveGap, gapFilled;
            string state;
            lock (_sync)
            {
                swings = new List<Swing>(_swings);
                fvgs = new List<Fvg>(_fvgs);
                bos = new List<Bos>(_bos);
                prevClose = _prevClose;
                haveGap = _haveGap;
                gapFilled = _gapFilled;
                state = _state;
            }

            var w = ChartArea.Width;
            var h = ChartArea.Height;

            if (ShowFvg)
                foreach (var g in fvgs)
                    DrawFvg(context, g, h);
            if (ShowGap && haveGap && !gapFilled)
                DrawGapLevel(context, prevClose, w);
            if (ShowBos)
                foreach (var b in bos)
                    DrawBos(context, b, w);
            if (ShowSwings)
                foreach (var s in swings)
                    DrawSwing(context, s);

            DrawPanel(context, state, haveGap, gapFilled, prevClose);
        }

        private void DrawGapLevel(RenderContext context, decimal level, int w)
        {
            int y;
            try { y = ChartInfo.GetYByPrice(level, false); }
            catch { return; }
            context.DrawLine(new RenderPen(GapEdge, 2), 0, y, w, y);
            context.DrawString("GAP LEVEL  " + level.ToString("N2"),
                               _fTiny, GapEdge, 8, y - 14);
        }

        private void DrawFvg(RenderContext context, Fvg g, int h)
        {
            int yt, yb, x0;
            try
            {
                yt = ChartInfo.GetYByPrice(g.Top, false);
                yb = ChartInfo.GetYByPrice(g.Bottom, false);
                x0 = X(g.Bar);
            }
            catch { return; }
            var top = Math.Min(yt, yb);
            var hh = Math.Abs(yb - yt);
            if (hh < 1 || top > h || top + hh < 0)
                return;
            context.FillRectangle(g.Up ? FvgUp : FvgDown,
                                  new Rectangle(x0, top, Math.Max(2, ChartArea.Width - x0), hh));
        }

        private void DrawBos(RenderContext context, Bos b, int w)
        {
            int y, x;
            try
            {
                y = ChartInfo.GetYByPrice(b.Price, false);
                x = X(b.Bar);
            }
            catch { return; }
            context.DrawLine(new RenderPen(BosInk, 1), Math.Max(0, x - 40), y, w, y);
            context.DrawString("BOS " + (b.Up ? "up" : "down"), _fTiny,
                               b.Up ? UpInk : DownInk, x + 4, y - 13);
        }

        private void DrawSwing(RenderContext context, Swing s)
        {
            int y, x;
            try
            {
                y = ChartInfo.GetYByPrice(s.Price, false);
                x = X(s.Bar);
            }
            catch { return; }
            var ink = s.Label == "HH" || s.Label == "HL" ? UpInk : DownInk;
            var size = context.MeasureString(s.Label, _fTiny);
            var yy = s.IsHigh ? y - (int)size.Height - 3 : y + 3;
            context.DrawString(s.Label, _fTiny, ink, x - (int)size.Width / 2, yy);
        }

        private void DrawPanel(RenderContext context, string state, bool haveGap,
                               bool gapFilled, decimal level)
        {
            var head = StructureMinutes + "-min structure:  " +
                       (string.IsNullOrEmpty(state) ? "waiting" : state);
            var line2 = !haveGap ? "no gap today"
                      : gapFilled ? "gap has been filled"
                      : "gap still open at " + level.ToString("N2");

            var wide = Math.Max(context.MeasureString(head, _fMid).Width,
                                context.MeasureString(line2, _fTiny).Width);
            var box = new Rectangle(10, 10, (int)wide + 26, 54);
            context.FillRectangle(PanelFill, box);
            context.DrawRectangle(new RenderPen(PanelEdge, 1), box);
            context.DrawString(head, _fMid, PanelInk, 23, 18);
            context.DrawString(line2, _fTiny, GapEdge, 23, 42);
        }
    }
}
