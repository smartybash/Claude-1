// Level Plan — computes the weight rule's levels live, and writes the plan.
//
// The execution study settled what this needs to do. Median hold is 2.6 minutes
// and the first quartile is 48 seconds, so reacting to a chart is hopeless, but
// the levels come from the PREVIOUS session and are known before the open. The
// trade is therefore a resting limit with a bracket, placed in advance, and the
// useful output is a list of prices to place them at -- not a drawing.
//
// So this writes three files and draws nothing:
//
//   PROFILE_{sym}_{date}.csv   volume at every price in the cash session, which
//                              is the raw material for tomorrow's levels and
//                              survives a restart
//   PLAN_{sym}_{date}.txt      the levels to trade, each marked LIGHT (place an
//                              order) or HEAVY (do not), with the side
//   SIGNALS_{sym}_{date}.csv   a row each time price touches a light level, so
//                              live behaviour can be checked against the study
//
// Everything here uses only API that the recorder has already compiled against:
// OnNewTrade, InstrumentInfo, and file I/O. Nothing is drawn on the chart and
// no rendering API is touched, because a wrong guess there costs a build and
// the plan file is what the trade actually needs.
//
// The rule, frozen, from reports/findings_summary.md:
//
//   levels      previous cash session high, low, close, VAH, POC, VAL
//   merge       levels within 5 points become one, at their mean
//   weight      volume traded within +/- 2 points of the level, previous session
//   LIGHT       under 10,000 contracts  -> fade it
//   HEAVY       10,000 or more          -> leave it alone
//   side        approached from above -> buy limit; from below -> sell limit
//   stop/target 30 points each
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;

using ATAS.Indicators;

namespace Claude1.Recorders
{
    [DisplayName("Level Plan (weight rule)")]
    public partial class LevelPlanner : Indicator
    {
        private const string BuildTag = "2026-09-14.plan.f";

        private readonly object _sync = new object();

        // Volume at each price for the session in progress. The key is the price
        // in ticks so that decimal equality is exact.
        private readonly Dictionary<long, long> _vol = new Dictionary<long, long>();
        private decimal _hi, _lo, _close;
        private bool _any;
        private string _sessionDate = "";

        private readonly List<Level> _levels = new List<Level>();
        private readonly Dictionary<string, bool> _armed =
            new Dictionary<string, bool>();
        private readonly Dictionary<string, bool> _above =
            new Dictionary<string, bool>();

        // Session cumulative delta, and a five-minute rolling window of it.
        // These are the only two of ATAS's reads that separated anything when
        // tested on the light-level trades: a day running hard against the fade
        // is the losing case, and aggression INTO the level is the winning one.
        private long _cvd;
        private readonly List<KeyValuePair<DateTime, long>> _recent =
            new List<KeyValuePair<DateTime, long>>();
        private long _delta5;

        internal long SessionCvd { get { return _cvd; } }
        internal long Delta5Min { get { return _delta5; } }

        private StreamWriter _signals;
        private string _lastError = "(none)";
        private long _trades, _touches;
        private DateTime _lastStatus = DateTime.MinValue;

        internal sealed class Level
        {
            public string Name;
            public decimal Price;
            public long Weight;
            public bool Light;
            public bool Buy;          // approached from above -> fade with a buy
            public decimal Stop;
            public decimal Target;
        }

        /// <summary>Levels for the render half. Empty until a plan exists.</summary>
        internal List<Level> PlanLevels { get { return _levels; } }

        internal decimal LastPrice { get { return _close; } }

        /// <summary>The light level price is nearest to, and how far away.</summary>
        internal Level Nearest;
        internal decimal NearestDist = 9999m;
        internal Level Touching;
        internal DateTime TouchedAt = DateTime.MinValue;

        /// <summary>Set true by the optional render half if it is compiled in.</summary>
#pragma warning disable 0649   // assigned only in LevelPlanner.Render.cs
        internal static bool RenderAvailable;
#pragma warning restore 0649

        // ---- settings -------------------------------------------------------
        [DisplayName("Output folder")]
        public string OutputFolder { get; set; } =
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                "ATAS_Export");

