// IB 1R — the frozen candidate, shown live so out-of-sample data can be
// collected. PRINTS ZONES AND LEVELS ONLY. IT NEVER PLACES AN ORDER.
//
// ====================================================================
//  READ THIS FIRST. THIS RULE FAILED ITS OWN SCREEN.
// ====================================================================
//
// The retroactive concentration audit re-ran every historical pass under
// max(10, ceil(0.10n)) instead of the old "remove the best 1%". On 685 QQQ
// trades this rule returns +0.0612 R a trade (t = +2.23, PF 1.22, 5 of 6
// years) and lands at -0.0433 R once the top decile is removed. The top 69
// trades carry 164% of total R; the other 616 lose money in aggregate.
//
// The related-instrument check put the pooled non-QQQ estimate at +0.0269
// with an interval spanning zero, and XLK and EFA both fail the same
// concentration test.
//
// So this is a SMALL LIVE ALLOCATION TO GATHER OUT-OF-SAMPLE DATA. It is not
// a validated strategy and must not be sized as one. The live log is the
// deliverable; the P&L is not.
//
// ====================================================================
//  THE FROZEN RULE, reproduced exactly from reopen_study.test1, seq == 1
// ====================================================================
//
//   IB          09:30-10:30 ET. Bars with 0 <= minutes-from-open < 60.
//   IBH / IBL   high and low of that window, with the bar that made each.
//   FIRST       whichever extreme printed first. If both are on the SAME
//               bar the session is skipped -- the backtest cannot tell
//               which came first inside a bar, so neither can this.
//   EXPECTED    low formed first  -> expect break UP   -> level = IBH
//               high formed first -> expect break DOWN -> level = IBL
//   EZ          100 * |close_10:30 - expected level| / (IBH - IBL)
//               0% sits at the EXPECTED BREAK side, 100% at the side that
//               formed first.
//   QUALIFIED   EZ < 25. The backtest's test is `if ez >= 25: continue`.
//   INVALIDATED the OPPOSITE boundary (the stop level) is touched before
//               the expected level is broken. The frozen rule takes no
//               trade -- the stop was violated before entry.
//   ENTRY       first bar at or after 10:30 whose high exceeds the expected
//               level (or low breaks below it, when short). Fill is
//               max(level, bar open) long, min(level, bar open) short.
//   STOP        the opposite IB boundary.
//   TARGET      1R = fill +/- 1.0 * |fill - stop|.
//   FLAT        16:00 ET.
//
// ====================================================================
//  TWO THINGS THAT WILL MAKE LIVE DIFFER FROM THE BACKTEST. BOTH REAL.
// ====================================================================
//
//  1  THE BACKTEST EXCLUDES THE ENTRY BAR from the exit search
//     (run_trade scans from i+1). A stop touched on the entry bar is not
//     counted there. Live, you can be stopped on the entry bar. This
//     indicator follows the BACKTEST convention so the numbers reconcile,
//     and flags the bar when it would have mattered. Log what actually
//     happened, not what the indicator says, and note the divergence.
//
//  2  BAR RESOLUTION IS PART OF THE RULE. IBH/IBL and, more importantly,
//     WHICH ONE FORMED FIRST are properties of the bar grid. The study ran
//     on 1-MINUTE bars. On any other period this is a different rule. The
//     panel turns red if the chart is not 1-minute.
//
// ====================================================================
//  DAYLIGHT SAVING. CHECK THIS EVERY MARCH AND NOVEMBER.
// ====================================================================
//
//  The defaults below are 13:30 platform time, which is 09:30 ET only while
//  New York is on EDT (summer). On EST (winter) 09:30 ET is 14:30 platform
//  time. If the platform clock is UTC you MUST move the start to 14:30 and
//  the flat to 21:00 when the US falls back, or the rule silently measures
//  the wrong hour. The panel always prints the window it is actually using
//  and the first IB candle's timestamp so this is visible rather than
//  assumed. Setting the platform clock to New York time avoids the problem.
using System;
using System.ComponentModel;
using System.Drawing;

using ATAS.Indicators;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;

