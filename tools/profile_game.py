"""Repeatable live-game profiler for the automated SDL benchmark scenario.

This remains a normal Python entry point so sampling profilers can attach:
    py-spy record -o reports/ebee.svg -- python tools/profile_game.py
"""

import argparse
import cProfile
import contextlib
import io
import json
import os
from pathlib import Path
import pstats
import re
import sys
import time
import tracemalloc


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


DEFAULT_WAR_COUNTRIES = (
    "Malaysia,Singapore,Indonesia,Thailand,Philippines,Vietnam,Myanmar,"
    "Cambodia,Laos,Brunei,Timor_Leste"
)
KEY_VALUE_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^ ]+)")


class MetricsTee(io.TextIOBase):
    def __init__(self, stream):
        self.stream = stream
        self.lines = []
        self.pending = ""

    def write(self, text):
        self.stream.write(text)
        self.stream.flush()
        self.pending += text
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            if line.startswith("EBEE_PERF_"):
                self.lines.append(line)
        return len(text)

    def flush(self):
        self.stream.flush()


def parsevalue(value):
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def parsemetrics(lines):
    parsed = []
    for line in lines:
        tokens = line.split()
        name = tokens[0]
        fields = {
            key: parsevalue(value.rstrip(","))
            for key, value in KEY_VALUE_PATTERN.findall(line)
        }
        if name.endswith("_SECTION") and len(tokens) > 2 and "=" not in tokens[2]:
            fields["section"] = tokens[2]
        parsed.append({"metric": name, **fields, "raw": line})
    return parsed


def configureenvironment(arguments):
    if arguments.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    os.environ["EBEE_PERF_AUTO_COUNTRY"] = arguments.country
    os.environ["EBEE_PERF_IDLE_FRAMES"] = str(arguments.idle_frames)
    os.environ["EBEE_PERF_WARMUP_FRAMES"] = str(arguments.warmup_frames)

    if arguments.war_countries:
        os.environ["EBEE_PERF_WAR_TURN"] = str(arguments.turn)
        os.environ["EBEE_PERF_MONITOR_TURNS"] = str(arguments.monitor_turns)
        os.environ["EBEE_PERF_WAR_COUNTRIES"] = arguments.war_countries
        os.environ.pop("EBEE_PERF_AUTO_TURN", None)
    else:
        os.environ["EBEE_PERF_AUTO_TURN"] = str(arguments.turn)
        os.environ.pop("EBEE_PERF_WAR_TURN", None)
        os.environ.pop("EBEE_PERF_MONITOR_TURNS", None)
        os.environ.pop("EBEE_PERF_WAR_COUNTRIES", None)


def writetracemallocreport(before, after, outputpath, limit=40):
    outputpath.parent.mkdir(parents=True, exist_ok=True)
    comparison = after.compare_to(before, "lineno")
    with outputpath.open("w", encoding="utf-8") as report:
        report.write("Top net Python allocations during profiled game run\n")
        report.write("=" * 56 + "\n")
        for statistic in comparison[:limit]:
            report.write(f"{statistic}\n")


def buildparser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", default="Malaysia")
    parser.add_argument("--turn", type=int, default=100)
    parser.add_argument("--idle-frames", type=int, default=60)
    parser.add_argument("--warmup-frames", type=int, default=5)
    parser.add_argument(
        "--monitor-turns",
        type=int,
        default=3,
        help="Number of turn advances to time (the run emits one extra idle snapshot).",
    )
    parser.add_argument(
        "--war-countries",
        default=DEFAULT_WAR_COUNTRIES,
        help="Comma-separated war sources; pass an empty string for an idle-only run.",
    )
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--cprofile", type=Path)
    parser.add_argument("--tracemalloc", type=Path)
    parser.add_argument("--line-profile", type=Path)
    parser.add_argument("--result-json", type=Path)
    return parser


def main(argv=None):
    arguments = buildparser().parse_args(argv)
    configureenvironment(arguments)

    from engine.diagnostics import getprocessmemorystats
    from engine.runtime import main as rungame

    callablegame = rungame
    lineprofiler = None
    if arguments.line_profile:
        try:
            from line_profiler import LineProfiler
            from engine import movement
            from engine.npc.director import NpcDirector
        except ImportError as error:
            raise SystemExit(
                "line_profiler is optional; install it with `pip install line_profiler`."
            ) from error
        lineprofiler = LineProfiler()
        lineprofiler.add_function(movement.processmovementorders)
        lineprofiler.add_function(NpcDirector.executeturn)
        callablegame = lineprofiler(callablegame)

    profiler = cProfile.Profile() if arguments.cprofile else None
    if arguments.tracemalloc:
        # A shallow traceback materially reduces profiler distortion while still
        # identifying the allocating source line.
        tracemalloc.start(5)
        allocationsbefore = tracemalloc.take_snapshot()

    tee = MetricsTee(sys.stdout)
    started = time.perf_counter()
    with contextlib.redirect_stdout(tee):
        if profiler:
            profiler.enable()
        try:
            callablegame()
        finally:
            if profiler:
                profiler.disable()
    wallseconds = time.perf_counter() - started

    if profiler:
        arguments.cprofile.parent.mkdir(parents=True, exist_ok=True)
        profiler.dump_stats(str(arguments.cprofile))
        with arguments.cprofile.with_suffix(".txt").open("w", encoding="utf-8") as report:
            stats = pstats.Stats(profiler, stream=report).strip_dirs().sort_stats("cumulative")
            stats.print_stats(80)

    if arguments.tracemalloc:
        allocationsafter = tracemalloc.take_snapshot()
        writetracemallocreport(
            allocationsbefore,
            allocationsafter,
            arguments.tracemalloc,
        )
        tracemalloc.stop()

    if lineprofiler:
        arguments.line_profile.parent.mkdir(parents=True, exist_ok=True)
        with arguments.line_profile.open("w", encoding="utf-8") as report:
            lineprofiler.print_stats(stream=report)

    result = {
        "protocol_version": 1,
        "python": sys.version,
        "wall_seconds": wallseconds,
        "scenario": {
            "country": arguments.country,
            "turn": arguments.turn,
            "idle_frames": arguments.idle_frames,
            "warmup_frames": arguments.warmup_frames,
            "monitor_turns": arguments.monitor_turns,
            "war_countries": arguments.war_countries.split(",") if arguments.war_countries else [],
            "headless": arguments.headless,
        },
        "process_memory": getprocessmemorystats(),
        "metrics": parsemetrics(tee.lines),
    }
    if arguments.result_json:
        arguments.result_json.parent.mkdir(parents=True, exist_ok=True)
        arguments.result_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        "EBEE_PROFILE_COMPLETE "
        f"wall_seconds={wallseconds:.3f} rss_mb={result['process_memory']['rss_mb']}",
        flush=True,
    )
    return result


if __name__ == "__main__":
    main()