        [DisplayName("Price step")]
        public decimal PriceStep { get; set; } = 0.25m;

        [DisplayName("RTH start hour (platform clock)")]
        public int RthStartHour { get; set; } = 13;

        [DisplayName("RTH start minute")]
        public int RthStartMinute { get; set; } = 30;

        [DisplayName("RTH end hour (platform clock)")]
        public int RthEndHour { get; set; } = 20;

        [DisplayName("RTH end minute")]
        public int RthEndMinute { get; set; } = 0;

        [DisplayName("Value area fraction")]
        public double ValueArea { get; set; } = 0.70;

        [DisplayName("Merge levels within (points)")]
        public decimal MergePts { get; set; } = 5.0m;

        [DisplayName("Weight band (points either side)")]
        public decimal BandPts { get; set; } = 2.0m;

        [DisplayName("Heavy threshold (contracts)")]
        public long HeavyThreshold { get; set; } = 10000;

        [DisplayName("Touch tolerance (points)")]
        public decimal TouchTol { get; set; } = 0.25m;

        [DisplayName("Re-arm distance (points)")]
        public decimal RearmPts { get; set; } = 8.0m;

        [DisplayName("Stop and target (points)")]
        public decimal StopPts { get; set; } = 30.0m;

        [DisplayName("Watch when within (points)")]
        public decimal WatchPts { get; set; } = 50.0m;

        [DisplayName("Keep touch prompt up for (seconds)")]
        public int PromptSeconds { get; set; } = 120;

        [DisplayName("No-trade band height (points)")]
        public decimal NoTradeBandPts { get; set; } = 6.0m;

        /// <summary>
        /// Implemented in the optional LevelPlanner.Render.cs. When that file is
        /// compiled out the compiler erases both this declaration and the call
        /// below, so the indicator builds and runs with no drawing and no
        /// reference to any rendering type.
        /// </summary>
        partial void ConfigureRendering();

        public LevelPlanner()
        {
            try { DataSeries[0].IsHidden = true; } catch { }
            ConfigureRendering();
            WriteStatus(true);
        }

        // ---- helpers --------------------------------------------------------
        private long Ticks(decimal price)
        {
            return (long)Math.Round(price / PriceStep, MidpointRounding.AwayFromZero);
        }

        private decimal Price(long ticks)
        {
            return ticks * PriceStep;
        }

        private bool InSession(DateTime t)
        {
            var m = t.Hour * 60 + t.Minute;
            var a = RthStartHour * 60 + RthStartMinute;
            var b = RthEndHour * 60 + RthEndMinute;
            return a <= b ? (m >= a && m < b) : (m >= a || m < b);
        }

        private string Folder()
        {
            Directory.CreateDirectory(OutputFolder);
            return OutputFolder;
        }

        private string Sym()
        {
            try
            {
                var i = InstrumentInfo;
                if (i != null && !string.IsNullOrEmpty(i.Instrument))
                {
                    var s = i.Instrument;
                    foreach (var c in Path.GetInvalidFileNameChars())
                        s = s.Replace(c, '_');
                    return s;
                }
            }
            catch { }
            return "UNKNOWN";
        }

        // ---- the profile ----------------------------------------------------
        /// <summary>
        /// POC and value area from volume at price, grown outward from the POC
        /// taking the heavier neighbour each step. This is deliberately the same
        /// algorithm as volume_profile() in scripts/orderflow/tape.py; if the
        /// two disagree the backtest and the live levels are different rules.
        /// </summary>
        private bool Profile(Dictionary<long, long> vol,
                             out decimal poc, out decimal vah, out decimal val)
        {
            poc = vah = val = 0m;
            if (vol.Count == 0)
                return false;

            var keys = new List<long>(vol.Keys);
            keys.Sort();

            var n = keys.Count;
            var pocI = 0;
            long best = -1;
            long total = 0;
            for (var i = 0; i < n; i++)
            {
                var v = vol[keys[i]];
                total += v;
                if (v > best) { best = v; pocI = i; }
            }

            var target = ValueArea * total;
            int lo = pocI, hi = pocI;
            double got = vol[keys[pocI]];
            while (got < target && (lo > 0 || hi < n - 1))
            {
                long below = lo > 0 ? vol[keys[lo - 1]] : -1;
                long above = hi < n - 1 ? vol[keys[hi + 1]] : -1;
                if (above >= below) { hi++; got += vol[keys[hi]]; }
                else { lo--; got += vol[keys[lo]]; }
            }

            poc = Price(keys[pocI]);
            val = Price(keys[lo]);
            vah = Price(keys[hi]);
            return true;
        }