namespace Claude1.Recorders
{
    [DisplayName("IB 1R (frozen candidate — display only)")]
    public class IbOneR : Indicator
    {
        private const string BuildTag = "2026-09-20.ib1r.a";

        private static readonly Color LongInk = Color.FromArgb(56, 190, 130);
        private static readonly Color ShortInk = Color.FromArgb(228, 106, 82);
        private static readonly Color IbInk = Color.FromArgb(210, 138, 176, 232);
        private static readonly Color BandFill = Color.FromArgb(46, 238, 186, 88);
        private static readonly Color TargetInk = Color.FromArgb(200, 120, 200, 240);
        private static readonly Color StopInk = Color.FromArgb(210, 228, 106, 82);
        private static readonly Color FlatInk = Color.FromArgb(150, 160, 172);
        private static readonly Color PanelFill = Color.FromArgb(236, 16, 18, 22);
        private static readonly Color PanelEdge = Color.FromArgb(150, 110, 120, 136);
        private static readonly Color PanelInk = Color.FromArgb(236, 240, 245);
        private static readonly Color WarnInk = Color.FromArgb(238, 186, 88);
        private static readonly Color BadInk = Color.FromArgb(240, 120, 110);

        private readonly RenderFont _fBig = new RenderFont("Segoe UI", 16);
        private readonly RenderFont _fMid = new RenderFont("Segoe UI", 12);
        private readonly RenderFont _fTiny = new RenderFont("Segoe UI", 10);

        private readonly object _sync = new object();

        // ------------------------------------------------------- settings --

        [DisplayName("IB start hour (platform clock)")]
        public int SessionHour { get; set; } = 13;

        [DisplayName("IB start minute")]
        public int SessionMinute { get; set; } = 30;

        [DisplayName("IB length, minutes")]
        public int IbMinutes { get; set; } = 60;

        [DisplayName("Forced flat hour (platform clock)")]
        public int FlatHour { get; set; } = 20;

        [DisplayName("Forced flat minute")]
        public int FlatMinute { get; set; } = 0;

        [DisplayName("Ending-zone qualifying band, percent")]
        public decimal EzBand { get; set; } = 25m;

        [DisplayName("Target, in R")]
        public decimal TargetR { get; set; } = 1.0m;

        [DisplayName("Draw levels on the chart")]
        public bool DrawLevels { get; set; } = true;

        // ------------------------------------------------- session state --

        private enum St { Forming, Qualified, Armed, Triggered, Invalidated, NoTrade }

        private int _sessionStart = -1;
        private int _lastBar = -1;

        private decimal _ibh, _ibl;
        private int _ibhBar = -1, _iblBar = -1;
        private DateTime _ibhTime, _iblTime, _firstIbTime;
        private int _ibBars;
        private bool _ibDone;
        private bool _sameBar;                 // both extremes on one bar

        private bool _highFirst;
        private decimal _close1030, _ez, _range;
        private decimal _expLvl, _stopLvl, _risk, _target, _fill;
        private int _dir;                      // +1 long, -1 short
        private St _state = St.Forming;
        private string _why = "";

        private int _qualBar = -1;
        private int _entryBar = -1;
        private DateTime _entryTime;
        private bool _exited;
        private decimal _exitPx;
        private DateTime _exitTime;
        private string _exitWhy = "";
        private decimal _realisedR;
        private bool _entryBarWouldHaveStopped;
        private bool _ambiguousBar;

        public IbOneR()
        {
            try { DataSeries[0].IsHidden = true; } catch { }
            EnableCustomDrawing = true;
            SubscribeToDrawingEvents(DrawingLayouts.Final | DrawingLayouts.LatestBar);
        }

        // --------------------------------------------------------- clock --

        private int OpenMins => SessionHour * 60 + SessionMinute;
        private int FlatMins => FlatHour * 60 + FlatMinute;

        private int MinsFromOpen(DateTime t)
        {
            return (t.Hour * 60 + t.Minute) - OpenMins;
        }

