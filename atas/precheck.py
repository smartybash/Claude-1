#!/usr/bin/env python3
"""Catch the compile errors that are findable without a compiler.

There is no .NET SDK and no ATAS assembly here, so the C# cannot be built
before it is sent. But of the errors that have actually cost a rebuild in this
project, most needed no compiler to find:

    MSB4025   a double hyphen inside an XML comment in the csproj    (twice)
    CS0108    a property name colliding with a base member of Indicator
    CS0120    a static method reading an instance property
    CS0649    a field only ever assigned in an optional file

Each is a pattern in the text. This checks for all of them, plus the structural
invariants the optional-file scheme depends on. It is not a type checker and
will never catch a wrong method signature -- that is what the fallback build
passes are for -- but it stops the same self-inflicted errors recurring.

Usage: python3 atas/precheck.py
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Instance members of ATAS.Indicators.Indicator that a static method cannot use.
# Confirmed by the compiler: ChartInfo produced CS0120 exactly this way.
INSTANCE_MEMBERS = [
    "ChartInfo", "InstrumentInfo", "DataSeries", "ChartArea", "Container",
    "MouseLocationInfo", "MarketDepthInfo", "GetCandle", "CurrentBar",
    "EnableCustomDrawing", "SubscribeToDrawingEvents",
]

# Base members whose names must not be redeclared. TickSize cost a CS0108.
RESERVED_NAMES = [
    "TickSize", "Name", "Panel", "Digits", "Container", "ChartInfo",
    "DataSeries", "LineSeries", "Calculate", "Instrument",
]


def strip(src: str) -> str:
    """Remove comments and string literals so matches are real code."""
    s = re.sub(r"//[^\n]*", "", src)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r'@"(?:[^"]|"")*"', '""', s)
    s = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
    s = re.sub(r"'(?:\\.|[^'\\])*'", "''", s)
    return s


def body_of(code: str, start: int) -> str:
    """The braced block beginning at or after `start`."""
    i = code.find("{", start)
    if i < 0:
        return ""
    depth, j = 0, i
    while j < len(code):
        if code[j] == "{":
            depth += 1
        elif code[j] == "}":
            depth -= 1
            if depth == 0:
                return code[i:j + 1]
        j += 1
    return code[i:]


def check_cs(path: Path, problems: list):
    src = path.read_text(encoding="utf-8")
    code = strip(src)

    # --- braces and parens -------------------------------------------------
    if code.count("{") != code.count("}"):
        problems.append(f"{path.name}: unbalanced braces "
                        f"({code.count('{')} open, {code.count('}')} close)")
    if code.count("(") != code.count(")"):
        problems.append(f"{path.name}: unbalanced parentheses")

    # --- CS0120: static method using an instance member --------------------
    for m in re.finditer(r"\b(?:private|protected|public|internal)\s+static\s+"
                         r"[\w<>\[\],\s\.]+?\s+(\w+)\s*\(", code):
        name = m.group(1)
        body = body_of(code, m.end())
        for member in INSTANCE_MEMBERS:
            if re.search(r"\b" + member + r"\b", body):
                problems.append(
                    f"{path.name}: CS0120 — static method {name}() reads the "
                    f"instance member {member}")

    # --- CS0108: redeclaring a base member ---------------------------------
    for m in re.finditer(r"\bpublic\s+(?!partial|class|sealed)"
                         r"[\w<>\[\],\.]+\s+(\w+)\s*\{\s*get", code):
        if m.group(1) in RESERVED_NAMES:
            problems.append(
                f"{path.name}: CS0108 — property {m.group(1)} hides a member of "
                f"Indicator; rename it")

    # --- CS0649: a field only the optional half assigns ---------------------
    for m in re.finditer(r"internal\s+static\s+bool\s+(\w+)\s*;", code):
        field = m.group(1)
        if f"#pragma warning disable 0649" not in src:
            problems.append(
                f"{path.name}: CS0649 — {field} is assigned only in an optional "
                f"file; wrap it in #pragma warning disable 0649")

    # --- partial-method scheme ---------------------------------------------
    for m in re.finditer(r"partial\s+void\s+(\w+)\s*\(\s*\)\s*;", code):
        hook = m.group(1)
        impls = [p for p in HERE.glob("*.cs")
                 if re.search(r"partial\s+void\s+" + hook + r"\s*\(\s*\)\s*\{",
                              strip(p.read_text(encoding="utf-8")))]
        if not impls:
            problems.append(f"{path.name}: partial hook {hook}() is declared "
                            f"but never implemented anywhere")


def check_csproj(path: Path, problems: list):
    src = path.read_text(encoding="utf-8")
    try:
        ET.fromstring(src)
    except ET.ParseError as e:
        problems.append(f"{path.name}: not valid XML — {e}")
        return
    if "<!--" in src:
        problems.append(f"{path.name}: MSB4025 risk — contains a comment. "
                        f"A double hyphen inside one kills the whole build; "
                        f"this file is kept comment-free on purpose")
    for opt, prop in (("L2Recorder.Cumulative.cs", "NoCumulative"),
                      ("LevelPlanner.Render.cs", "NoRender")):
        if (HERE / opt).exists() and f'Remove="{opt}"' not in src:
            problems.append(f"{path.name}: {opt} exists but has no "
                            f"<Compile Remove> guarded by {prop}, so a failure "
                            f"in it cannot be built around")


def check_partials(sources):
    """Every partial implementation needs a declaration, with matching names.

    Two builds have now been lost to this. CS0759 fires when an implementing
    partial has no declaring half -- which happens the moment an edit to the
    main file removes a `partial void X();` line that an optional file still
    implements. CS8826 fires when the two halves spell a parameter
    differently, which compiles but warns and is pure noise.

    Both are plain text patterns and neither needs a compiler.
    """
    decl, impl = {}, {}
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"partial\s+void\s+(\w+)\s*\(([^)]*)\)\s*;", text):
            decl[m.group(1)] = (path.name, m.group(2).strip())
        for m in re.finditer(r"partial\s+void\s+(\w+)\s*\(([^)]*)\)\s*\n?\s*\{", text):
            impl[m.group(1)] = (path.name, m.group(2).strip())

    problems = []
    for name, (where, args) in impl.items():
        if name not in decl:
            problems.append(
                f"CS0759: {where} implements partial '{name}' but no file "
                f"declares 'partial void {name}(...);'")
            continue
        dwhere, dargs = decl[name]
        if _names(dargs) != _names(args):
            problems.append(
                f"CS8826: '{name}' parameter names differ -- "
                f"{dwhere} says ({dargs}), {where} says ({args})")
    return problems


def _names(args):
    out = []
    for part in args.split(","):
        part = part.strip()
        if part:
            out.append(part.split()[-1])
    return out


def main():
    problems = []
    for p in sorted(HERE.glob("*.cs")):
        check_cs(p, problems)
    for p in sorted(HERE.glob("*.csproj")):
        check_csproj(p, problems)

    problems += check_partials(sorted(HERE.glob("*.cs")))

    bat = HERE / "build.bat"
    if bat.exists():
        b = bat.read_text(encoding="utf-8")
        for prop in ("NoRender", "NoCumulative"):
            if f"-p:{prop}=true" not in b:
                problems.append(f"build.bat: no fallback pass for {prop}")

    print(f"checked {len(list(HERE.glob('*.cs')))} sources, "
          f"{len(list(HERE.glob('*.csproj')))} project files")
    if problems:
        print(f"\n{len(problems)} problem(s):\n")
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print("no known-pattern problems found")


if __name__ == "__main__":
    main()
