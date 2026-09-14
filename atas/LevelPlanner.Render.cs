// On-chart drawing for the Level Plan. OPTIONAL FILE.
//
// Compiled out with -p:NoRender=true, and build.bat retries that way
// automatically, so if a rendering type resolves to a different namespace on
// this ATAS build the cost is one rebuild and the indicator still works from
// its plan file. Every method signature below is from the ATAS drawing
// documentation rather than guessed: DrawString(text, font, colour, x, y),
// FillRectangle(colour, rect), DrawRectangle(pen, rect), DrawLine(pen, x1, y1,
// x2, y2), MeasureString(text, font), and ChartInfo.GetYByPrice(price, atLevel).
//
// What it draws, and why each thing is there rather than the alternative:
//
//   grey bands     the HEAVY levels. Fading those lost 12 points a trade at a
//                  33% win rate, so they are not a weaker signal, they are the
//                  wrong side of the trade. Drawn as a band rather than a line
//                  because the instruction is "do not trade in here", and a
//                  region states that where a line does not.
//
//   coloured lines the LIGHT levels, each labelled with the order itself, ready
//                  to place. Green buys, red sells. The side is decided when
//                  the plan is built from where price sat, so there is nothing
//                  to work out at the touch.
//
//   watch panel    the nearest light level and the distance to it, once inside
//                  the watch range. Deliberately the only countdown drawn: a
//                  countdown to a heavy level would invite exactly the trade
//                  the rule forbids.
//
//   touch prompt   what to do at the touch, and it is short because the honest
//                  answer is short. Aggression into the level, volume and tape
//                  speed were all tested as filters and none separated the
//                  holds from the breaks at any stop size. There is nothing to
//                  read. Take it, or skip the session.
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
        private static readonly Color BuyInk = Color.FromArgb(56, 190, 130);
        private static readonly Color SellInk = Color.FromArgb(228, 106, 82);
        private static readonly Color BandFill = Color.FromArgb(52, 132, 138, 150);
        private static readonly Color BandEdge = Color.FromArgb(130, 140, 146, 158);
        private static readonly Color BandInk = Color.FromArgb(200, 176, 182, 192);
        private static readonly Color PanelFill = Color.FromArgb(226, 16, 18, 22);
        private static readonly Color PanelEdge = Color.FromArgb(160, 110, 120, 136);
        private static readonly Color PanelInk = Color.FromArgb(232, 236, 241);
        private static readonly Color DimInk = Color.FromArgb(150, 160, 172);
        private static readonly Color WatchInk = Color.FromArgb(238, 186, 88);

        private readonly RenderFont _fSmall = new RenderFont("Segoe UI", 11);
        private readonly RenderFont _fMid = new RenderFont("Segoe UI", 12);
        private readonly RenderFont _fBig = new RenderFont("Segoe UI", 16);

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

        protected override void OnRender(RenderContext context, DrawingLayouts layout)
        {
            if (ChartInfo == null)
                return;

            // OnRender runs on the drawing thread while OnNewTrade writes from
            // the data thread. Copy everything needed under the lock; reading
            // the live list while it is being rebuilt at a session roll is a
            // race whose symptom is a crash inside the platform's paint loop.
            List<Shot> levels;
            Shot near, touch;
            decimal nearDist, price;
            DateTime touchedAt;
            lock (_sync)
            {
                levels = new List<Shot>(_levels.Count);
                foreach (var l in _levels)
                    levels.Add(Shot.Of(l));
                near = Shot.Of(Nearest);
                touch = Shot.Of(Touching);
                nearDist = NearestDist;
                price = _close;
                touchedAt = TouchedAt;
            }

            var w = ChartArea.Width;
            var h = ChartArea.Height;

            foreach (var l in levels)
            {
                int y;
                try { y = ChartInfo.GetYByPrice(l.Price, false); }
                catch { continue; }
                if (y < -60 || y > h + 60)
                    continue;

                if (l.Light)
                    DrawTradeLevel(context, l, y, w);
                else
                    DrawNoTradeBand(context, l, y, w);
            }

            DrawPanel(context, price, near, nearDist, touch, touchedAt);
        }

        private void DrawNoTradeBand(RenderContext context, Shot l, int y, int w)
        {
            var half = (int)Math.Max(3, PxPerPoint() * (double)NoTradeBandPts / 2.0);
            var rect = new Rectangle(0, y - half, w, half * 2);
            context.FillRectangle(BandFill, rect);
            context.DrawRectangle(new RenderPen(BandEdge, 1), rect);
            context.DrawString(
                "NO TRADE   " + Fmt(l.Price) + "   " + l.Weight.ToString("N0") +
                " contracts traded here",
                _fSmall, BandInk, 8, y - half + 3);
        }

        private void DrawTradeLevel(RenderContext context, Shot l, int y, int w)
        {
            var ink = l.Buy ? BuyInk : SellInk;
            context.DrawLine(new RenderPen(ink, 2), 0, y, w, y);

            var text = (l.Buy ? "BUY  " : "SELL  ") + Fmt(l.Price) +
                       "      stop " + Fmt(l.Stop) + "      target " + Fmt(l.Target);
            var size = context.MeasureString(text, _fMid);
            var box = new Rectangle(8, y - (int)size.Height - 3,
                                    (int)size.Width + 12, (int)size.Height + 4);
            context.FillRectangle(PanelFill, box);
            context.DrawString(text, _fMid, ink, 14, y - (int)size.Height - 1);
        }

        /// <summary>Pixels per index point, from two prices ten points apart.</summary>
        private double PxPerPoint()
        {
            try
            {
                var a = ChartInfo.GetYByPrice(10000m, false);
                var b = ChartInfo.GetYByPrice(10010m, false);
                var d = Math.Abs(a - b) / 10.0;
                return d > 0.02 ? d : 1.0;
            }
            catch { return 1.0; }
        }

        private static string Fmt(decimal p)
        {
            return p.ToString("N2");
        }

        private void DrawPanel(RenderContext context, decimal price, Shot near,
                               decimal nearDist, Shot touch, DateTime touchedAt)
        {
            string head, line2, line3;
            Color ink;

            if (touch != null)
            {
                var age = (int)(DateTime.Now - touchedAt).TotalSeconds;
                if (age < 0 || age > 3600)
                    age = 0;
                ink = touch.Buy ? BuyInk : SellInk;
                head = (touch.Buy ? "BUY " : "SELL ") + Fmt(touch.Price) +
                       "   TOUCHED   " + age + "s ago";
                line2 = "stop " + Fmt(touch.Stop) + "    target " + Fmt(touch.Target) +
                        "    risking $600 to make $600";
                line3 = "One position only — cancel the others. Nothing to read: " +
                        "no flow filter separated holds from breaks.";
            }
            else if (near != null && nearDist <= WatchPts)
            {
                ink = WatchInk;
                head = "WATCHING   " + (near.Buy ? "BUY " : "SELL ") +
                       Fmt(near.Price) + "   " +
                       ((double)nearDist).ToString("N1") + " pts away";
                line2 = "stop " + Fmt(near.Stop) + "    target " + Fmt(near.Target);
                line3 = "The limit should already be resting there. Do not chase it.";
            }
            else if (near != null)
            {
                ink = DimInk;
                head = "Nothing in range";
                line2 = "nearest " + (near.Buy ? "BUY " : "SELL ") + Fmt(near.Price) +
                        "   " + ((double)nearDist).ToString("N0") + " pts away";
                line3 = "Watch begins inside " +
                        ((double)WatchPts).ToString("N0") + " points.";
            }
            else
            {
                ink = DimInk;
                head = "No plan yet";
                line2 = "needs one complete previous cash session";
                line3 = "Replay yesterday once and it appears.";
            }

            var wide = Math.Max(context.MeasureString(head, _fBig).Width,
                       Math.Max(context.MeasureString(line2, _fSmall).Width,
                                context.MeasureString(line3, _fSmall).Width));
            var boxW = (int)wide + 28;
            var boxH = 82;
            var box = new Rectangle(10, 10, boxW, boxH);

            context.FillRectangle(PanelFill, box);
            context.DrawRectangle(new RenderPen(PanelEdge, 1), box);
            context.DrawString(head, _fBig, ink, 24, 18);
            context.DrawString(line2, _fSmall, PanelInk, 24, 44);
            context.DrawString(line3, _fSmall, DimInk, 24, 62);
        }

        /// <summary>An immutable copy of a level, taken under the lock.</summary>
        private sealed class Shot
        {
            public decimal Price, Stop, Target;
            public long Weight;
            public bool Light, Buy;

            public static Shot Of(Level l)
            {
                if (l == null)
                    return null;
                return new Shot
                {
                    Price = l.Price,
                    Stop = l.Stop,
                    Target = l.Target,
                    Weight = l.Weight,
                    Light = l.Light,
                    Buy = l.Buy,
                };
            }
        }
    }
}