        private bool IsSessionOpen(int i)
        {
            if (i == 0)
                return true;
            var a = GetCandle(i - 1).Time;
            var b = GetCandle(i).Time;
            if (a.Date != b.Date)
                return true;
            return (a.Hour * 60 + a.Minute) < OpenMins
                && (b.Hour * 60 + b.Minute) >= OpenMins;
        }

        private void ResetSession(int bar)
        {
            _sessionStart = bar;
            _ibh = 0m; _ibl = 0m;
            _ibhBar = -1; _iblBar = -1;
            _ibBars = 0; _ibDone = false; _sameBar = false;
            _highFirst = false;
            _close1030 = 0m; _ez = 0m; _range = 0m;
            _expLvl = 0m; _stopLvl = 0m; _risk = 0m; _target = 0m; _fill = 0m;
            _dir = 0;
            _state = St.Forming; _why = "";
            _qualBar = -1; _entryBar = -1; _exited = false; _exitPx = 0m; _exitWhy = "";
            _realisedR = 0m;
            _entryBarWouldHaveStopped = false; _ambiguousBar = false;
        }

        // ----------------------------------------------------- the rule ---

        protected override void OnCalculate(int bar, decimal value)
        {
            if (bar == _lastBar)
                return;
            _lastBar = bar;

            if (IsSessionOpen(bar))
                lock (_sync) ResetSession(bar);
            if (_sessionStart < 0)
                return;

            var c = GetCandle(bar);
            var m = MinsFromOpen(c.Time);
            if (m < 0)
                return;

            lock (_sync)
            {
                if (m < IbMinutes)
                {
                    BuildIb(bar, c);
                    return;
                }

                if (!_ibDone)
                    CloseIb(bar);

                if (_state == St.NoTrade || _state == St.Invalidated)
                    return;

                var flat = (c.Time.Hour * 60 + c.Time.Minute) >= FlatMins;

                // QUALIFIED is the instant the IB closes; ARMED is every bar
                // after it while the expected level is still unbroken.
                if (_state == St.Qualified && bar > _qualBar)
                    _state = St.Armed;

                if (_state == St.Qualified || _state == St.Armed)
                {
                    // The frozen rule's pre-entry invalidation: the opposite
                    // boundary is violated before the expected level breaks.
                    var opp = _dir > 0 ? c.Low < _stopLvl : c.High > _stopLvl;
                    var brk = _dir > 0 ? c.High > _expLvl : c.Low < _expLvl;
                    if (opp && !brk)
                    {
                        _state = St.Invalidated;
                        _why = "opposite IB boundary broke first — the stop "
                             + "level was violated before entry";
                        return;
                    }
                    if (opp && brk)
                    {
                        // Both on one bar. The backtest compares FIRST
                        // occurrence by bar index, so a tie on the same bar
                        // resolves to the entry. Flagged, because it is a
                        // genuine ambiguity in the live tape.
                        _ambiguousBar = true;
                    }
                    if (brk)
                    {
                        Enter(bar, c);
                        return;
                    }
                    if (flat)
                    {
                        _state = St.NoTrade;
                        _why = "no break of the expected level before the flat time";
                    }
                    return;
                }

                if (_state == St.Triggered && !_exited)
                {
                    // ENTRY BAR EXCLUDED, matching run_trade's scan from i+1.
                    if (bar == _entryBar)
                        return;
                    Manage(bar, c, flat);
                }
            }
        }

        private void BuildIb(int bar, IndicatorCandle c)
        {
            if (_ibBars == 0)
            {
                _firstIbTime = c.Time;
                _ibh = c.High; _ibl = c.Low;
                _ibhBar = bar; _iblBar = bar;
                _ibhTime = c.Time; _iblTime = c.Time;
            }
            else
            {
                if (c.High > _ibh) { _ibh = c.High; _ibhBar = bar; _ibhTime = c.Time; }
                if (c.Low < _ibl) { _ibl = c.Low; _iblBar = bar; _iblTime = c.Time; }
            }
            _close1030 = c.Close;           // the last IB close is the 10:30 close
            _ibBars++;
        }

