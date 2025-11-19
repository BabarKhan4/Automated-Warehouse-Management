Robot Warehouse Management
=========================

Overview
--------
This repository contains a minimal grid-based warehouse simulation and planner
integration. The simulation (Python + pygame) models robots picking up packages
and delivering them to destinations. Planning is handled via PDDL and the
Fast Downward planner.

Contents
--------
- main.py                — application entrypoint, scenario setup & workflow
- interface.py           — pygame GUI (buttons, drawing, controls)
- environment.py         — grid, obstacles and position helpers
- robot.py               — Robot class (move, pickup, drop)
- package.py             — Package class and state
- pddl_generator.py      — exports current simulation state to a PDDL problem
- planner_interface.py   — wrapper to call Fast Downward
- plan_executor.py       — parse and execute plans; supports parallel execution
- domain.pddl            — PDDL domain for the warehouse
- problem.pddl           — example or template problem (we generate fresh problems)
- downward/              — Fast Downward planner sources/builds (subrepo)
- requirements.txt       — Python dependencies (pygame, etc.)

Features
--------

- Collision management (2025-11-12): added `(occupied ?l - location)` predicate to
  `domain.pddl` and emit `(occupied ...)` facts during problem generation so
  planners can avoid placing two robots in the same cell simultaneously.
  (Use `scripts/add_feature.py` to add future features automatically.)

Quick start (macOS / zsh)
-------------------------
1. Create and activate the project virtualenv (helper available):

```bash
# create/install into ./.venv and install requirements
./.venv/bin/python main.py --setup
```

2. Run the GUI (from repo root):

```bash
# Launch GUI using the venv python
./.venv/bin/python main.py
```

3. Command-line options for `main.py`:
- `--random` : randomize robot/package positions
- `--seed N` : use specific seed for reproducible randomness
- `--setup`  : create/reuse local `.venv` and install requirements
- `--build-planner` : when used with `--setup`, attempt to build Fast Downward
- `--force-recreate` : recreate `.venv` even if it exists

GUI flow
--------
- Extract State: exports current simulation to a generated `problem_generated.pddl`.
- Plan: writes a clean PDDL problem and calls Fast Downward (if present) to
  generate a plan. The planner runs the translator and search; plan is saved to
  `solution.txt` (or similar) when found.
- Execute Plan: executes the plan in-simulation. New executor supports parallel
  execution so multiple robots can execute independent actions in the same tick.
- Reset: resets the simulation; if Randomize is on (or a plan just executed) the
  reset will re-randomize placement.

Planner (Fast Downward)
-----------------------
This project ships a `downward/` directory. Fast Downward requires a compiled
build (C/C++ toolchain). To build the planner locally (optional):

```bash
cd downward
python build.py release
```

After building, the GUI will detect the build and call `downward/fast-downward.py`
with the generated PDDL problem. If you prefer not to build the planner, you can
still test the GUI and extraction functionality.

Why we generate a fresh PDDL problem
-----------------------------------
We create a self-contained problem file (via `write_planner_problem`) each time
before calling the planner. This avoids malformed files caused by template
content or leftover file fragments and ensures the translator accepts the input.

Parallel execution & shortest paths
-----------------------------------
- The plan executor supports `execute_plan` (sequential) and
  `execute_plan_parallel` (parallel scheduling for multiple robots).
- `execute_plan_parallel` creates per-robot action queues and schedules
  non-conflicting actions (avoiding collisions and swapping).
- The executor also supports a shortest-path mode (enabled by default) where
  the executor computes BFS shortest paths for assigned robot-package pairs
  and generates move/pickup/drop sequences from those paths.
- Toggle this behavior by setting `PlanExecutor.shortest_path_mode = False`
  before executing a plan if you want to follow the planner's exact moves.

Developer notes / important code points
--------------------------------------
- `main.py`: scenario setup, obstacle placement, assignments, and `handle_gui_click`.
  - `setup_scenario(randomize, seed)` returns `(env, robots, packages)`.
  - `write_planner_problem(env, robots, packages, filename)` writes a clean problem.
- `pddl_generator.py`: previously used for a template-style export. The app now
  uses `write_planner_problem` to avoid translator errors, but `extract_state_to_pddl`
  still exists for compatibility.
- `plan_executor.py`:
  - `execute_plan(plan)` — sequential execution
  - `execute_plan_parallel(plan)` — parallel scheduling
  - `shortest_path_mode` (default True) — compute shortest paths instead of following planner moves

Testing & debug commands
------------------------
- Generate a reproducible random scenario (seeded), write a fresh PDDL and run the planner:

```bash
# in repo root, using venv python
./.venv/bin/python - <<'PY'
from main import setup_scenario, write_planner_problem
from planner_interface import call_planner
env, robots, packages = setup_scenario(randomize=True, seed=123)
write_planner_problem(env, robots, packages, 'problem_test.pddl')
call_planner('domain.pddl','problem_test.pddl', output_file='solution_test.txt')
PY
```

- Run executor non-GUI for fast iteration (uses `solution_test.txt`):

```bash
./.venv/bin/python - <<'PY'
from plan_executor import parse_plan, PlanExecutor
from main import setup_scenario
env, robots, packages = setup_scenario(randomize=True, seed=123)
plan = parse_plan('solution_test.txt')
exec = PlanExecutor(env, robots, packages, gui_instance=None)
exec.execute_plan_parallel(plan, delay=0)
PY
```

Troubleshooting
---------------
- "No plan found" / translator errors:
  - Ensure the generated PDDL file is valid (we use `write_planner_problem`).
  - If translator complains about `:goal` or malformed content, remove or
    regenerate the problem file and re-run the planner via the GUI or helper
    commands above.
- Packages on obstacles:
  - Scenario setup moves any robot/package that would spawn on an obstacle to
    the nearest free cell. You may see relocation messages printed to terminal
    during GUI startup.
- Planner missing / build missing:
  - Ensure `downward/fast-downward.py` exists and the build directory
    `downward/builds/release/bin` is present. If not, build in `downward/`.

Restore point
-------------
A git tag checkpoint was created before the "final step" work:
- Tag: `restore-before-final-step`
- Commit: `d4b858bf3396535bb16fe48a407215d5069b3539`

You can restore using:

```bash
git checkout restore-before-final-step
```

Contributing
------------
- Follow Python style consistent with the existing code.
- Add tests when altering planner/exec logic.

License
-------
Check the repository root for a LICENSE file. No license file present means
standard GitHub default — add a license file if you plan to publish.

Contact / Author
----------------
Repository: Automated-Warehouse-Management



README created by developer tooling — update as needed.

## Features

- Dynamic Obstacles (toggle) (2025-11-12): Allow user to place/remove obstacles by clicking; toggle between manual placement and randomized mode via GUI button

- Test feature automation (2025-11-12): Helper script added to README features list