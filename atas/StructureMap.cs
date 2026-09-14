// Structure Map — draws the market structure read, from candles.
//
// Everything on this chart is a label for something already visible. That is
// the point: it removes the eye-strain and the hindsight, not the judgement.
// A swing is only marked once it is CONFIRMED, which is Pivot bars after the
// bar it sits on, so a label never appears on a high that is still forming.
// Nothing here repaints.
//
// What it draws:
//
//   gap          the opening gap against the previous session's close, as a
//                shaded band with the close drawn as the gap level
//   FVG          a three-bar imbalance -- bullish when a bar's low is above
//                the high two bars back. Shaded until price trades back
//                through it, then dropped.
//   HH HL LH LL  confirmed swing points, each labelled against the previous
//                swing of the same kind, which is what makes a trend readable
//   BOS          a close through the last confirmed swing high or low, drawn
//                as a horizontal line at the level that broke
//
// A note on what this is and is not. The sequence -- gap, FVG that holds,
// higher low, break of structure, enter toward the gap -- was tested on 2,680
// sessions of 5-minute bars in scripts/orderflow/gapstructure.py. Waiting for
// it beats entering blind by +0.176R (t = +2.43), so the read is real. Every
// complete version of the TRADE still lost, because the break confirms at the
// top of the leg. So this indicator marks the structure and does not print an
// order. If a setup is taken it is taken on judgement, and the chart is
// showing what is there rather than telling anybody what to do.
//
// Self-contained: candles only, no tape, no files, no dependency on the
// recorder or the level plan. Runs alongside both.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;

using ATAS.Indicators;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;

namespace Claude1.Recorders
{
    [DisplayName("Structure Map (gaps, FVG, BOS)")]
    public class StructureMap : Indicator
    {
        private const string BuildTag = "2026-09-14.structure.a";

        private static readonly Color UpInk = Color.FromArgb(56, 190, 130);
        private static readonly Color DownInk = Color.FromArgb(228, 106, 82);
        private static readonly Color GapFill = Color.FromArgb(38, 238, 186, 88);
        private static readonly Color GapEdge = Color.FromArgb(150, 238, 186, 88);
        private static readonly Color FvgUp = Color.FromArgb(34, 56, 190, 130);
        private static readonly Color FvgDown = Color.FromArgb(34, 228, 106, 82);
        private static readonly Color BosInk = Color.FromArgb(200, 200, 210, 226);
        private static readonly Color PanelFill = Color.FromArgb(226, 16, 18, 22);
        private static readonly Color PanelEdge = Color.FromArgb(160, 110, 120, 136);
        private static readonly Color PanelInk = Color.FromArgb(232, 236, 241);
        private static readonly Color DimInk = Color.FromArgb(150, 160, 172);

        private readonly RenderFont _fTiny = new RenderFont("Segoe UI", 10);
        private readonly RenderFont _fSmall = new RenderFont("Segoe UI", 11);
        private readonly RenderFont _fBig = new RenderFont("Segoe UI", 15);

        private readonly object _sync = new object();

        [DisplayName("Pivot strength (bars each side)")]
        public int Pivot { get; set; } = 2;

        [DisplayName("Show fair value gaps")]
        public bool ShowFvg { get; set; } = true;

        [DisplayName("Show the opening gap")]
        public bool ShowGap { get; set; } = true;

        [DisplayName("Show swing labels")]
        public bool ShowSwings { get; set; } = true;

        [DisplayName("Show break of structure")]
        public bool ShowBos { get; set; } = true;

        [DisplayName("Session start hour (platform clock)")]
        public int SessionHour { get; set; } = 13;

        [DisplayName("Session start minute")]
        public int SessionMinute { get; set; } = 30;

        private sealed class Swing
        {
            public int Bar;
            public decimal Price;
            public bool IsHigh;
            public string Label;      // HH, HL, LH, LL
        }

        private sealed class Fvg
        {
            public int Bar;           // the third bar of the imbalance
            public decimal Top, Bottom;
            public bool Up;
            public int FilledAt = -1; // bar that traded back through it
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
        private bool _haveGap;
        private int _lastBuilt = -1;