        private void CloseIb(int bar)
        {
            _ibDone = true;

            if (_ibBars < 30)
            {
                _state = St.NoTrade;
                _why = "fewer than 30 IB bars — the backtest skips this session";
                return;
            }
            if (_ibhBar == _iblBar)
            {
                _sameBar = true;
                _state = St.NoTrade;
                _why = "both IB extremes on the same bar — which formed first "
                     + "is undecidable, and the backtest skips it";
                return;
            }
            _range = _ibh - _ibl;
            if (_range <= 0m)
            {
                _state = St.NoTrade;
                _why = "IB range is zero";
                return;
            }

            _highFirst = _ibhBar < _iblBar;
            _dir = _highFirst ? -1 : 1;
            _expLvl = _highFirst ? _ibl : _ibh;
            _stopLvl = _highFirst ? _ibh : _ibl;
            _ez = 100m * Math.Abs(_close1030 - _expLvl) / _range;

            if (_ez >= EzBand)
            {
                _state = St.NoTrade;
                _why = "ending zone " + _ez.ToString("N1") + "% is outside the 0–"
                     + EzBand.ToString("N0") + "% band";
                return;
            }
            _state = St.Qualified;          // ARMED from the next bar on
            _qualBar = bar;
            _why = "qualified — waiting for the expected level to break";
        }

        private void Enter(int bar, IndicatorCandle c)
        {
            _fill = _dir > 0 ? Math.Max(_expLvl, c.Open)
                             : Math.Min(_expLvl, c.Open);
            _risk = Math.Abs(_fill - _stopLvl);
            if (_risk <= 0m)
            {
                _state = St.NoTrade;
                _why = "risk computed as zero";
                return;
            }
            _target = _fill + _dir * TargetR * _risk;
            _entryBar = bar;
            _entryTime = c.Time;
            _state = St.Triggered;
            _why = "entered on the break of the expected level";

            // Backtest excludes this bar. Record whether it mattered.
            _entryBarWouldHaveStopped =
                _dir > 0 ? c.Low <= _stopLvl : c.High >= _stopLvl;
        }

        private void Manage(int bar, IndicatorCandle c, bool flat)
        {
            var st = _dir > 0 ? c.Low <= _stopLvl : c.High >= _stopLvl;
            var ht = _dir > 0 ? c.High >= _target : c.Low <= _target;
            if (st && ht)
                _ambiguousBar = true;

            if (st)
            {
                // honest fill: a gap through the stop fills at the open
                _exitPx = _dir > 0 ? Math.Min(_stopLvl, c.Open)
                                   : Math.Max(_stopLvl, c.Open);
                Close(bar, c, "stop");
                return;
            }
            if (ht)
            {
                _exitPx = _target;
                Close(bar, c, "target");
                return;
            }
            if (flat)
            {
                _exitPx = c.Close;
                Close(bar, c, "flat 16:00");
            }
        }

        private void Close(int bar, IndicatorCandle c, string why)
        {
            _exited = true;
            _exitTime = c.Time;
            _exitWhy = why;
            _realisedR = _risk > 0m ? _dir * (_exitPx - _fill) / _risk : 0m;
        }

        // --------------------------------------------------------- render --

        private string StateName()
        {
            switch (_state)
            {
                case St.Forming: return "FORMING";
                case St.Qualified: return "QUALIFIED";
                case St.Armed: return "ARMED";
                case St.Triggered: return "TRIGGERED";
                case St.Invalidated: return "INVALIDATED";
                default: return "NO TRADE";
            }
        }

        private Color StateInk()
        {
            if (_state == St.Invalidated || _state == St.NoTrade) return FlatInk;
            if (_state == St.Forming) return WarnInk;
            return _dir > 0 ? LongInk : ShortInk;
        }

        private int ChartMinutes()
        {
            try
            {
                if (ChartInfo == null) return -1;
                var a = GetCandle(Math.Max(1, CurrentBar - 1)).Time;
                var b = GetCandle(Math.Max(2, CurrentBar)).Time;
                var d = (int)Math.Round((b - a).TotalMinutes);
                return d > 0 ? d : -1;
            }
            catch { return -1; }
        }

