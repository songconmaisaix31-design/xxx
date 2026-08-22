"""TagPulse: dependency-free Harness Engineering runner for this Flask MVP."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    label: str
    command: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class StageResult:
    stage: Stage
    passed: bool
    elapsed: float
    output: str


class Console:
    def __init__(self, color: bool) -> None:
        self.color = color
        try:
            "╭─→•".encode(sys.stdout.encoding or "utf-8")
            self.unicode = True
        except UnicodeEncodeError:
            self.unicode = False

    def write(self, text: str = "", *, end: str = "\n") -> None:
        try:
            print(text, end=end, flush=True)
        except UnicodeEncodeError:
            encoding = sys.stdout.encoding or "utf-8"
            safe = text.encode(encoding, errors="backslashreplace").decode(encoding)
            print(safe, end=end, flush=True)

    def paint(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def info(self, text: str) -> None:
        self.write(self.paint(text, "38;5;81"))

    def ok(self, text: str) -> None:
        self.write(self.paint(text, "38;5;82"))

    def warn(self, text: str) -> None:
        self.write(self.paint(text, "38;5;221"))

    def fail(self, text: str) -> None:
        self.write(self.paint(text, "38;5;203"))

    def muted(self, text: str) -> None:
        self.write(self.paint(text, "38;5;244"))

    def accent(self, text: str) -> None:
        self.write(self.paint(text, "1;38;5;45"))


def banner(console: Console) -> None:
    if console.unicode:
        console.info("\n  ╭─ TAGPULSE ───────────────────────── build confidence ─╮")
        console.accent("  │  HARNESS ENGINEERING                                  │")
        console.info("  │  Flask SSR · privacy gates · event state machine      │")
        console.info("  ╰───────────────────────────────────────────────────────╯")
    else:
        console.info("\n  +-- TAGPULSE ---------------------- build confidence --+")
        console.accent("  |  HARNESS ENGINEERING                                  |")
        console.info("  |  Flask SSR / privacy gates / event state machine      |")
        console.info("  +-------------------------------------------------------+")


def print_flow_map(console: Console) -> None:
    console.accent("\n  PRODUCT JOURNEYS")
    arrow = "→" if console.unicode else "->"
    console.write(f"  01  IDENTITY     registration {arrow} mock OAuth {arrow} self_only tags")
    console.write(f"  02  CONNECTION   ready {arrow} calculate {arrow} result {arrow} chat {arrow} L0/L1/L3/L4 {arrow} safety")
    console.write(f"  03  USER EVENT   create {arrow} admin review {arrow} anonymous signup review {arrow} formation {arrow} group")
    console.write(f"  04  MERCHANT     nearby filter {arrow} signup {arrow} deadline {arrow} coupon {arrow} redeem / cancel")
    console.write(f"  05  MODERATION   report {arrow} admin decision {arrow} audit log")


def environment_for_child() -> dict[str, str]:
    environment = os.environ.copy()
    environment.setdefault("PYTHONIOENCODING", "utf-8")
    return environment


def execute_stage(console: Console, stage: Stage, index: int, total: int, verbose: bool) -> StageResult:
    width = max(72, min(shutil.get_terminal_size((92, 24)).columns, 120))
    prefix = f"  {index:02}  {stage.label.upper():<16} {stage.detail} "
    leader = ("·" if console.unicode else ".") * max(3, width - len(prefix) - 14)
    console.write(f"{prefix}{leader} ", end="")
    started = time.perf_counter()
    completed = subprocess.run(
        stage.command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment_for_child(),
        check=False,
    )
    elapsed = time.perf_counter() - started
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    result = StageResult(stage, completed.returncode == 0, elapsed, output)
    if result.passed:
        console.ok(f"  PASS  {elapsed:5.2f}s")
        if verbose and output:
            console.write(indent(output))
    else:
        console.fail(f"  FAIL  {elapsed:5.2f}s")
        if output:
            console.write(indent(output))
    return result


def indent(value: str) -> str:
    return "\n".join(f"      {line}" for line in value.splitlines())


def verification_stages(suite: str) -> list[Stage]:
    python = sys.executable
    stages = [
        Stage("Preflight", (python, "-c", "import flask; print('Flask import OK')"), "runtime and Flask import"),
        Stage("Syntax", (python, "-m", "compileall", "-q", "app", "tests"), "compile application and harness"),
    ]
    if suite in ("all", "core"):
        stages.append(
            Stage("Match motion", ("node", "--test", "tests/match_flow.test.mjs"), "timeline, cancel, retry, reduced motion")
        )
    if suite in ("all", "core"):
        stages.append(
            Stage("Core checks", (python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_core.py", "-v"), "unit and SSR smoke checks")
        )
        stages.append(
            Stage(
                "Feature checks",
                (
                    python, "-m", "unittest",
                    "tests.test_admin_moderation", "tests.test_chat_ui", "tests.test_nearby_events",
                    "tests.test_adapters", "tests.test_prd_acceptance", "-v",
                ),
                "admin, chat, nearby, adapters, PRD gates",
            )
        )
    if suite in ("all", "e2e"):
        stages.append(
            Stage("E2E harness", (python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_e2e_harness.py", "-v"), "isolated complete product flows")
        )
    return stages


def run_verification(console: Console, suite: str, verbose: bool, fail_fast: bool) -> int:
    banner(console)
    separator = "·" if console.unicode else "/"
    coverage = {
        "all": f"43 unit/SSR/contract checks + 4 motion checks {separator} 5 product journeys",
        "core": "43 unit/SSR/contract checks + 4 motion checks",
        "e2e": "5 complete product journeys",
        "doctor": "runtime + syntax",
    }[suite]
    console.muted(f"\n  ISOLATED SQLITE  /  LOCAL DATA UNTOUCHED  /  {coverage}")
    console.accent("\n  PIPELINE")
    stages = verification_stages(suite)
    results: list[StageResult] = []
    for index, stage in enumerate(stages, start=1):
        result = execute_stage(console, stage, index, len(stages), verbose)
        results.append(result)
        if not result.passed and fail_fast:
            console.warn("\n  Fail-fast is enabled; remaining stages were not run.")
            break
    passed = sum(result.passed for result in results)
    elapsed = sum(result.elapsed for result in results)
    if passed == len(stages):
        rule = "─" * 57 if console.unicode else "-" * 57
        console.muted(f"\n  {rule}")
        console.ok(f"  VERIFIED  {passed}/{len(stages)} gates passed  {separator}  {elapsed:.2f}s  {separator}  exit 0")
        serve_command = r".\harness.cmd serve" if os.name == "nt" else "python tools/harness_cli.py serve"
        console.muted(f"  Next: {serve_command}\n")
        return 0
    rule = "─" * 57 if console.unicode else "-" * 57
    console.muted(f"\n  {rule}")
    console.fail(f"  BLOCKED   {passed}/{len(stages)} gates passed  {separator}  {elapsed:.2f}s  {separator}  exit 1")
    console.warn("  Re-run with --verbose after fixing the first failed gate.\n")
    return 1


def run_one_command(console: Console, label: str, command: Sequence[str]) -> int:
    banner(console)
    console.warn(f"  {label}")
    console.warn(f"  $ {' '.join(command)}\n")
    try:
        return subprocess.run(command, cwd=ROOT, env=environment_for_child(), check=False).returncode
    except FileNotFoundError:
        console.fail(f"Command not found: {command[0]}")
        return 127


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TagPulse harness runner. Default command: run the complete isolated verification suite."
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="run the verification pipeline")
    run.add_argument("--suite", choices=("all", "core", "e2e"), default="all", help="select checks to run")
    run.add_argument("--verbose", action="store_true", help="show successful subprocess output")
    run.add_argument("--fail-fast", action="store_true", help="stop after the first failed stage")

    flow = subparsers.add_parser("flow", help="run only the complete HTTP workflow harness")
    flow.add_argument("--verbose", action="store_true", help="show successful subprocess output")
    flow.add_argument("--fail-fast", action="store_true", help="stop after the first failed stage")

    subparsers.add_parser("map", help="show the workflow coverage map")
    subparsers.add_parser("doctor", help="run only runtime and syntax preflight checks")
    subparsers.add_parser("scheduler", help="explicitly process due events in the local instance database")
    subparsers.add_parser("serve", help="start the Flask development server")
    parser.set_defaults(command="run", suite="all", verbose=False, fail_fast=False)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    color = not args.no_color and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    console = Console(color)
    command = args.command or "run"
    try:
        if command == "run":
            return run_verification(console, getattr(args, "suite", "all"), args.verbose, args.fail_fast)
        if command == "flow":
            return run_verification(console, "e2e", args.verbose, args.fail_fast)
        if command == "doctor":
            return run_verification(console, "doctor", False, True)
        if command == "map":
            banner(console)
            print_flow_map(console)
            console.muted("\n  All workflow scenarios run against disposable databases.\n")
            return 0
        if command == "scheduler":
            return run_one_command(console, "This action evaluates and may update the local instance database.", (sys.executable, "-m", "flask", "--app", "run.py", "process-events"))
        if command == "serve":
            return run_one_command(console, "Starting Flask development server. Use Ctrl+C to stop.", (sys.executable, "run.py"))
    except KeyboardInterrupt:
        console.warn("\n  Interrupted by user.")
        return 130
    parser.error(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
