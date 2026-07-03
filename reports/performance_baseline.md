# Ebee Conquest performance benchmark

## Protocol

- Host: Windows, Python 3.14.4, pygame-ce 2.5.2, SDL dummy video/audio at 1280x720.
- World: cached production `states.svg` (1,046 shapes), `provinces.svg` (10,046 shapes), and province graph (26,889 edges).
- Scenario: Malaysia, advance to turn 100, inject all 11 countries as war sources (22 active war pairs), then measure three turn advances.
- Frame samples: 30 or more frames per turn after five unmeasured warmup frames. Warmup excludes war injection and one-time render-cache construction.
- FPS is `1000 / average frame ms`; p95 and p99 use nearest-rank percentiles. With 20 samples, p99 is the maximum.
- `--monitor-turns N` means N measured turn advances and therefore N+1 idle-frame snapshots.

Run the standard live benchmark:

```powershell
python tools/profile_game.py --turn 100 --monitor-turns 3 --idle-frames 60 --warmup-frames 5 --result-json reports/live.json
```

CPU profile (run separately because deterministic profiling perturbs frame time):

```powershell
python tools/profile_game.py --turn 100 --monitor-turns 3 --idle-frames 10 --warmup-frames 2 --cprofile reports/live.prof
python -m pstats reports/live.prof
```

Sampling profile with the same ordinary Python entry point:

```powershell
py-spy record -o reports/live.svg -- python tools/profile_game.py --turn 100 --monitor-turns 3 --idle-frames 60
```

Allocation profile (run separately; tracemalloc is intentionally not a timing run):

```powershell
python tools/profile_game.py --turn 2 --monitor-turns 1 --idle-frames 1 --warmup-frames 0 --war-countries Malaysia --tracemalloc reports/allocations.txt
```

Optional line profiling:

```powershell
pip install line_profiler
python tools/profile_game.py --turn 100 --monitor-turns 1 --idle-frames 1 --line-profile reports/lines.txt
```

## Code-path map

- Entrypoint: `main.py` -> `game/menu_gui.py:985` -> `engine/runtime.py:1135`.
- Live loop/render/update: `engine/runtime.py:3598`; map polygons, badges, movement paths, borders, capitals, UI, overlays, event handling, and display flip all remain in this loop.
- Turn resolution: UI button path near `engine/runtime.py:4775`; automated/space-key path near `engine/runtime.py:5392`.
- Movement/combat: `engine/movement.py:456`; A* pathfinding: `engine/movement.py:289`; frontline refresh: `engine/movement.py:1959`.
- NPC turn: `engine/npc/director.py:218`; country/border indexing: `engine/npc/index.py:29`; defense and invasion planning in `engine/npc/defense.py` and `engine/npc/invasion.py`.
- War event handlers and country canonicalization: nested functions in `engine/runtime.py` around lines 1852 and 2920-3120.
- SVG/vector load: `engine/core.py:47`; geometry/province-graph pickle cache: `engine/eso.py:26-175`.
- Animation primitives/particles: `game/animation/motion.py`; UI animation update and draw: `game/ingame_ui.py:2196` and `game/ingame_ui.py:2705`.

## Baseline evidence

The committed pre-change 20-frame headless run at turn 100 created 22 wars. Stable late-war measurements were:

| Metric | Turn 101 | Turn 102 | Turn 103 |
|---|---:|---:|---:|
| Average frame | 26.860 ms | 30.821 ms | 30.900 ms |
| FPS estimate | 37.2 | 32.4 | 32.4 |
| p95 frame | 32.832 ms | 40.139 ms | 34.832 ms |
| Turn advance | 946.749 ms | 932.671 ms | n/a |

At turn 102, render sections were UI 10.779 ms, map polygons 9.066 ms, borders/labels/capitals 3.906 ms, background/grid 2.531 ms, badges 2.495 ms, and movement paths 1.904 ms. Startup RSS rose from 87.6 MiB to 218.1 MiB.

The original first turn-100 sample averaged hundreds of milliseconds while p95 stayed below 30 ms. That was a benchmark artifact: war injection and first cache construction occurred inside the first sampled frame. The new warmup option removes this distortion, while p99/max remain available to expose recurring spikes.

A baseline cProfile run made 159 million calls. The dominant exact hotspot was `runtime.py:1852 canonicalizecountry`: 48.338 s cumulative over 3,695 calls and roughly 128 million `dict.get` calls. The benchmark war injector accounted for 45.095 s, but normal gameplay handlers were also affected: province-control events cost 1.910 s over 48 calls and combat-resolution events cost 1.568 s over 60 calls. `NpcDirector.executeturn` cost 6.519 s over 101 turns and movement processing cost 3.559 s over 101 turns.

## Current measured result

The final 60-frame run used five warmup frames and the same turn-100,
22-war scenario:

| Metric | Turn 100 | Turn 101 | Turn 102 | Turn 103 |
|---|---:|---:|---:|---:|
| Average frame | 21.136 ms | 16.647 ms | 16.579 ms | 16.789 ms |
| FPS estimate | 47.3 | 60.1 | 60.3 | 59.6 |
| p95 frame | 31.634 ms | 18.558 ms | 18.871 ms | 19.231 ms |
| p99/max frame | 34.407 ms | 22.074 ms | 20.284 ms | 19.781 ms |
| Turn advance | 82.250 ms | 69.492 ms | 44.306 ms | n/a |