        private void HLine(RenderContext ctx, decimal price, Color ink, int w,
                           string label)
        {
            if (price <= 0m) return;
            int y;
            try { y = ChartInfo.GetYByPrice(price, false); }
            catch { return; }
            if (y == int.MinValue) return;
            ctx.DrawLine(new RenderPen(ink, w), 0, y, ChartArea.Width, y);
            if (!string.IsNullOrEmpty(label))
                ctx.DrawString(label, _fTiny, ink, 8, y - 14);
        }

        protected override void OnRender(RenderContext context, DrawingLayouts layout)
        {
            if (ChartInfo == null || _sessionStart < 0)
                return;

            decimal ibh, ibl, ez, expLvl, stopLvl, risk, target, fill, c1030;
            bool ibDone, highFirst, exited, sameBar;
            int dir, ibBars;
            St state;
            string why, exitWhy;
            decimal realisedR;
            DateTime ibhT, iblT, firstT;

            lock (_sync)
            {
                ibh = _ibh; ibl = _ibl; ez = _ez; expLvl = _expLvl;
                stopLvl = _stopLvl; risk = _risk; target = _target; fill = _fill;
                c1030 = _close1030; ibDone = _ibDone; highFirst = _highFirst;
                exited = _exited; sameBar = _sameBar; dir = _dir;
                ibBars = _ibBars; state = _state; why = _why; exitWhy = _exitWhy;
                realisedR = _realisedR; ibhT = _ibhTime; iblT = _iblTime;
                firstT = _firstIbTime;
            }

            if (DrawLevels && ibh > 0m)
            {
                HLine(context, ibh, IbInk, 2,
                      "IBH " + ibh.ToString("N2")
                      + (ibDone && !sameBar && highFirst ? "  ← FORMED FIRST "
                         + ibhT.ToString("HH:mm") : ""));
                HLine(context, ibl, IbInk, 2,
                      "IBL " + ibl.ToString("N2")
                      + (ibDone && !sameBar && !highFirst ? "  ← FORMED FIRST "
                         + iblT.ToString("HH:mm") : ""));

                if (ibDone && !sameBar && expLvl > 0m)
                {
                    // the qualifying band: 0% at the expected break side
                    var far = expLvl - dir * (EzBand / 100m) * (ibh - ibl);
                    int y1, y2;
                    try
                    {
                        y1 = ChartInfo.GetYByPrice(expLvl, false);
                        y2 = ChartInfo.GetYByPrice(far, false);
                    }
                    catch { y1 = y2 = int.MinValue; }
                    if (y1 != int.MinValue && y2 != int.MinValue)
                    {
                        var top = Math.Min(y1, y2);
                        var h = Math.Abs(y2 - y1);
                        if (h > 0)
                            context.FillRectangle(BandFill,
                                new Rectangle(0, top, ChartArea.Width, h));
                        context.DrawString(
                            "0–" + EzBand.ToString("N0") + "% qualifying band",
                            _fTiny, WarnInk, 8, top + 2);
                    }
                    if (state == St.Triggered)
                    {
                        HLine(context, stopLvl, StopInk, 2,
                              "STOP " + stopLvl.ToString("N2"));
                        HLine(context, target, TargetInk, 2,
                              TargetR.ToString("N1") + "R TARGET "
                              + target.ToString("N2"));
                        HLine(context, fill, PanelInk, 1,
                              "FILL " + fill.ToString("N2"));
                    }
                }
            }

            // ------------------------------------------------- the panel --
            var cm = ChartMinutes();
            var head = StateName();
            if (state == St.Triggered && exited)
                head += "   exited " + exitWhy + "   R = " + realisedR.ToString("N3");

            var l1 = ibDone
                ? "IBH " + ibh.ToString("N2") + "   IBL " + ibl.ToString("N2")
                  + "   range " + (ibh - ibl).ToString("N2")
                  + "   bars " + ibBars
                : "IB forming   bars " + ibBars + "   IBH " + ibh.ToString("N2")
                  + "   IBL " + ibl.ToString("N2");

            var l2 = ibDone && !sameBar
                ? (highFirst ? "HIGH formed first " + ibhT.ToString("HH:mm")
                               + "  (low " + iblT.ToString("HH:mm") + ")"
                             : "LOW formed first " + iblT.ToString("HH:mm")
                               + "  (high " + ibhT.ToString("HH:mm") + ")")
                  + "   →  expect break " + (dir > 0 ? "UP" : "DOWN")
                : (sameBar ? "both extremes on one bar" : "which formed first: pending");

            var l3 = ibDone && !sameBar
                ? "10:30 close " + c1030.ToString("N2")
                  + "   EZ " + ez.ToString("N1") + "%"
                  + "   " + (ez < EzBand ? "QUALIFIED" : "NOT QUALIFIED")
                  + "   (band 0–" + EzBand.ToString("N0") + "%)"
                : "ending zone: pending the 10:30 close";

            var l4 = (state == St.Qualified || state == St.Armed
                      || state == St.Triggered)
                ? "expected " + expLvl.ToString("N2")
                  + "   stop " + stopLvl.ToString("N2")
                  + (risk > 0m
                     ? "   risk " + risk.ToString("N2") + " pts"
                       + "   " + TargetR.ToString("N1") + "R target "
                       + target.ToString("N2")
                     : "   risk/target on entry")
                : why;

            var l5 = "window " + SessionHour.ToString("00") + ":"
                   + SessionMinute.ToString("00") + "–"
                   + ((OpenMins + IbMinutes) / 60).ToString("00") + ":"
                   + ((OpenMins + IbMinutes) % 60).ToString("00")
                   + " platform   flat " + FlatHour.ToString("00") + ":"
                   + FlatMinute.ToString("00")
                   + "   first IB candle "
                   + (ibBars > 0 ? firstT.ToString("HH:mm") : "--:--")
                   + "   chart " + (cm > 0 ? cm + "m" : "?");

            var l6 = "DISPLAY ONLY — no orders. Failed the concentration audit "
                   + "(top decile carries 164% of R). Small size, data only.";

            var warn = "";
            if (cm > 0 && cm != 1)
                warn = "CHART IS " + cm + "-MINUTE. The rule was frozen on "
                     + "1-MINUTE bars — which extreme formed first is a "
                     + "property of the bar grid. This is a different rule.";
            else if (ibBars > 0 && firstT.Minute != SessionMinute)
                warn = "First IB candle is " + firstT.ToString("HH:mm")
                     + " but the window starts " + SessionHour.ToString("00")
                     + ":" + SessionMinute.ToString("00")
                     + " — check the platform clock and US daylight saving.";
            else if (_entryBarWouldHaveStopped)
                warn = "The stop was touched on the ENTRY BAR. The backtest "
                     + "excludes that bar; live you may have been stopped. "
                     + "Log what happened, not what this says.";
            else if (_ambiguousBar)
                warn = "Ambiguous bar: stop and target both touched in one "
                     + "candle. Record it in the log.";

            var lines = new[] { l1, l2, l3, l4, l5, l6 };
            var wide = context.MeasureString(head, _fBig).Width;
            foreach (var s in lines)
                wide = Math.Max(wide, context.MeasureString(s, _fMid).Width);
            if (warn != "")
                wide = Math.Max(wide, context.MeasureString(warn, _fTiny).Width);

            var h2 = 34 + lines.Length * 20 + (warn != "" ? 22 : 0) + 14;
            var box = new Rectangle(10, 10, (int)wide + 28, h2);
            context.FillRectangle(PanelFill, box);
            context.DrawRectangle(new RenderPen(PanelEdge, 1), box);

            context.DrawString(head, _fBig, StateInk(), 24, 18);
            var y0 = 46;
            for (int i = 0; i < lines.Length; i++)
            {
                var ink = i == 5 ? WarnInk : PanelInk;
                if (i == 2 && ibDone && !sameBar)
                    ink = ez < EzBand ? (dir > 0 ? LongInk : ShortInk) : FlatInk;
                context.DrawString(lines[i], i >= 4 ? _fTiny : _fMid, ink,
                                   24, y0 + i * 20);
            }
            if (warn != "")
                context.DrawString(warn, _fTiny, BadInk, 24, y0 + lines.Length * 20);
        }
    }
}
