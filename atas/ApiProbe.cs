// API PROBE — writes a complete inventory of what this ATAS build offers.
//
// WHY THIS EXISTS
//
// The question "what does ATAS give us that we are not recording" cannot be
// answered away from the machine ATAS is installed on. The assemblies are not
// in this repository; the project file resolves them from the ATAS install
// directory at build time. Answering it from memory or from documentation
// would produce a plausible list that might not match this build, and a
// plausible list is worse than none -- it would be trusted.
//
// So this asks the assemblies directly, on the machine that has them, and
// writes the answer to a file.
//
// WHAT IT WRITES
//
//   _api_inventory.txt   in the same folder the recorder uses
//
//     1  every assembly loaded, with version          (provenance)
//     2  every overridable method on the Indicator chain, full signatures --
//        this is the complete set of callbacks available to us, not the
//        trade-and-depth subset the recorder already prints
//     3  every public property and field of every type those signatures
//        mention, with types
//     4  every market-data type in the ATAS and OFT assemblies, matched by
//        name, with members; enums expanded to their values
//     5  the live InstrumentInfo, every property, with current values --
//        which is where the price step will be visible as a number
//
// It draws nothing, records nothing, and writes once.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;

using ATAS.Indicators;

namespace Claude1.Recorders
{
    [DisplayName("API Probe (writes _api_inventory.txt)")]
    public class ApiProbe : Indicator
    {
        private const string BuildTag = "2026-09-16.probe.a";

        private bool _done;

        [DisplayName("Output folder (blank = Desktop\\ATAS_Export)")]
        public string OutputFolder { get; set; } = "";

        /// <summary>Type names containing any of these are treated as market
        /// data types worth expanding. Broad on purpose: the point is to find
        /// what we did not know to look for.</summary>
        private static readonly string[] Keywords =
        {
            "Trade", "Depth", "Book", "Quote", "Tick", "Market", "Instrument",
            "Level", "Cumulative", "Candle", "Order", "Security", "Session",
        };

        public ApiProbe()
        {
            try { DataSeries[0].IsHidden = true; } catch { }
        }

