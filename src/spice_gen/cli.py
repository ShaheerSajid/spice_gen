from __future__ import annotations

import argparse
import pathlib
import sys
import textwrap

from .parser.loader import load_file
from .generator import DIALECT_REGISTRY, get_generator


def _build_arg_parser() -> argparse.ArgumentParser:
    valid_dialects = sorted(DIALECT_REGISTRY)
    p = argparse.ArgumentParser(
        prog="spice_gen",
        description="Generate SPICE netlists from YAML/JSON cell topology files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(f"""\
            Supported dialects: {', '.join(valid_dialects)}

            Examples:
              spice_gen inverter.yaml
              spice_gen nand2.yaml --dialect hspice --output nand2.sp
              spice_gen opamp.yaml --dialect ngspice --stdout
              spice_gen cell.json  --dialect spice3  -v

              # PDK-aware generation
              spice_gen sky130_inverter.yaml --pdk pdks/sky130A.yaml --dialect ngspice --stdout
              spice_gen sky130_inverter.yaml --pdk pdks/sky130A.yaml --corner ff --dialect ngspice
        """),
    )
    p.add_argument(
        "input",
        help="Path to input YAML or JSON topology file",
    )
    p.add_argument(
        "-d", "--dialect",
        default="spice3",
        choices=valid_dialects,
        metavar="DIALECT",
        help=f"SPICE output dialect (default: spice3). Choices: {valid_dialects}",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        metavar="FILE",
        help="Output file path (default: <input_stem>_<dialect>.sp)",
    )
    p.add_argument(
        "--stdout",
        action="store_true",
        help="Write output to stdout instead of a file (ignores --output)",
    )
    p.add_argument(
        "--pdk",
        default=None,
        metavar="PDK_YAML",
        help="Path to PDK config YAML file for technology-aware generation",
    )
    p.add_argument(
        "--corner",
        default=None,
        metavar="CORNER",
        help="Process corner (e.g. tt, ff, ss). Defaults to PDK's default_corner.",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print diagnostic information to stderr",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    input_path = pathlib.Path(args.input)
    if not input_path.exists():
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 1

    # Parse topology
    if args.verbose:
        print(f"[spice_gen] loading: {input_path}", file=sys.stderr)
    try:
        netlist = load_file(input_path)
    except Exception as exc:
        print(f"error: failed to parse input: {exc}", file=sys.stderr)
        return 2

    # PDK resolution (optional)
    if args.pdk:
        pdk_path = pathlib.Path(args.pdk)
        if not pdk_path.exists():
            print(f"error: PDK config file not found: {pdk_path}", file=sys.stderr)
            return 1
        if args.verbose:
            print(f"[spice_gen] applying PDK: {pdk_path}  corner: {args.corner or 'default'}", file=sys.stderr)
        try:
            from .pdk import load_pdk, resolve
            pdk = load_pdk(pdk_path)
            netlist = resolve(netlist, pdk, args.corner or None)
        except Exception as exc:
            print(f"error: PDK resolution failed: {exc}", file=sys.stderr)
            return 2

    # Generate
    if args.verbose:
        print(f"[spice_gen] generating dialect: {args.dialect}", file=sys.stderr)
    try:
        generator = get_generator(args.dialect)
        output_text = generator.generate(netlist)
    except Exception as exc:
        print(f"error: generation failed: {exc}", file=sys.stderr)
        return 3

    # Output
    if args.stdout:
        sys.stdout.write(output_text)
        return 0

    out_path = (
        pathlib.Path(args.output)
        if args.output
        else pathlib.Path(f"{input_path.stem}_{args.dialect}.sp")
    )

    try:
        out_path.write_text(output_text, encoding="utf-8")
        if args.verbose:
            print(f"[spice_gen] written to: {out_path}", file=sys.stderr)
        else:
            print(out_path)
    except OSError as exc:
        print(f"error: could not write output: {exc}", file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())