        private long WeightAt(Dictionary<long, long> vol, decimal level)
        {
            var band = (long)Math.Round(BandPts / PriceStep);
            var c = Ticks(level);
            long sum = 0;
            for (var t = c - band; t <= c + band; t++)
            {
                long v;
                if (vol.TryGetValue(t, out v))
                    sum += v;
            }
            return sum;
        }

        // ---- persistence ----------------------------------------------------
        private void SaveProfile(string date)
        {
            var path = Path.Combine(Folder(), "PROFILE_" + Sym() + "_" + date + ".csv");
            var sb = new StringBuilder();
            sb.AppendLine("price,volume");
            var keys = new List<long>(_vol.Keys);
            keys.Sort();
            foreach (var k in keys)
                sb.AppendLine(Price(k).ToString(CultureInfo.InvariantCulture) + "," +
                              _vol[k].ToString(CultureInfo.InvariantCulture));
            sb.AppendLine("# high," + _hi.ToString(CultureInfo.InvariantCulture));
            sb.AppendLine("# low," + _lo.ToString(CultureInfo.InvariantCulture));
            sb.AppendLine("# close," + _close.ToString(CultureInfo.InvariantCulture));
            File.WriteAllText(path, sb.ToString(), Encoding.UTF8);
        }

        private bool LoadLatestProfile(string beforeDate,
                                       out Dictionary<long, long> vol,
                                       out decimal hi, out decimal lo,
                                       out decimal close, out string usedDate)
        {
            vol = new Dictionary<long, long>();
            hi = lo = close = 0m;
            usedDate = "";

            var dir = Folder();
            var prefix = "PROFILE_" + Sym() + "_";
            var files = Directory.GetFiles(dir, prefix + "*.csv");
            Array.Sort(files);
            string pick = null;
            foreach (var f in files)
            {
                var name = Path.GetFileNameWithoutExtension(f);
                var d = name.Substring(prefix.Length);
                if (string.CompareOrdinal(d, beforeDate) < 0)
                {
                    pick = f;
                    usedDate = d;
                }
            }
            if (pick == null)
                return false;

            foreach (var line in File.ReadAllLines(pick))
            {
                if (line.Length == 0)
                    continue;
                var parts = line.Split(',');
                if (line[0] == '#')
                {
                    if (parts.Length < 2)
                        continue;
                    var v = decimal.Parse(parts[1], CultureInfo.InvariantCulture);
                    if (line.IndexOf("high", StringComparison.Ordinal) >= 0) hi = v;
                    else if (line.IndexOf("low", StringComparison.Ordinal) >= 0) lo = v;
                    else if (line.IndexOf("close", StringComparison.Ordinal) >= 0) close = v;
                    continue;
                }
                if (parts.Length < 2 || parts[0] == "price")
                    continue;
                decimal p;
                long q;
                if (decimal.TryParse(parts[0], NumberStyles.Any,
                                     CultureInfo.InvariantCulture, out p) &&
                    long.TryParse(parts[1], out q))
                    vol[Ticks(p)] = q;
            }
            return vol.Count > 0;
        }