NPC AI is still the largest turn phase, but scoping it to the 618 playable
provinces reduced it to 78.308/62.633/37.368 ms. Movement/frontline work was
0.102/3.435/3.104 ms, focus/economy 2.107/1.907/2.472 ms, and
capitulation/domestic 1.666/1.486/1.334 ms.

At turn 102, render sections were map polygons 5.961 ms, UI 4.641 ms,
badges 1.502 ms, background/grid 1.354 ms, movement paths 0.592 ms, and
borders/labels/capitals 0.577 ms. Update preparation was 0.081 ms,
event/display tail work was 0.024 ms, and the 60 FPS limiter waited 1.540 ms.
All render/UI sections together were approximately 14.93 ms.
Against the baseline at the same turn, this is a 46.2% average-frame
reduction (30.821 -> 16.579 ms), a 53.0% p95 reduction
(40.139 -> 18.871 ms), and an 85.2% border-section reduction
(3.906 -> 0.577 ms). Turn 102->103 fell 95.3%
(932.671 -> 44.306 ms).

The final structural cProfile made 25.8 million calls, down from 159 million.
Its largest cumulative gameplay functions were `InGameUI.draw` (3.171 s/127),
visible troop-badge preparation (2.185 s/127), badge merging (2.064 s/103),
and `NpcDirector.executeturn` (1.850 s/102). Country-index rebuilds cost
0.872 s/114; pathfinding cost 0.414 s across 5,975 calls. Script-UI `SysFont`
construction fell from 276 calls to 23 one-time startup/cache misses.

## Implemented safe changes

- Reused the NPC country index for O(1) country canonicalization instead of
  rebuilding an alias table from all 10,046 provinces for every war event.
- Passed only the 618 playable provinces and their restricted topology to the
  NPC director. Values still reference the runtime's original province
  objects, preserving troop and control mutations.
- Cached static map polygon and country-border layers with keys covering
  viewport, camera, view mode, ownership revision, hover, selection, movement,
  and animated state. Hovered or pulsing items remain on the live vector path.
- Added a conservative spatial grid before troop-badge overlap checks and
  preserved the legacy pair/union order.
- Cached scanline/light-sweep assets, reused the ambient-particle overlay, and
  culled fully off-screen pulses before allocating temporary surfaces.
- Reused script-UI fonts instead of constructing two `SysFont` objects on
  every frame.
- Added warmup-aware p95/p99/max frame metrics and explicit turn-phase timing.

## Allocation evidence

The isolated tracemalloc run reports retained Python allocations, not SDL surface memory. The leading sites were:

- `engine/eso.py:44`: 45.9 MiB across 1,164,969 objects while unpickling cached SVG geometry.
- `engine/eso.py:128`: 6.1 MiB across 17,919 graph-cache objects.
- `engine/movement.py:194`: 3.8 MiB across 10,046 per-province metadata allocations.
- `engine/core.py:402` and `engine/core.py:248`: about 1.0 MiB each for geometry/parent metadata.

The allocation profiler inflated peak RSS to 637 MiB and frame time by orders of magnitude, so its timing output must not be compared with live results. The final live run's startup RSS was 88.6 -> 222.9 MiB, final RSS was 215.2 MiB, and peak RSS was 276.9 MiB.

Late-war GC measurement found four generation-1 pauses across turns 100-103:
3.579 ms total, 0.895 ms average, and 1.147 ms maximum. GC is measurable but
is not the source of the large turn spikes. The troop-badge spatial filter
reduced `Rect.colliderect` calls by 49.9% in cProfile and cut a synthetic
200-badge candidate pass from 2.013 ms to 0.441 ms.

## Ranked diagnosis

1. NPC planning remains the largest late-war turn phase at 41-76 ms, but is
   now far below the previous 0.9-second spikes. The next target is repeated
   planner graph work, not rendering or GC.
2. Per-frame map polygons and UI remain the largest render costs at about
   12.6 ms combined on turn 102. Cache invalidation and interactive-state
   correctness make further caching medium risk.
3. Rebuilding the country alias map was the strongest proven prior bottleneck.
   The indexed replacement reduced its cProfile total from 48.338 seconds to
   0.0068 seconds.
4. Country-border drawing previously issued about 82,345 line calls over 91
   profiled frames; viewport-keyed caching reduced the turn-102 section by
   84.4%.
5. SVG geometry retention is the largest Python memory consumer. It is loaded
   once from ESO cache, not repeatedly converted per frame. Compact immutable
   geometry or arrays are a higher-risk memory project.

No evidence justifies multiprocessing the render loop. The process benchmark
measured the raw geometry snapshot at 10.2 MiB with about 1.39 seconds to
pickle and 0.58 seconds to unpickle. A compact playable turn snapshot is only
3.65 KiB, but the current planner mutates troop/economy state and emits events
in observable country order. A representative 76.7 ms pure batch regressed to
79.5 ms on two workers; a heavier 389.2 ms batch improved to 238.6 ms. Process
workers should therefore wait for a pure immutable planner API, deterministic
delta validation, and compact persistent worker state.

## Verification

- `python -m pytest -q`: 7 passed.
- Focused performance/NPC/movement/save tests: 60 passed.
- Strict project lint (`flake8`, excluding the local `.venv`): 0 errors.
- `py_compile` and `git diff --check`: passed.
- Explicit collection of all `.playground_testing` tests has 60 passes plus
  eight pre-existing `test_console.py` failures and one pre-existing helper
  collection error caused by its fake NPC interface/fixture signature.