        public StructureMap()
        {
            // Same shape as the recorder and the level plan, which both build
            // on this platform. base(true) and an unguarded DataSeries touch
            // are two ways to lose a build for no gain.
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

        /// <summary>
        /// Rebuild the whole structure from the start of the current session.
        /// Cheap -- a cash session is a few hundred bars -- and it means the
        /// state cannot drift out of step with the bars after a reload.
        /// </summary>
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
                    _haveGap = true;
                    _swings.Clear();
                    _fvgs.Clear();
                    _bos.Clear();
                }
            }
            if (_sessionStart < 0 || bar == _lastBuilt)
                return;
            _lastBuilt = bar;
            lock (_sync)
                Rebuild(bar);
        }

        private void Rebuild(int last)
        {
            _swings.Clear();
            _fvgs.Clear();
            _bos.Clear();

            var k = Pivot < 1 ? 1 : Pivot;
            var from = _sessionStart;

            // --- swings. A pivot at i is only knowable at i+k, so the loop
            // stops k bars short of the last bar and never labels a forming high.
            decimal lastHigh = 0m, lastLow = 0m;
            var haveHigh = false;
            var haveLow = false;
            for (var i = from + k; i <= last - k; i++)
            {
                var c = GetCandle(i);
                var isHigh = true;
                var isLow = true;
                for (var j = i - k; j <= i + k; j++)
                {
                    if (j == i)
                        continue;
                    var o = GetCandle(j);
                    if (o.High > c.High) isHigh = false;
                    if (o.Low < c.Low) isLow = false;
                }
                if (isHigh)
                {
                    var lbl = !haveHigh ? "H" : (c.High > lastHigh ? "HH" : "LH");
                    _swings.Add(new Swing
                    {
                        Bar = i, Price = c.High, IsHigh = true, Label = lbl
                    });
                    lastHigh = c.High;
                    haveHigh = true;
                }
                if (isLow)
                {
                    var lbl = !haveLow ? "L" : (c.Low > lastLow ? "HL" : "LL");
                    _swings.Add(new Swing
                    {
                        Bar = i, Price = c.Low, IsHigh = false, Label = lbl
                    });
                    lastLow = c.Low;
                    haveLow = true;
                }
            }

            // --- fair value gaps: bar i's low above bar i-2's high, or the
            // mirror. Marked filled once price trades back through the far side.
            for (var i = from + 2; i <= last; i++)
            {
                var a = GetCandle(i - 2);
                var c = GetCandle(i);
                Fvg g = null;
                if (c.Low > a.High)
                    g = new Fvg { Bar = i, Bottom = a.High, Top = c.Low, Up = true };
                else if (c.High < a.Low)
                    g = new Fvg { Bar = i, Bottom = c.High, Top = a.Low, Up = false };
                if (g == null)
                    continue;
                for (var j = i + 1; j <= last; j++)
                {
                    var f = GetCandle(j);
                    if ((g.Up && f.Low <= g.Bottom) || (!g.Up && f.High >= g.Top))
                    {
                        g.FilledAt = j;
                        break;
                    }
                }
                _fvgs.Add(g);
            }

            // --- break of structure: a CLOSE through the most recent confirmed
            // swing in that direction. Confirmation timing matters -- the swing
            // must have been knowable (bar + k) before the close that breaks it.
            for (var i = from; i <= last; i++)
            {
                var c = GetCandle(i);
                Swing hi = null, lo = null;
                foreach (var s in _swings)
                {
                    if (s.Bar + k > i)
                        continue;                 // not yet confirmed at bar i
                    if (s.IsHigh) hi = s; else lo = s;
                }
                if (hi != null && c.Close > hi.Price &&
                    !_bos.Exists(b => b.Up && b.Price == hi.Price))
                    _bos.Add(new Bos { Bar = i, Price = hi.Price, Up = true });
                if (lo != null && c.Close < lo.Price &&
                    !_bos.Exists(b => !b.Up && b.Price == lo.Price))
                    _bos.Add(new Bos { Bar = i, Price = lo.Price, Up = false });
            }
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
            decimal prevClose, sessionOpen;
            bool haveGap;
            lock (_sync)
            {
                swings = new List<Swing>(_swings);
                fvgs = new List<Fvg>(_fvgs);
                bos = new List<Bos>(_bos);
                prevClose = _prevClose;
                sessionOpen = _sessionOpen;
                haveGap = _haveGap;
            }

            var w = ChartArea.Width;
            var h = ChartArea.Height;

            if (ShowGap && haveGap && prevClose != sessionOpen)
                DrawGap(context, prevClose, sessionOpen, w, h);
            if (ShowFvg)
                foreach (var g in fvgs)
                    DrawFvg(context, g, h);
            if (ShowBos)
                foreach (var b in bos)
                    DrawBos(context, b, w);
            if (ShowSwings)
                foreach (var s in swings)
                    DrawSwing(context, s);

            DrawPanel(context, swings, bos, prevClose, sessionOpen, haveGap);
        }

