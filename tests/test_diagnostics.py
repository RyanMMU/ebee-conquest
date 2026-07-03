from engine.diagnostics import percentile, summarizeframetimes
from tools.profile_game import parsemetrics


def test_percentile_uses_nearest_rank_for_small_samples():
    samples = list(range(1, 21))

    assert percentile(samples, 0.95) == 19
    assert percentile(samples, 0.99) == 20


def test_summarizeframetimes_reports_tail_and_fps():
    summary = summarizeframetimes([10, 20, 30, 40])

    assert summary["count"] == 4
    assert summary["average_ms"] == 25
    assert summary["p95_ms"] == 40
    assert summary["p99_ms"] == 40
    assert summary["max_ms"] == 40
    assert summary["fps"] == 40


def test_parsemetrics_keeps_machine_readable_fields():
    metrics = parsemetrics(
        [
            "EBEE_PERF_TURN_IDLE turn=101 frames=20 avg_ms=26.860 "
            "p95_ms=32.832 p99_ms=40.000 fps_est=37.2 orders=128 active_wars=22",
            "EBEE_PERF_TURN_SECTION turn=101 map_polygons avg_ms=7.125",
        ]
    )

    assert metrics[0]["metric"] == "EBEE_PERF_TURN_IDLE"
    assert metrics[0]["turn"] == 101
    assert metrics[0]["p99_ms"] == 40.0
    assert metrics[0]["active_wars"] == 22
    assert metrics[1]["section"] == "map_polygons"
