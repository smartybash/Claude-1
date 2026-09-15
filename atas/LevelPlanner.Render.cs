// On-chart drawing for the levels. OPTIONAL FILE.
//
// Compiled out with -p:NoRender=true, and build.bat retries that way
// automatically, so if a rendering type resolves to a different namespace on
// this ATAS build the cost is one rebuild and the plan file still gets written.
// Every signature below is from the ATAS drawing documentation rather than
// guessed: DrawString(text, font, colour, x, y), FillRectangle(colour, rect),
// DrawRectangle(pen, rect), DrawLine(pen, x1, y1, x2, y2), MeasureString(text,
// font), and ChartInfo.GetYByPrice(price, atLevel).
//
// What it draws: a labelled line at each reference price, and a small panel
// naming the nearest one.
//
// What it deliberately does NOT draw any more: buy and sell brackets. An
// earlier version printed an order at every "light" level. That rule came from
// 198 touches and did not survive 3,682 -- fading a level wins 49.1%, and the
// light/heavy split ran backwards, so the lightest third was the worst thing
// to fade rather than the best. Drawing an order the data does not support is
// worse than drawing nothing, so the levels are now reference prices and the
// decision is left where it belongs.
using System;
using System.Collections.Generic;
using System.Drawing;

using ATAS.Indicators;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;

namespace Claude1.Recorders
{
    public partial class LevelPlanner
    {
        // One colour per family, so the chart reads at a glance: prior day in
        // amber, value area in blue, overnight sessions in grey-green.
        private static readonly Color PriorInk = Color.FromArgb(238, 186, 88);
        private static readonly Color ValueInk = Color.FromArgb(110, 168, 232);
        private static readonly Color AsiaInk = Color.FromArgb(146, 186, 160);
        private static readonly Color LdnInk = Color.FromArgb(178, 160, 200);
        private static readonly Color PanelFill = Color.FromArgb(226, 16, 18, 22);
        private static readonly Color PanelEdge = Color.FromArgb(160, 110, 120, 136);
        private static readonly Color PanelInk = Color.FromArgb(232, 236, 241);
        private static readonly Color DimInk = Color.FromArgb(150, 160, 172);

        private readonly RenderFont _fSmall = new RenderFont("Segoe UI", 11);
        private readonly RenderFont _fMid = new RenderFont("Segoe UI", 12);
        private readonly RenderFont _fBig = new RenderFont("Segoe UI", 15);

        /// <summary>
        /// Called from the constructor in the main file. Both the call and this
        /// body vanish when the file is compiled out.
        /// </summary>
        partial void ConfigureRendering()
        {
            RenderAvailable = true;
            EnableCustomDrawing = true;
            SubscribeToDrawingEvents(DrawingLayouts.Final | DrawingLayouts.LatestBar);
        }

        private static Color InkFor(Kind k)
        {
            switch (k)
            {
                case Kind.Asia: return AsiaInk;
                case Kind.London: return LdnInk;
                case Kind.ValueArea: return ValueInk;
                default: return PriorInk;
            }
        }

        protected override void OnRender(RenderContext context, DrawingLayouts layout)
        {
            if (ChartInfo == null)
                return;

            // OnRender runs on the drawing thread while OnNewTrade writes from
            // the data thread. Copy everything needed under the lock; reading
            // the live list while it is being rebuilt at a session roll is a
            // race whose symptom is a crash inside the platform's paint loop.
            List<Shot> levels;
            Shot near;
            decimal nearDist, price;
            long cvd, d5, svol;
            bool cvdFull;
            lock (_sync)
            {
                cvd = _cvd;
                d5 = _delta5;
                svol = _sessionVol;
                cvdFull = _cvdComplete;
                levels = new List<Shot>(_levels.Count);
                foreach (var l in _levels)
                    levels.Add(Shot.Of(l));
                near = Shot.Of(Nearest);
                nearDist = NearestDist;
                price = _close;
            }

            var w = ChartArea.Width;
            var h = ChartArea.Height;

            foreach (var l in levels)
            {
                int y;
                try { y = ChartInfo.GetYByPrice(l.Price, false); }
                catch { continue; }
                if (y < -40 || y > h + 40)
                    continue;
                DrawLevel(context, l, y, w);
            }

            DrawPanel(context, price, near, nearDist, cvd, d5, svol, cvdFull);
        }

        private void DrawLevel(RenderContext context, Shot l, int y, int w)
        {
            var ink = InkFor(l.Group);
            context.DrawLine(new RenderPen(ink, 1), 0, y, w, y);

            var text = l.Name + "   " + Fmt(l.Price);
            var size = context.MeasureString(text, _fSmall);
            var box = new Rectangle(6, y - (int)size.Height - 2,
                                    (int)size.Width + 10, (int)size.Height + 3);
            context.FillRectangle(PanelFill, box);
            context.DrawString(text, _fSmall, ink, 11, y - (int)size.Height - 1);
        }

        private static string Fmt(decimal p)
        {
            return p.ToString("N2");
        }

        private void DrawPanel(RenderContext context, decimal price, Shot near,
                               decimal nearDist, long cvd, long d5, long svol,
                               bool cvdFull)
        {
            string head, line2;
            if (near != null)
            {
                head = "Nearest: " + near.Name + "  " + Fmt(near.Price) +
                       "   " + ((double)nearDist).ToString("N1") + " pts away";
                line2 = "last " + Fmt(price);
            }
            else
            {
                head = "No levels yet";
                line2 = "needs one complete previous cash session";
            }

            // Session CVD as a share of the day's volume. Raw contracts are not
            // comparable across the session -- the same figure means different
            // things at 13:45 and at 19:30 -- and the share is the form that
            // separated anything when it was tested.
            var share = svol > 0 ? 100.0 * cvd / svol : 0.0;
            var line3 = "CVD " + (cvd >= 0 ? "+" : "") + cvd.ToString("N0") +
                        "  (" + (share >= 0 ? "+" : "") + share.ToString("N2") +
                        "% of session)" + (cvdFull ? "" : "  PARTIAL") +
                        "      5m delta " + (d5 >= 0 ? "+" : "") + d5.ToString("N0");

            var wide = Math.Max(context.MeasureString(head, _fBig).Width,
                       Math.Max(context.MeasureString(line2, _fSmall).Width,
                                context.MeasureString(line3, _fSmall).Width));
            var box = new Rectangle(10, 10, (int)wide + 28, 78);

            context.FillRectangle(PanelFill, box);
            context.DrawRectangle(new RenderPen(PanelEdge, 1), box);
            context.DrawString(head, _fBig, PanelInk, 24, 18);
            context.DrawString(line2, _fSmall, DimInk, 24, 42);
            context.DrawString(line3, _fSmall, DimInk, 24, 60);
        }

        /// <summary>An immutable copy of a level, taken under the lock.</summary>
        private sealed class Shot
        {
            public string Name;
            public decimal Price;
            public long Weight;
            public Kind Group;

            public static Shot Of(Level l)
            {
                if (l == null)
                    return null;
                return new Shot
                {
                    Name = l.Name,
                    Price = l.Price,
                    Weight = l.Weight,
                    Group = l.Group,
                };
            }
        }
    }
}
