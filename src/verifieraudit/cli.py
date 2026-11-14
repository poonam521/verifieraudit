"""Command line: ``verifieraudit audit <folder>`` and ``verifieraudit init <folder>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, report, scaffold
from .audit import Config, audit_task
from .task import TaskError, discover_tasks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verifieraudit",
        description="Audit the graders that score AI coding agents.",
    )
    parser.add_argument("--version", action="version", version=f"verifieraudit {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    audit = commands.add_parser("audit", help="audit one task folder or a folder of tasks")
    audit.add_argument("path")
    audit.add_argument("--out", default="verifieraudit-report",
                       help="folder for report.md and report.json (default: %(default)s)")
    audit.add_argument("--samples", type=int, default=Config.samples,
                       help="random inputs per comparison (default: %(default)s)")
    audit.add_argument("--seed", type=int, default=Config.seed)
    audit.add_argument("--max-mutants", type=int, default=Config.max_mutants)
    audit.add_argument("--workers", type=int, default=None)
    audit.add_argument("--max-false-accept", type=float, default=Config.max_false_accept,
                       help="share of wrong variants a grader may accept (default: %(default)s)")
    audit.add_argument("--max-false-reject", type=float, default=Config.max_false_reject,
                       help="share of correct alternatives a grader may reject (default: %(default)s)")
    audit.add_argument("--strict", action="store_true",
                       help="exit with status 1 if any grader fails (for CI)")

    init = commands.add_parser("init", help="create a starter task folder")
    init.add_argument("path")
    return parser


def _audit(args: argparse.Namespace) -> int:
    try:
        tasks = discover_tasks(args.path)
    except TaskError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    cfg = Config(samples=args.samples, seed=args.seed, max_mutants=args.max_mutants,
                 max_false_accept=args.max_false_accept,
                 max_false_reject=args.max_false_reject)
    if args.workers:
        cfg.workers = args.workers

    audits = []
    for task in tasks:
        print(f"auditing {task.name} ...", file=sys.stderr, flush=True)
        audits.append(audit_task(task, cfg))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(report.to_markdown(audits, cfg), encoding="utf-8")
    (out / "report.json").write_text(report.to_json(audits, cfg), encoding="utf-8")

    print(report.to_console(audits))
    print(f"\nFull report: {out / 'report.md'}")

    if any(audit.error for audit in audits):
        return 2
    if args.strict and any(not audit.passed for audit in audits):
        return 1
    return 0


def _init(args: argparse.Namespace) -> int:
    try:
        written = scaffold.write_task(args.path)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for path in written:
        print(f"created {path}")
    print(f"\nNext: edit the files, then run  verifieraudit audit {args.path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return _audit(args) if args.command == "audit" else _init(args)


if __name__ == "__main__":
    sys.exit(main())