        // ---- the plan -------------------------------------------------------
        private void BuildPlan(string today)
        {
            _levels.Clear();
            _armed.Clear();
            _above.Clear();

            Dictionary<long, long> pv;
            decimal hi, lo, close, poc, vah, val;
            string from;
            if (!LoadLatestProfile(today, out pv, out hi, out lo, out close, out from))
            {
                _lastError = "no previous session profile yet; one will be " +
                             "written at the end of today";
                return;
            }
            if (!Profile(pv, out poc, out vah, out val))
            {
                _lastError = "previous profile had no volume";
                return;
            }

            var raw = new List<KeyValuePair<string, decimal>>
            {
                new KeyValuePair<string, decimal>("pdHIGH", hi),
                new KeyValuePair<string, decimal>("pdLOW", lo),
                new KeyValuePair<string, decimal>("pdCLOSE", close),
                new KeyValuePair<string, decimal>("pdVAH", vah),
                new KeyValuePair<string, decimal>("pdPOC", poc),
                new KeyValuePair<string, decimal>("pdVAL", val),
            };
            raw.Sort((a, b) => a.Value.CompareTo(b.Value));

            // Merge anything within MergePts, exactly as the study did: two
            // levels half a point apart are one level, and counting them
            // separately was what inflated the first result.
            var names = new List<string>();
            var sum = 0m;
            var count = 0;
            Action flush = delegate
            {
                if (count == 0)
                    return;
                var price = sum / count;
                var w = WeightAt(pv, price);
                _levels.Add(new Level
                {
                    Name = string.Join("+", names.ToArray()),
                    Price = price,
                    Weight = w,
                    Light = w < HeavyThreshold,
                });
                names.Clear();
                sum = 0m;
                count = 0;
            };

            decimal lastPrice = 0m;
            foreach (var kv in raw)
            {
                if (count > 0 && kv.Value - lastPrice > MergePts)
                    flush();
                names.Add(kv.Key);
                sum += kv.Value;
                count++;
                lastPrice = kv.Value;
            }
            flush();

            foreach (var l in _levels)
            {
                _armed[l.Name] = true;
                _above[l.Name] = close > l.Price;
                SetSide(l, close > l.Price);
            }

            WritePlan(today, from);
        }

        private void WritePlan(string today, string from)
        {
            var sb = new StringBuilder();
            sb.AppendLine("LEVEL PLAN  " + Sym() + "  " + today);
            sb.AppendLine("levels computed from the cash session of " + from);
            sb.AppendLine("recorder " + BuildTag);
            sb.AppendLine();
            sb.AppendLine("Place a bracketed limit at each LIGHT level. Buy limits");
            sb.AppendLine("below price, sell limits above. Stop and target " +
                          StopPts.ToString(CultureInfo.InvariantCulture) +
                          " points.");
            sb.AppendLine("Leave HEAVY levels alone: fading those lost 12 points a");
            sb.AppendLine("trade at 33% in the study.");
            sb.AppendLine();
            sb.AppendLine("   price        weight   verdict   level");
            sb.AppendLine("   ----------   -------  --------  -----------------");
            _levels.Sort((a, b) => b.Price.CompareTo(a.Price));
            foreach (var l in _levels)
                sb.AppendLine("   " +
                    l.Price.ToString("N2", CultureInfo.InvariantCulture).PadLeft(10) +
                    "   " + l.Weight.ToString("N0", CultureInfo.InvariantCulture).PadLeft(7) +
                    "  " + (l.Light ? "LIGHT   " : "heavy   ") +
                    "  " + l.Name);
            sb.AppendLine();
            sb.AppendLine("LIGHT levels are the tradeable ones. Heavy threshold is " +
                          HeavyThreshold.ToString("N0", CultureInfo.InvariantCulture) +
                          " contracts");
            sb.AppendLine("within " + BandPts.ToString(CultureInfo.InvariantCulture) +
                          " points of the level during the previous cash session.");

            File.WriteAllText(Path.Combine(Folder(),
                "PLAN_" + Sym() + "_" + today + ".txt"), sb.ToString(),
                Encoding.UTF8);
        }

        // ---- live -----------------------------------------------------------
        private void CheckTouch(decimal price, DateTime when)
        {
            foreach (var l in _levels)
            {
                var d = price - l.Price;
                var ad = d < 0 ? -d : d;
                bool armed;
                if (!_armed.TryGetValue(l.Name, out armed))
                    continue;

                if (armed && ad <= TouchTol)
                {
                    _armed[l.Name] = false;
                    _touches++;
                    var fromAbove = _above[l.Name];
                    if (l.Light)
                    {
                        Touching = l;
                        TouchedAt = when;
                    }
                    LogSignal(when, l, fromAbove, price);
                }
                else if (!armed && ad >= RearmPts)
                {
                    _armed[l.Name] = true;
                    _above[l.Name] = d > 0;
                }
            }
        }

