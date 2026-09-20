#!/usr/bin/env python3
"""
Generates the headlight-visibility add-on's per-vehicle head_light .sii files
by transforming the BetterFlares dot_7500 pack's files with fixed multipliers.

Source:  tools/extracted/dot_7500/def/vehicle/truck/**/head_light/*.sii
Output:  src/def/vehicle/truck/**/head_light/*.sii  (same relative paths)

Only numeric brightness/range fields are changed; everything else (shape,
aim, masks, metadata) is preserved byte-for-byte via line-based regex edits.
"""
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_ROOT = SCRIPT_DIR / "extracted" / "dot_7500" / "def" / "vehicle" / "truck"
OUT_ROOT = SCRIPT_DIR.parent / "src" / "def" / "vehicle" / "truck"

STAGES = ["low_beam", "hi_beam", "front_beam", "roof_beam", "front_roof_beam"]

COLOR_MULT = 1.35

RANGE_MULT = {
    "low_beam": 1.3,
    "hi_beam": 1.4,
    "front_beam": 1.4,
    "roof_beam": 1.5,
    "front_roof_beam": 1.5,
}

BIAS_ADD = {
    "low_beam": 0.15,
    "hi_beam": 0.15,
    "front_beam": 0.15,
    "roof_beam": 0.20,
    "front_roof_beam": 0.20,
}

# Flat +5 degrees on all stages. Note: aspect stays fixed, so vertical FOV
# (= angle / aspect) widens by the same relative ~5.3% as horizontal.
ANGLE_ADD = {
    "low_beam": 5.0,
    "hi_beam": 5.0,
    "front_beam": 5.0,
    "roof_beam": 5.0,
    "front_roof_beam": 5.0,
}

REFRACTED_COLOR_FRACTION_MULT = 2.0
REFRACTED_RANGE_MULT = 1.3

# One rule per (suffix, transform) applied for every stage prefix.
# transform(old_float) -> new_float
def scalar_rule(mult):
    return lambda v: v * mult

def add_rule(amount):
    return lambda v: v + amount

FIELD_RULES = {
    "_color": scalar_rule(COLOR_MULT),
    "_color_specular": scalar_rule(COLOR_MULT),
    "_color_ambient": scalar_rule(COLOR_MULT),
    "_refracted_color_fraction": scalar_rule(REFRACTED_COLOR_FRACTION_MULT),
    "_refracted_range": scalar_rule(REFRACTED_RANGE_MULT),
}

FLOAT = r"[-+]?[0-9]*\.?[0-9]+"

VEC3_RE = re.compile(r"\(\s*(" + FLOAT + r")\s*,\s*(" + FLOAT + r")\s*,\s*(" + FLOAT + r")\s*\)")
SCALAR_RE = re.compile(r"(" + FLOAT + r")")


def transform_vec3_line(line, mult):
    def repl(m):
        vals = [round(float(m.group(i)) * mult, 6) for i in (1, 2, 3)]
        return "(" + ", ".join(f"{v:g}" for v in vals) + ")"
    return VEC3_RE.sub(repl, line, count=1)


def transform_scalar_line(line, fn):
    def repl(m):
        v = fn(float(m.group(1)))
        return f"{v:g}"
    return SCALAR_RE.sub(repl, line, count=1)


def process_file(text: str) -> str:
    out_lines = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        matched = False

        for stage in STAGES:
            # range field: "<stage>_range: <float>"
            m = re.match(rf"({re.escape(stage)}_range)\s*:\s*(" + FLOAT + r")", stripped)
            if m:
                new_val = float(m.group(2)) * RANGE_MULT[stage]
                line = re.sub(FLOAT, f"{new_val:g}", line, count=1)
                # only replace after the colon; guard against touching key names
                matched = True
                break

            # angle field: "<stage>_angle: <float>"
            m = re.match(rf"({re.escape(stage)}_angle)\s*:\s*(" + FLOAT + r")", stripped)
            if m:
                new_val = float(m.group(2)) + ANGLE_ADD[stage]
                line = re.sub(FLOAT, f"{new_val:g}", line, count=1)
                matched = True
                break

            # bias field: "<stage>_bias: <float>"
            m = re.match(rf"({re.escape(stage)}_bias)\s*:\s*(" + FLOAT + r")", stripped)
            if m:
                new_val = float(m.group(2)) + BIAS_ADD[stage]
                line = re.sub(FLOAT, f"{new_val:g}", line, count=1)
                matched = True
                break

            # color-family fields (vec3): "<stage><suffix>: (r, g, b)"
            for suffix in ("_color", "_color_specular", "_color_ambient"):
                key = f"{stage}{suffix}"
                if stripped.startswith(key + ":"):
                    line = transform_vec3_line(line, COLOR_MULT)
                    matched = True
                    break
            if matched:
                break

            # refracted scalar fields
            for suffix, fn in (
                ("_refracted_color_fraction", FIELD_RULES["_refracted_color_fraction"]),
                ("_refracted_range", FIELD_RULES["_refracted_range"]),
            ):
                key = f"{stage}{suffix}"
                if stripped.startswith(key + ":"):
                    line = transform_scalar_line(line, fn)
                    matched = True
                    break
            if matched:
                break

        out_lines.append(line)
    return "".join(out_lines)


def main():
    if not SRC_ROOT.exists():
        raise SystemExit(f"Source not found: {SRC_ROOT}")

    files = sorted(SRC_ROOT.glob("*/head_light/*.sii"))
    if not files:
        raise SystemExit("No head_light .sii files found under source root")

    count = 0
    for f in files:
        rel = f.relative_to(SRC_ROOT)
        out_path = OUT_ROOT / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        text = f.read_text(encoding="utf-8")
        out_path.write_text(process_file(text), encoding="utf-8")
        count += 1

    print(f"Generated {count} files under {OUT_ROOT}")


if __name__ == "__main__":
    main()