        private void DrawGap(RenderContext context, decimal prevClose,
                             decimal open, int w, int h)
        {
            int y1, y2;
            try
            {
                y1 = ChartInfo.GetYByPrice(prevClose, false);
                y2 = ChartInfo.GetYByPrice(open, false);
            }
            catch { return; }
            var top = Math.Min(y1, y2);
            var hh = Math.Abs(y2 - y1);
            if (hh < 1 || top > h || top + hh < 0)
                return;

            var rect = new Rectangle(0, top, w, hh);
            context.FillRectangle(GapFill, rect);
            context.DrawLine(new RenderPen(GapEdge, 1), 0, y1, w, y1);

            var pts = Math.Abs(open - prevClose);
            var text = "GAP " + (open > prevClose ? "UP " : "DOWN ") +
                       ((double)pts).ToString("N1") + " pts    gap level " +
                       prevClose.ToString("N2");
            context.DrawString(text, _fTiny, GapEdge, 8, y1 + 3);
        }

        private void DrawFvg(RenderContext context, Fvg g, int h)
        {
            int yt, yb, x0, x1;
            try
            {
                yt = ChartInfo.GetYByPrice(g.Top, false);
                yb = ChartInfo.GetYByPrice(g.Bottom, false);
                x0 = X(g.Bar);
                x1 = g.FilledAt >= 0 ? X(g.FilledAt) : ChartArea.Width;
            }
            catch { return; }
            if (x1 <= x0)
                x1 = x0 + 2;
            var top = Math.Min(yt, yb);
            var hh = Math.Abs(yb - yt);
            if (hh < 1 || top > h || top + hh < 0)
                return;
            context.FillRectangle(g.Up ? FvgUp : FvgDown,
                                  new Rectangle(x0, top, x1 - x0, hh));
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
            var pen = new RenderPen(BosInk, 1);
            context.DrawLine(pen, Math.Max(0, x - 60), y, w, y);
            context.DrawString("BOS " + (b.Up ? "up" : "down"), _fTiny,
                               b.Up ? UpInk : DownInk, x + 4, y - 14);
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
            var yy = s.IsHigh ? y - (int)size.Height - 4 : y + 4;
            context.DrawString(s.Label, _fTiny, ink, x - (int)size.Width / 2, yy);
        }

        private void DrawPanel(RenderContext context, List<Swing> swings,
                               List<Bos> bos, decimal prevClose,
                               decimal open, bool haveGap)
        {
            string head;
            if (haveGap && prevClose != open)
            {
                var pts = Math.Abs(open - prevClose);
                head = "Gap " + (open > prevClose ? "up " : "down ") +
                       ((double)pts).ToString("N1") + " pts   level " +
                       prevClose.ToString("N2");
            }
            else
            {
                head = "No gap";
            }

            // The last two swings say what the structure is doing right now,
            // in the words the chart is already labelled in.
            var trail = "";
            for (var i = Math.Max(0, swings.Count - 4); i < swings.Count; i++)
                trail += (trail.Length > 0 ? " -> " : "") + swings[i].Label;
            if (trail.Length == 0)
                trail = "no confirmed swings yet";

            var lastBos = bos.Count > 0 ? bos[bos.Count - 1] : null;
            var line3 = lastBos == null
                ? "no break of structure yet"
                : "last BOS " + (lastBos.Up ? "up through " : "down through ") +
                  lastBos.Price.ToString("N2");

            var wide = Math.Max(context.MeasureString(head, _fBig).Width,
                       Math.Max(context.MeasureString(trail, _fSmall).Width,
                                context.MeasureString(line3, _fSmall).Width));
            var box = new Rectangle(10, 96, (int)wide + 28, 78);

            context.FillRectangle(PanelFill, box);
            context.DrawRectangle(new RenderPen(PanelEdge, 1), box);
            context.DrawString(head, _fBig, PanelInk, 24, 104);
            context.DrawString(trail, _fSmall, DimInk, 24, 128);
            context.DrawString(line3, _fSmall, DimInk, 24, 146);
        }
    }
}