        /// <summary>
        /// Nearest light level, and whether a touch prompt is still current.
        /// Heavy levels are deliberately ignored here: they are not trades, so
        /// counting down to one would invite exactly the thing the rule forbids.
        /// </summary>
        /// <summary>
        /// Price is above the level, so it will be approached from above and
        /// faded with a buy. Brackets follow the side.
        /// </summary>
        private void SetSide(Level l, bool priceAbove)
        {
            l.Buy = priceAbove;
            l.Stop = l.Buy ? l.Price - StopPts : l.Price + StopPts;
            l.Target = l.Buy ? l.Price + StopPts : l.Price - StopPts;
        }

        /// <summary>
        /// Drop anything older than five minutes and recompute the window sum.
        /// The list is walked from the front rather than rebuilt, because this
        /// runs on every trade and the session carries a third of a million.
        /// </summary>
        private void TrimRecent(DateTime now)
        {
            var cut = now.AddMinutes(-5);
            var drop = 0;
            while (drop < _recent.Count && _recent[drop].Key < cut)
                drop++;
            if (drop > 0)
                _recent.RemoveRange(0, drop);

            long sum = 0;
            for (var i = 0; i < _recent.Count; i++)
                sum += _recent[i].Value;
            _delta5 = sum;
        }

        private void UpdateWatch(decimal price, DateTime when)
        {
            Level best = null;
            var bestD = 9999m;
            foreach (var l in _levels)
            {
                // A level price is sitting below is approached from below and
                // sold; one above it is bought. Refreshed here so a level that
                // price has crossed during the session shows the right side.
                if (Touching != l)
                    SetSide(l, price > l.Price);

                if (!l.Light)
                    continue;
                var d = price - l.Price;
                if (d < 0) d = -d;
                if (d < bestD) { bestD = d; best = l; }
            }
            Nearest = best;
            NearestDist = bestD;

            if (Touching != null &&
                (when - TouchedAt).TotalSeconds > PromptSeconds)
                Touching = null;
        }

