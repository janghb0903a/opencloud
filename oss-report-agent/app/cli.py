from __future__ import annotations

import argparse

from .service import run_generation


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenStack/Kubernetes report generation agent")
    parser.add_argument("--input-path", default=None, help="Override input directory path")
    parser.add_argument("--output-path", default=None, help="Override output markdown file path")
    args = parser.parse_args()

    out = run_generation(input_path=args.input_path, output_path=args.output_path)
    print(f"Report generated: {out}")


if __name__ == "__main__":
    main()