        private static bool Interesting(string name)
        {
            foreach (var k in Keywords)
                if (name.IndexOf(k, StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
            return false;
        }

        private static string Pretty(Type t)
        {
            if (t == null)
                return "?";
            if (!t.IsGenericType)
                return t.Name;
            var args = string.Join(", ", t.GetGenericArguments().Select(Pretty));
            var n = t.Name;
            var tick = n.IndexOf('`');
            if (tick > 0)
                n = n.Substring(0, tick);
            return n + "<" + args + ">";
        }

        private static void DumpMembers(StringBuilder sb, Type t, HashSet<string> seen)
        {
            if (t == null || !seen.Add(t.FullName ?? t.Name))
                return;

            sb.AppendLine();
            sb.AppendLine("  " + (t.IsEnum ? "enum " : "type ") + t.FullName);

            if (t.IsEnum)
            {
                foreach (var v in Enum.GetValues(t))
                    sb.AppendLine("      " + v + " = " +
                        Convert.ToInt64(v).ToString(CultureInfo.InvariantCulture));
                return;
            }

            foreach (var p in t.GetProperties(BindingFlags.Instance |
                                              BindingFlags.Public))
                sb.AppendLine("      prop  " + Pretty(p.PropertyType) + " " +
                              p.Name + (p.CanWrite ? "  { get; set; }" : "  { get; }"));

            foreach (var f in t.GetFields(BindingFlags.Instance |
                                          BindingFlags.Public))
                sb.AppendLine("      field " + Pretty(f.FieldType) + " " + f.Name);

            foreach (var m in t.GetMethods(BindingFlags.Instance |
                                           BindingFlags.Public |
                                           BindingFlags.DeclaredOnly))
            {
                if (m.IsSpecialName)
                    continue;
                var ps = string.Join(", ", m.GetParameters()
                    .Select(x => Pretty(x.ParameterType) + " " + x.Name));
                sb.AppendLine("      method " + Pretty(m.ReturnType) + " " +
                              m.Name + "(" + ps + ")");
            }
        }

        private string Folder()
        {
            try
            {
                var dir = string.IsNullOrWhiteSpace(OutputFolder)
                    ? Path.Combine(Environment.GetFolderPath(
                          Environment.SpecialFolder.DesktopDirectory), "ATAS_Export")
                    : OutputFolder;
                Directory.CreateDirectory(dir);
                return dir;
            }
            catch { return null; }
        }

        private string LiveInstrument()
        {
            var sb = new StringBuilder();
            try
            {
                var info = (object)InstrumentInfo;
                if (info == null)
                    return "  InstrumentInfo is null right now\n";
                var t = info.GetType();
                sb.AppendLine("  runtime type: " + t.FullName);
                foreach (var p in t.GetProperties(BindingFlags.Instance |
                                                  BindingFlags.Public))
                {
                    object v;
                    try { v = p.GetValue(info); }
                    catch (Exception e) { v = "<" + e.GetType().Name + ">"; }
                    sb.AppendLine("      " + p.Name + " = " +
                        Convert.ToString(v, CultureInfo.InvariantCulture));
                }
            }
            catch (Exception e)
            {
                sb.AppendLine("  could not read InstrumentInfo: " + e.Message);
            }
            return sb.ToString();
        }

        protected override void OnCalculate(int bar, decimal value)
        {
            if (_done)
                return;
            _done = true;

            try
            {
                var dir = Folder();
                if (dir == null)
                    return;

                var sb = new StringBuilder();
                sb.AppendLine("ATAS API INVENTORY");
                sb.AppendLine("==================");
                sb.AppendLine("probe version: " + BuildTag);
                sb.AppendLine("written:       " + DateTime.Now.ToString(
                    "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture));
                sb.AppendLine();

                // ---- 1. provenance -----------------------------------------
                sb.AppendLine("---- 1. ASSEMBLIES LOADED ----");
                foreach (var a in AppDomain.CurrentDomain.GetAssemblies()
                             .OrderBy(x => x.GetName().Name))
                {
                    var n = a.GetName();
                    if (n.Name == null)
                        continue;
                    if (!n.Name.StartsWith("ATAS", StringComparison.OrdinalIgnoreCase) &&
                        !n.Name.StartsWith("OFT", StringComparison.OrdinalIgnoreCase) &&
                        !n.Name.StartsWith("Utils", StringComparison.OrdinalIgnoreCase))
                        continue;
                    sb.AppendLine("  " + n.Name + "  " + n.Version);
                }

                // ---- 2. every overridable callback -------------------------
                sb.AppendLine();
                sb.AppendLine("---- 2. EVERY OVERRIDABLE METHOD ON THE INDICATOR CHAIN ----");
                sb.AppendLine("(the complete callback surface, not a filtered subset)");
                var payload = new List<Type>();
                var t0 = typeof(ApiProbe).BaseType;
                while (t0 != null)
                {
                    var printed = false;
                    foreach (var m in t0.GetMethods(BindingFlags.Instance |
                                                    BindingFlags.Public |
                                                    BindingFlags.NonPublic |
                                                    BindingFlags.DeclaredOnly)
                                 .OrderBy(x => x.Name))
                    {
                        if (!m.IsVirtual || m.IsFinal || m.IsSpecialName)
                            continue;
                        if (!printed)
                        {
                            sb.AppendLine();
                            sb.AppendLine("  from " + t0.FullName + ":");
                            printed = true;
                        }
                        var ps = m.GetParameters();
                        foreach (var p in ps)
                            payload.Add(p.ParameterType);
                        sb.AppendLine("      " + Pretty(m.ReturnType) + " " + m.Name +
                            "(" + string.Join(", ", ps.Select(
                                x => Pretty(x.ParameterType) + " " + x.Name)) + ")");
                    }
                    t0 = t0.BaseType;
                }

                // ---- 3. the types those callbacks hand us ------------------
                sb.AppendLine();
                sb.AppendLine("---- 3. TYPES APPEARING IN THOSE SIGNATURES ----");
                var seen = new HashSet<string>();
                foreach (var t in payload.Distinct())
                {
                    var u = t.IsByRef ? t.GetElementType() : t;
                    if (u == null || u.IsPrimitive || u == typeof(string))
                        continue;
                    DumpMembers(sb, u, seen);
                }

                // ---- 4. every market-data type in the assemblies -----------
                sb.AppendLine();
                sb.AppendLine("---- 4. MARKET DATA TYPES IN THE ATAS/OFT ASSEMBLIES ----");
                foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    var n = a.GetName().Name;
                    if (n == null)
                        continue;
                    if (!n.StartsWith("ATAS", StringComparison.OrdinalIgnoreCase) &&
                        !n.StartsWith("OFT", StringComparison.OrdinalIgnoreCase))
                        continue;
                    Type[] types;
                    try { types = a.GetTypes(); }
                    catch (ReflectionTypeLoadException e)
                    { types = e.Types.Where(x => x != null).ToArray(); }
                    catch { continue; }

                    foreach (var t in types.OrderBy(x => x.FullName))
                    {
                        if (!t.IsPublic || t.Name == null || !Interesting(t.Name))
                            continue;
                        DumpMembers(sb, t, seen);
                    }
                }

                // ---- 5. the live instrument, with values -------------------
                sb.AppendLine();
                sb.AppendLine("---- 5. LIVE INSTRUMENT ----");
                sb.AppendLine("(the price step is a NUMBER here; 0.25 is the true NQ tick)");
                sb.Append(LiveInstrument());

                File.WriteAllText(Path.Combine(dir, "_api_inventory.txt"),
                                  sb.ToString(), Encoding.UTF8);
            }
            catch
            {
                // A probe that throws on the chart is worse than one that is
                // silent; the absence of the file is the error report.
            }
        }
    }
}
