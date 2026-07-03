"""Measure whether process-based NPC planning can repay Windows spawn and IPC.

This is an isolated benchmark; it does not change game behavior.  It loads the
real cached province topology, compares snapshot representations, and times a
representative country/enemy graph-search batch both serially and through a
spawned ProcessPoolExecutor.

Run from the repository root:
    python tools/benchmark_npc_parallelism.py
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
from pathlib import Path
import pickle
from statistics import median
import time


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MAP_DIRECTORY = REPOSITORY_ROOT / "map"
PROVINCE_CACHE = (
    MAP_DIRECTORY
    / ".ebee_super_optimization"
    / "provinces.ebeecache_v1.pkl"
)
GRAPH_CACHE = (
    MAP_DIRECTORY
    / ".ebee_super_optimization"
    / "provinces.provincegraph.ebeecache_v1.pkl"
)

_WORKER_ADJACENCY = ()


def _parent_state_id(province_id):
    parent_id = province_id.rsplit("_", 1)[0] if "_" in province_id else province_id
    return {"Trung_Bo": "Trong_Bo"}.get(parent_id, parent_id)


def _timed_median(callable_object, iterations):
    samples = []
    result = None
    for _ in range(iterations):
        started = time.perf_counter()
        result = callable_object()
        samples.append((time.perf_counter() - started) * 1000.0)
    return median(samples), result


def _serialization_metrics(label, value, iterations):
    dump_ms, payload = _timed_median(
        lambda: pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL),
        iterations,
    )
    load_ms, _ = _timed_median(lambda: pickle.loads(payload), iterations)
    return {
        "label": label,
        "pickle_kib": len(payload) / 1024.0,
        "dump_ms": dump_ms,
        "load_ms": load_ms,
    }


def _init_worker(adjacency):
    global _WORKER_ADJACENCY
    _WORKER_ADJACENCY = adjacency


def _ping(value):
    return value


def _country_search_task(task):
    country_id, enemy_ids, controller_ids, repeats = task
    enemy_id_set = set(enemy_ids)
    allowed = {
        province_index
        for province_index, controller_id in enumerate(controller_ids)
        if controller_id == country_id or controller_id in enemy_id_set
    }
    sources = [
        province_index
        for province_index, controller_id in enumerate(controller_ids)
        if controller_id == country_id
    ]
    targets = []
    for source_index in sources:
        for neighbor_index in _WORKER_ADJACENCY[source_index]:
            if controller_ids[neighbor_index] in enemy_id_set:
                targets.append(neighbor_index)
    targets = sorted(set(targets))[:16]
    sources = sources[:32]

    checksum = 0
    for _ in range(repeats):
        for source_index in sources:
            queue = [source_index]
            distance = {source_index: 0}
            queue_index = 0
            while queue_index < len(queue):
                current_index = queue[queue_index]
                queue_index += 1
                if current_index in targets:
                    checksum += distance[current_index]
                    break
                next_distance = distance[current_index] + 1
                for neighbor_index in _WORKER_ADJACENCY[current_index]:
                    if neighbor_index not in allowed or neighbor_index in distance:
                        continue
                    distance[neighbor_index] = next_distance
                    queue.append(neighbor_index)
    return checksum


def _load_world():
    with PROVINCE_CACHE.open("rb") as cache_file:
        province_cache = pickle.load(cache_file)
    with GRAPH_CACHE.open("rb") as cache_file:
        graph = pickle.load(cache_file)["graph"]
    with (MAP_DIRECTORY / "countries.json").open("r", encoding="utf-8") as country_file:
        country_data = json.load(country_file)

    state_to_country = {
        state_id: country_entry["Country"]
        for country_entry in country_data
        for state_id in country_entry.get("States", {})
    }
    shapes = province_cache["shapes"]
    playable_ids = tuple(
        shape["id"]
        for shape in shapes
        if _parent_state_id(shape["id"]) in state_to_country
    )
    province_index = {
        province_id: index
        for index, province_id in enumerate(playable_ids)
    }
    adjacency = tuple(
        tuple(
            sorted(
                province_index[neighbor_id]
                for neighbor_id in graph.get(province_id, ())
                if neighbor_id in province_index
            )
        )
        for province_id in playable_ids
    )

    country_names = tuple(sorted(set(state_to_country.values())))
    country_index = {
        country_name: index
        for index, country_name in enumerate(country_names)
    }
    controller_ids = tuple(
        country_index[state_to_country[_parent_state_id(province_id)]]
        for province_id in playable_ids
    )
    compact_playable = (
        playable_ids,
        adjacency,
        controller_ids,
    )
    compact_all = tuple(
        (
            shape["id"],
            state_to_country.get(_parent_state_id(shape["id"])),
            _parent_state_id(shape["id"]),
            100,
            0,
        )
        for shape in shapes
    )
    mutable_turn_state = (
        controller_ids,
        controller_ids,
        tuple(100 for _ in playable_ids),
        tuple(0 for _ in playable_ids),
    )

    # Give every country two deterministic enemies. This approximates the
    # benchmark's simultaneous-war fanout without depending on runtime state.
    tasks = []
    for index in range(len(country_names)):
        enemies = (
            (index + 1) % len(country_names),
            (index + 2) % len(country_names),
        )
        tasks.append((index, enemies, controller_ids))

    return {
        "raw_cache": province_cache,
        "compact_all": compact_all,
        "compact_playable": compact_playable,
        "mutable_turn_state": mutable_turn_state,
        "adjacency": adjacency,
        "tasks": tasks,
        "province_count": len(shapes),
        "playable_count": len(playable_ids),
        "country_count": len(country_names),
    }


def run_benchmark(iterations=7, workers=2, kernel_repeats=20):
    world = _load_world()
    serialization = [
        _serialization_metrics(
            "raw_geometry_cache",
            world["raw_cache"],
            iterations,
        ),
        _serialization_metrics(
            "compact_all_provinces",
            world["compact_all"],
            iterations,
        ),
        _serialization_metrics(
            "compact_playable_topology",
            world["compact_playable"],
            iterations,
        ),
        _serialization_metrics(
            "compact_playable_turn_state",
            world["mutable_turn_state"],
            iterations,
        ),
    ]

    tasks = [
        (country_id, enemy_ids, controller_ids, kernel_repeats)
        for country_id, enemy_ids, controller_ids in world["tasks"]
    ]
    _init_worker(world["adjacency"])
    serial_ms, serial_results = _timed_median(
        lambda: [_country_search_task(task) for task in tasks],
        iterations,
    )

    spawn_context = multiprocessing.get_context("spawn")
    pool_started = time.perf_counter()
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=spawn_context,
        initializer=_init_worker,
        initargs=(world["adjacency"],),
    ) as executor:
        first_ping = executor.submit(_ping, 1).result()
        startup_first_task_ms = (time.perf_counter() - pool_started) * 1000.0
        warm_ping_ms, _ = _timed_median(
            lambda: executor.submit(_ping, first_ping).result(),
            iterations,
        )
        process_ms, process_results = _timed_median(
            lambda: list(executor.map(_country_search_task, tasks)),
            iterations,
        )

    if serial_results != process_results:
        raise RuntimeError("serial and process kernels produced different results")

    return {
        "province_count": world["province_count"],
        "playable_count": world["playable_count"],
        "country_count": world["country_count"],
        "workers": workers,
        "kernel_repeats": kernel_repeats,
        "serialization": serialization,
        "spawn_startup_first_task_ms": startup_first_task_ms,
        "warm_ping_ms": warm_ping_ms,
        "serial_country_batch_ms": serial_ms,
        "process_country_batch_ms": process_ms,
        "process_speedup": serial_ms / process_ms if process_ms else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--kernel-repeats", type=int, default=20)
    parser.add_argument("--json", type=Path)
    arguments = parser.parse_args(argv)
    result = run_benchmark(
        iterations=max(1, arguments.iterations),
        workers=max(1, arguments.workers),
        kernel_repeats=max(1, arguments.kernel_repeats),
    )
    output = json.dumps(result, indent=2)
    print(output)
    if arguments.json:
        arguments.json.parent.mkdir(parents=True, exist_ok=True)
        arguments.json.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