        private void LogSignal(DateTime when, Level l, bool fromAbove, decimal price)
        {
            try
            {
                if (_signals == null)
                {
                    var path = Path.Combine(Folder(),
                        "SIGNALS_" + Sym() + "_" + _sessionDate + ".csv");
                    var isNew = !File.Exists(path);
                    _signals = new StreamWriter(
                        new FileStream(path, FileMode.Append, FileAccess.Write,
                                       FileShare.ReadWrite | FileShare.Delete),
                        Encoding.UTF8);
                    _signals.AutoFlush = true;
                    if (isNew)
                        _signals.WriteLine(
                            "time,level,level_price,weight,verdict,side,touch_price,"
                            + "stop,target,session_cvd,delta_5min");
                }
                var side = fromAbove ? "BUY" : "SELL";
                var stop = fromAbove ? l.Price - StopPts : l.Price + StopPts;
                var tgt = fromAbove ? l.Price + StopPts : l.Price - StopPts;
                _signals.WriteLine(
                    when.ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture) +
                    "," + l.Name +
                    "," + l.Price.ToString(CultureInfo.InvariantCulture) +
                    "," + l.Weight +
                    "," + (l.Light ? "LIGHT" : "heavy") +
                    "," + side +
                    "," + price.ToString(CultureInfo.InvariantCulture) +
                    "," + stop.ToString(CultureInfo.InvariantCulture) +
                    "," + tgt.ToString(CultureInfo.InvariantCulture) +
                    "," + _cvd.ToString(CultureInfo.InvariantCulture) +
                    "," + _delta5.ToString(CultureInfo.InvariantCulture));
            }
            catch (Exception ex)
            {
                _lastError = "signal: " + ex.Message;
            }
        }

        /// <summary>
        /// Report the real drawing API rather than guessing it a third time.
        ///
        /// Two builds have already been lost to assumed names in the cumulative
        /// trade API. The rendering surface is larger and the documentation is
        /// unreachable from here, so the installed assembly is asked directly:
        /// the signature of OnRender, every drawing method on whatever type it
        /// takes, and the price-to-pixel helpers on ChartInfo. Reflection
        /// compiles against whatever the API turns out to be, so this cannot
        /// itself break the build, and one run answers what a guess cannot.
        /// </summary>
        private string DescribeRenderApi()
        {
            try
            {
                var sb = new StringBuilder();
                Type ctxType = null;

                var t = typeof(LevelPlanner).BaseType;
                while (t != null && ctxType == null)
                {
                    foreach (var m in t.GetMethods(BindingFlags.Instance |
                                                   BindingFlags.Public |
                                                   BindingFlags.NonPublic |
                                                   BindingFlags.DeclaredOnly))
                    {
                        if (m.Name != "OnRender")
                            continue;
                        var ps = m.GetParameters();
                        sb.Append("OnRender(");
                        for (var i = 0; i < ps.Length; i++)
                        {
                            if (i > 0) sb.Append(", ");
                            sb.Append(ps[i].ParameterType.Name).Append(" ")
                              .Append(ps[i].Name);
                            if (ctxType == null && ps[i].ParameterType.Name
                                    .IndexOf("Context", StringComparison.Ordinal) >= 0)
                                ctxType = ps[i].ParameterType;
                        }
                        sb.AppendLine(")");
                        break;
                    }
                    t = t.BaseType;
                }

                if (ctxType != null)
                {
                    sb.AppendLine();
                    sb.AppendLine(ctxType.Name + " drawing methods:");
                    foreach (var m in ctxType.GetMethods(BindingFlags.Instance |
                                                         BindingFlags.Public))
                    {
                        var n = m.Name;
                        if (n.IndexOf("Draw", StringComparison.Ordinal) < 0 &&
                            n.IndexOf("Fill", StringComparison.Ordinal) < 0 &&
                            n.IndexOf("Measure", StringComparison.Ordinal) < 0)
                            continue;
                        var ps = m.GetParameters();
                        sb.Append("  ").Append(n).Append("(");
                        for (var i = 0; i < ps.Length; i++)
                        {
                            if (i > 0) sb.Append(", ");
                            sb.Append(ps[i].ParameterType.Name);
                        }
                        sb.AppendLine(")");
                    }
                }

                try
                {
                    var ci = ChartInfo;
                    if (ci != null)
                    {
                        sb.AppendLine();
                        sb.AppendLine(ci.GetType().Name + " members:");
                        foreach (var m in ci.GetType().GetMethods(
                                     BindingFlags.Instance | BindingFlags.Public))
                        {
                            var n = m.Name;
                            if (n.IndexOf("Price", StringComparison.Ordinal) < 0 &&
                                n.IndexOf("Y", StringComparison.Ordinal) != 0 &&
                                n.IndexOf("GetX", StringComparison.Ordinal) < 0)
                                continue;
                            var ps = m.GetParameters();
                            sb.Append("  ").Append(n).Append("(");
                            for (var i = 0; i < ps.Length; i++)
                            {
                                if (i > 0) sb.Append(", ");
                                sb.Append(ps[i].ParameterType.Name);
                            }
                            sb.AppendLine(")");
                        }
                        foreach (var pr in ci.GetType().GetProperties(
                                     BindingFlags.Instance | BindingFlags.Public))
                            sb.AppendLine("  ." + pr.Name + " : " +
                                          pr.PropertyType.Name);
                    }
                }
                catch { }

                return sb.ToString();
            }
            catch (Exception ex)
            {
                return "render api reflection failed: " + ex.Message;
            }
        }

        // ---- status ---------------------------------------------------------
        private void WriteStatus(bool force)
        {
            var now = DateTime.Now;
            if (!force && (now - _lastStatus).TotalSeconds < 2)
                return;
            _lastStatus = now;
            try
            {
                var sb = new StringBuilder();
                sb.AppendLine("Level Plan status");
                sb.AppendLine("=================");
                sb.AppendLine("version:          " + BuildTag);
                sb.AppendLine("updated:          " +
                    now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture));
                sb.AppendLine("instrument:       " + Sym());
                sb.AppendLine("session date:     " + _sessionDate);
                sb.AppendLine("trades seen:      " + _trades);
                sb.AppendLine("prices in profile:" + _vol.Count);
                sb.AppendLine("levels planned:   " + _levels.Count);
                sb.AppendLine("touches today:    " + _touches);
                sb.AppendLine("session CVD:      " + _cvd.ToString("N0", CultureInfo.InvariantCulture));
                sb.AppendLine("delta, last 5min: " + _delta5.ToString("N0", CultureInfo.InvariantCulture));
                sb.AppendLine("last error:       " + _lastError);
                sb.AppendLine("drawing:          " + (RenderAvailable
                    ? "on" : "OFF (built without the render half)"));
                sb.AppendLine();
                sb.AppendLine("---- drawing API, for Claude ----");
                sb.Append(DescribeRenderApi());
                sb.AppendLine("--------------------------------");
                sb.AppendLine();
                foreach (var l in _levels)
                    sb.AppendLine("   " +
                        l.Price.ToString("N2", CultureInfo.InvariantCulture).PadLeft(10) +
                        "  " + (l.Light ? "LIGHT" : "heavy") +
                        "  weight " + l.Weight.ToString("N0", CultureInfo.InvariantCulture) +
                        "  " + l.Name);
                File.WriteAllText(Path.Combine(Folder(), "_plan_status.txt"),
                                  sb.ToString(), Encoding.UTF8);
            }
            catch { }
        }

        // ---- ATAS hooks -----------------------------------------------------
        protected override void OnCalculate(int bar, decimal value)
        {
            lock (_sync)
                WriteStatus(false);
        }

        protected override void OnNewTrade(MarketDataArg arg)
        {
            if (arg == null)
                return;
            _trades++;
            if (!InSession(arg.Time))
                return;

            lock (_sync)
            {
                try
                {
                    var date = arg.Time.ToString("yyyyMMdd",
                                                 CultureInfo.InvariantCulture);
                    if (date != _sessionDate)
                    {
                        // A new cash session. Persist what was accumulated, then
                        // build today's plan from the most recent earlier one.
                        if (_any && _sessionDate.Length > 0)
                            SaveProfile(_sessionDate);
                        if (_signals != null)
                        {
                            _signals.Dispose();
                            _signals = null;
                        }
                        _vol.Clear();
                        _recent.Clear();
                        _cvd = 0;
                        _delta5 = 0;
                        _any = false;
                        _sessionDate = date;
                        BuildPlan(date);
                    }

                    var signed = arg.Direction == TradeDirection.Buy
                        ? (long)arg.Volume
                        : arg.Direction == TradeDirection.Sell
                            ? -(long)arg.Volume
                            : 0L;
                    _cvd += signed;
                    _recent.Add(new KeyValuePair<DateTime, long>(arg.Time, signed));
                    TrimRecent(arg.Time);

                    var t = Ticks(arg.Price);
                    long cur;
                    _vol[t] = _vol.TryGetValue(t, out cur)
                        ? cur + (long)arg.Volume
                        : (long)arg.Volume;

                    if (!_any)
                    {
                        _hi = _lo = arg.Price;
                        _any = true;
                        foreach (var l in _levels)
                            _above[l.Name] = arg.Price > l.Price;
                    }
                    if (arg.Price > _hi) _hi = arg.Price;
                    if (arg.Price < _lo) _lo = arg.Price;
                    _close = arg.Price;

                    CheckTouch(arg.Price, arg.Time);
                    UpdateWatch(arg.Price, arg.Time);
                }
                catch (Exception ex)
                {
                    _lastError = "trade: " + ex.Message;
                }
            }
        }

        protected override void OnDispose()
        {
            lock (_sync)
            {
                try
                {
                    if (_any && _sessionDate.Length > 0)
                        SaveProfile(_sessionDate);
                }
                catch (Exception ex) { _lastError = "save: " + ex.Message; }
                try
                {
                    if (_signals != null)
                    {
                        _signals.Dispose();
                        _signals = null;
                    }
                }
                catch { }
                WriteStatus(true);
            }
            base.OnDispose();
        }
    }
}
