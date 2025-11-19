# main.py
import sys
import os 
import argparse
import random
import subprocess
import shutil
from environment import Environment
from robot import Robot
from package import Package
from interface import GUI 
from pddl_generator import extract_state_to_pddl, parse_connectivity_from_domain
from pddl_generator import get_zone_name
from planner_interface import call_planner
from plan_executor import PlanExecutor, parse_plan


def clear_problem_init(problem_path='problem.pddl'):
    """Remove the first (:init ...) block from a problem PDDL file.

    This is a simple text-based parenthesis matcher: it finds the first
    occurrence of '(:init' and removes the balanced parentheses block that
    follows. If no (:init is found the function does nothing.
    """
    try:
        with open(problem_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return

    idx = content.find('(:init')
    if idx == -1:
        # nothing to clear
        return

    # find the matching closing parenthesis for this (:init block
    i = idx
    depth = 0
    end_idx = -1
    while i < len(content):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                end_idx = i
                break
        i += 1

    if end_idx == -1:
        # malformed file; do not modify
        return

    # Replace the init block with a short comment placeholder
    new_content = content[:idx] + ";; (:init removed by Reset — regenerate via generator)\n" + content[end_idx+1:]
    try:
        with open(problem_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception:
        # fail silently; Reset should not crash the GUI
        pass

def reachable(start, goal, env):
    """Module-level reachability check (BFS) between two grid cells avoiding obstacles."""
    from collections import deque
    sx, sy = start
    gx, gy = goal
    if not env.is_valid_position(sx, sy) or not env.is_valid_position(gx, gy):
        return False
    q = deque()
    q.append((sx, sy))
    seen = { (sx, sy) }
    while q:
        x, y = q.popleft()
        if (x, y) == (gx, gy):
            return True
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < env.width and 0 <= ny < env.height and (nx, ny) not in seen and env.is_valid_position(nx, ny):
                seen.add((nx, ny))
                q.append((nx, ny))
    return False

def write_planner_problem(env, robots, packages, output_file):
    """Write a clean PDDL problem file (no template content) tailored to the current env.

    This writer also emits `(occupied <location>)` facts for every location
    currently occupied by a robot so the planner can enforce collision
    avoidance. The domain declares the `(occupied ?l - location)` predicate
    and the `move` action updates occupied facts when robots move.

    The goal is that planners will not generate plans that place two robots in
    the same cell at the same time because moves require the destination to be
    unoccupied.
    """
    with open(output_file, 'w') as f:
        f.write('(define (problem warehouse-delivery)\n')
        f.write(' (:domain warehouse)\n\n')

        # objects
        f.write(' (:objects\n')
        robot_objects = ' '.join(r.id.lower() for r in robots)
        f.write(f'  {robot_objects} - robot\n')
        package_objects = ' '.join(p.id.lower() for p in packages)
        f.write(f'  {package_objects} - package\n')
        zone_objects = [get_zone_name(x,y) for x,y in env.get_locations()]
        f.write('  ' + ' '.join(zone_objects) + ' - location\n')
        f.write(' )\n\n')

        # init
        f.write(' (:init\n')
        for r in robots:
            zx = get_zone_name(*r.position)
            f.write(f'  (at-robot {r.id.lower()} {zx})\n')
            # mark occupied cells so planner enforces mutual exclusion
            f.write(f'  (occupied {zx})\n')
            if r.can_carry_more():
                f.write(f'  (robot-free {r.id.lower()})\n')

        for p in packages:
            if p.is_carried:
                f.write(f'  (carrying {p.carrier_id.lower()} {p.id.lower()})\n')
            else:
                f.write(f'  (at-package {p.id.lower()} {get_zone_name(*p.position)})\n')
            assigned = getattr(p, 'assigned_robot_id', None)
            if assigned:
                f.write(f'  (assigned {p.id.lower()} {assigned.lower()})\n')

        # connectivity only over non-obstacle locations
        # Prefer connectivity documented in domain.pddl (comments) as the
        # canonical source-of-truth for static connectivity. The parser will
        # filter out any connections that reference obstacle cells in the
        # current environment.
        conns = parse_connectivity_from_domain('domain.pddl', env=env)
        if conns:
            for a, b in conns:
                f.write(f'  (connected {a} {b})\n')
        else:
            for x,y in env.get_locations():
                cur = get_zone_name(x,y)
                for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nx,ny = x+dx, y+dy
                    if env.is_valid_position(nx,ny):
                        f.write(f'  (connected {cur} {get_zone_name(nx,ny)})\n')

        f.write(' )\n\n')

        # goal
        f.write(' (:goal (and\n')
        for p in packages:
            f.write(f'  (at-package {p.id.lower()} {get_zone_name(*p.destination)})\n')
        f.write(' ))\n')
        f.write(')\n')

# --- SCENARIO SETUP ---
def setup_scenario(randomize: bool = False, seed: int | None = None):
    """Defines the simplest possible scenario to ensure planning works.

    If `randomize` is True, robot and package positions (and package destination)
    will be chosen randomly from free cells. `seed` can be provided for
    reproducible randomness.
    """
    env = Environment(width=7, height=7)
    obs_pairs = 2

    def find_nearest_free(start_pos, env, forbidden=None):
        # BFS outward to find nearest cell not in obstacles and not in forbidden
        from collections import deque
        if forbidden is None:
            forbidden = set()
        sx, sy = start_pos
        if (sx, sy) not in env.obstacles and (sx, sy) not in forbidden:
            return (sx, sy)
        q = deque()
        q.append((sx, sy))
        seen = { (sx, sy) }
        while q:
            x, y = q.popleft()
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx, ny = x+dx, y+dy
                if not (0 <= nx < env.width and 0 <= ny < env.height):
                    continue
                if (nx, ny) in seen:
                    continue
                seen.add((nx, ny))
                if (nx, ny) not in env.obstacles and (nx, ny) not in forbidden:
                    return (nx, ny)
                q.append((nx, ny))
        # fallback: return original
        return start_pos
    return_pos = None
    # find_nearest_free remains in local scope; other helpers (like reachability)
    # are defined at module level below so they can be reused by the planner precheck.

    all_positions = [(x, y) for x in range(env.width) for y in range(env.height)]

    if randomize:
        if seed is not None:
            random.seed(seed)

        # 1) pick robot and package positions first so obstacles won't overlap them
        # Need 6 positions: 2 robots, 2 package starts, 2 package destinations
        if len(all_positions) < 6:
            raise RuntimeError("Grid too small for scenario placement")
        chosen_positions = random.sample(all_positions, k=6)
        robot1_pos = chosen_positions[0]
        robot2_pos = chosen_positions[1]
        pkg1_start = chosen_positions[2]
        pkg1_dest = chosen_positions[3]
        pkg2_start = chosen_positions[4]
        pkg2_dest = chosen_positions[5]

        # 2) place obstacle pairs biased toward center and package starts
        center = (env.width // 2, env.height // 2)
        placed = set()
        attempts = 0
        max_attempts = 400
        anchors = [center, pkg1_start, pkg2_start, pkg1_dest, pkg2_dest]
        while len(placed) < obs_pairs * 2 and attempts < max_attempts:
            attempts += 1
            anchor = random.choices(anchors, weights=[3,1,1,1,1], k=1)[0]
            ax, ay = anchor
            # pick offset biased near anchor but avoid placing on border cells
            ox = ax + random.randint(-2, 2)
            oy = ay + random.randint(-2, 2)
            # ensure candidate and its pair won't be on the outer border
            if not (1 <= ox < env.width-1 and 1 <= oy < env.height-1):
                continue
            if (ox, oy) in chosen_positions or (ox, oy) in placed:
                continue

            orient = random.choice([0, 1])
            if orient == 0:
                nx, ny = ox + 1, oy
            else:
                nx, ny = ox, oy + 1

            # ensure paired cell also stays away from border
            if not (1 <= nx < env.width-1 and 1 <= ny < env.height-1):
                continue
            if (nx, ny) in chosen_positions or (nx, ny) in placed:
                continue

            # Ensure there is at least one-cell gap (including diagonals)
            # between this new pair and any already placed obstacle cells.
            too_close = False
            for (ex, ey) in placed:
                # Chebyshev distance: max(|dx|,|dy|)
                if max(abs(ox - ex), abs(oy - ey)) <= 1 or max(abs(nx - ex), abs(ny - ey)) <= 1:
                    too_close = True
                    break
            if too_close:
                continue

                # ensure no robot/package sits on an obstacle (safety relocation)
                occupied = set()
                for r in (robot1, robot2):
                    if r.position in env.obstacles:
                        newpos = find_nearest_free(r.position, env, forbidden=occupied)
                        print(f"Relocating robot {r.id} from {r.position} to {newpos} (was on obstacle)")
                        r.position = newpos
                    occupied.add(r.position)

                for p in (pkg2, pkg3):
                    if p.position in env.obstacles or p.position in occupied:
                        newpos = find_nearest_free(p.position, env, forbidden=occupied)
                        print(f"Relocating package {p.id} from {p.position} to {newpos} (was invalid)")
                        p.position = newpos
                    occupied.add(p.position)
            placed.add((ox, oy))
            placed.add((nx, ny))

        # fallback: fill near center (but avoid border and respect spacing)
        if len(placed) < obs_pairs * 2:
            for x in range(1, env.width-1):
                for y in range(1, env.height-1):
                    if len(placed) >= obs_pairs * 2:
                        break
                    if (x, y) in chosen_positions or (x, y) in placed:
                        continue
                    if abs(x - center[0]) <= 2 and abs(y - center[1]) <= 2:
                        # ensure spacing from existing placed cells
                        too_close = False
                        for (ex, ey) in placed:
                            if max(abs(x - ex), abs(y - ey)) <= 1:
                                too_close = True
                                break
                        if too_close:
                            continue
                        placed.add((x, y))
                if len(placed) >= obs_pairs * 2:
                    break

        for ox, oy in placed:
            env.add_obstacle(ox, oy)

        # create two robots with capacity 1 each
        robot1 = Robot("R1", position=robot1_pos, capacity=1)
        robot2 = Robot("R2", position=robot2_pos, capacity=1)

        pkg2 = Package("p2", position=pkg1_start, destination=pkg1_dest)
        pkg3 = Package("p3", position=pkg2_start, destination=pkg2_dest)

        # Assign packages to robots based on minimal total distance (2x2 assignment)
        def manhattan(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        d_r1_p1 = manhattan(robot1.position, pkg2.position)
        d_r1_p2 = manhattan(robot1.position, pkg3.position)
        d_r2_p1 = manhattan(robot2.position, pkg2.position)
        d_r2_p2 = manhattan(robot2.position, pkg3.position)

        # two possible assignments: (r1->p2, r2->p3) or (r1->p3, r2->p2)
        cost_a = d_r1_p1 + d_r2_p2
        cost_b = d_r1_p2 + d_r2_p1
        if cost_a <= cost_b:
            pkg2.assigned_robot_id = robot1.id
            pkg3.assigned_robot_id = robot2.id
        else:
            pkg2.assigned_robot_id = robot2.id
            pkg3.assigned_robot_id = robot1.id

        robots = [robot1, robot2]
        packages = [pkg2, pkg3]

        return env, robots, packages

    # deterministic default scenario: two separated pairs (not touching each other)

    env.add_obstacle(2, 2)
    env.add_obstacle(2, 3)
    env.add_obstacle(5, 4)
    env.add_obstacle(5, 5)

    # deterministic: two robots and assign each to the nearer package
    robot1 = Robot("R1", position=(6, 6), capacity=1)
    robot2 = Robot("R2", position=(0, 6), capacity=1)
    pkg2 = Package("p2", position=(5, 5), destination=(0, 0))
    pkg3 = Package("p3", position=(3, 1), destination=(1, 1))

    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # ensure deterministic packages/robots are not placed on obstacles
    occupied = set()
    for r in (robot1, robot2):
        if r.position in env.obstacles:
            newpos = find_nearest_free(r.position, env, forbidden=occupied)
            print(f"Relocating robot {r.id} from {r.position} to {newpos} (was on obstacle)")
            r.position = newpos
        occupied.add(r.position)

    for p in (pkg2, pkg3):
        if p.position in env.obstacles or p.position in occupied:
            newpos = find_nearest_free(p.position, env, forbidden=occupied)
            print(f"Relocating package {p.id} from {p.position} to {newpos} (was invalid)")
            p.position = newpos
        occupied.add(p.position)

    # choose assignment minimizing total distance
    cost_a = manhattan(robot1.position, pkg2.position) + manhattan(robot2.position, pkg3.position)
    cost_b = manhattan(robot1.position, pkg3.position) + manhattan(robot2.position, pkg2.position)
    if cost_a <= cost_b:
        pkg2.assigned_robot_id = robot1.id
        pkg3.assigned_robot_id = robot2.id
    else:
        pkg2.assigned_robot_id = robot2.id
        pkg3.assigned_robot_id = robot1.id

    robots = [robot1, robot2]
    packages = [pkg2, pkg3]

    return env, robots, packages

# --- BUTTON HANDLER (Complete Logic) ---
def handle_gui_click(pos, gui, env, robots, packages):
    domain_file = "domain.pddl"
    # Default extraction target: problem.pddl (template/problem snapshot)
    problem_file = "problem.pddl"
    plan_output_file = "solution.txt"
    
    # --- 1. EXTRACT STATE LOGIC ---
    # --- Randomize toggle (GUI button) ---
    if 'Randomize' in gui.buttons and gui.buttons['Randomize'].collidepoint(pos):
        gui.randomize_enabled = not gui.randomize_enabled
        gui.update_info(f"Randomize set to: {gui.randomize_enabled}")
        return
    if 'RandomizeState' in gui.buttons and gui.buttons['RandomizeState'].collidepoint(pos):
        gui.randomize_enabled = not gui.randomize_enabled
        gui.update_info(f"Randomize set to: {gui.randomize_enabled}")
        return
    
    if 'Extract State' in gui.buttons and gui.buttons['Extract State'].collidepoint(pos):
        gui.update_info("Extracting current state...")
        try:
            extract_state_to_pddl(env, robots, packages, problem_file)
            gui.update_info("State extracted successfully to problem.pddl!")
        except Exception as e:
            gui.update_info(f"Error during extraction: {e}")
        return
    # Toggle overall mode between Random (auto) and Manual (click-to-place)
    if 'Toggle Mode' in gui.buttons and gui.buttons['Toggle Mode'].collidepoint(pos):
        # Ask for confirmation before switching global mode to avoid accidental flips
        target = 'Manual' if gui.randomize_enabled else 'Random'
        gui.pending_mode_confirm = True
        gui.pending_mode_target = target
        gui.update_info(f"Confirm switching to {target} mode...")
        return
    # If a confirmation modal is present, handle Yes/No clicks
    if gui.pending_mode_confirm:
        if 'ConfirmYes' in gui.buttons and gui.buttons['ConfirmYes'].collidepoint(pos):
            # apply the pending mode switch
            if gui.pending_mode_target == 'Manual':
                gui.randomize_enabled = False
                gui.dynamic_obstacles_enabled = True
            else:
                gui.randomize_enabled = True
                gui.dynamic_obstacles_enabled = False
            gui.update_info(f"Mode set to: {gui.pending_mode_target}")
            gui.pending_mode_confirm = False
            gui.pending_mode_target = None
            return
        if 'ConfirmNo' in gui.buttons and gui.buttons['ConfirmNo'].collidepoint(pos):
            gui.pending_mode_confirm = False
            gui.pending_mode_target = None
            gui.update_info("Mode switch cancelled")
            return
    # (Redundant toggle button removed)
            
    # --- 2. PLANNING LOGIC ---
    elif 'Plan' in gui.buttons and gui.buttons['Plan'].collidepoint(pos):
        # write to a fresh generated problem file using the safe writer to avoid
        # any template/header mixups that some on-disk files can introduce
        gen_problem = "problem_generated.pddl"
        write_planner_problem(env, robots, packages, gen_problem)

        # quick reachability pre-check to give clearer errors before calling planner
        # For each package, ensure assigned robot can reach the package start, and
        # the package start can reach the package destination (after pickup)
        unreachable_msgs = []
        # build a map of robots by id for lookup
        robot_map = {r.id: r for r in robots}
        for pkg in packages:
            assigned = getattr(pkg, 'assigned_robot_id', None)
            if assigned is None:
                # if no assignment, skip pre-check (planner will decide)
                continue
            r = robot_map.get(assigned)
            if r is None:
                unreachable_msgs.append(f"Assigned robot {assigned} for package {pkg.id} not present")
                continue
            if not reachable(r.position, pkg.position, env):
                unreachable_msgs.append(f"Robot {r.id} cannot reach package {pkg.id} start")
            if not reachable(pkg.position, pkg.destination, env):
                unreachable_msgs.append(f"Package {pkg.id} start cannot reach its destination")

        if unreachable_msgs:
            gui.update_info("Planning skipped: " + "; ".join(unreachable_msgs))
            return

        # Check planner availability before invoking (give clearer UI message)
        planner_script = os.path.join(os.getcwd(), 'downward', 'fast-downward.py')
        planner_build_dir = os.path.join(os.getcwd(), 'downward', 'builds', 'release', 'bin')
        if not os.path.exists(planner_script):
            gui.update_info(f"Planner script not found at {planner_script}. Please add Fast Downward or run setup with --build-planner.")
            return
        if not os.path.isdir(planner_build_dir):
            gui.update_info(f"Fast Downward build not found at {planner_build_dir}. Build Fast Downward in the 'downward' folder.")
            return

        gui.update_info("Calling planner (Fast Downward)...")
        try:
            found = call_planner(domain_file, gen_problem, plan_output_file)
            if found:
                gui.update_info(f"Plan found! Ready to execute.")
            else:
                gui.update_info("Planning failed (No solution found or error).")
        finally:
            # cleanup the generated problem file to avoid clutter.
            # Keep it only if a GUI flag `keep_problem` is set (for debugging).
            try:
                keep = getattr(gui, 'keep_problem', False)
                if not keep and os.path.exists(gen_problem):
                    os.remove(gen_problem)
            except Exception:
                # ignore cleanup errors but log to GUI
                try:
                    gui.update_info("Note: failed to remove temporary problem file.")
                except Exception:
                    pass
        return
    # --- 3. EXECUTE PLAN LOGIC ---
    elif 'Execute Plan' in gui.buttons and gui.buttons['Execute Plan'].collidepoint(pos):
        try:
            plan = parse_plan(plan_output_file)
            if plan is None or not plan:
                gui.update_info("Error: Plan not found or could not be parsed.")
                return

            gui.update_info(f"Executing plan of {len(plan)} steps...")
            
            executor = PlanExecutor(env, robots, packages, gui)
            # use parallel executor when available to run robots concurrently
            if hasattr(executor, 'execute_plan_parallel'):
                executor.execute_plan_parallel(plan, delay=0.4)
            else:
                executor.execute_plan(plan, delay=0.4)
            
        except Exception as e:
            gui.update_info(f"Execution Error: {e}")

    # --- 4. RESET LOGIC ---
    elif 'Reset' in gui.buttons and gui.buttons['Reset'].collidepoint(pos):
        # When Reset is pressed we want a fresh scenario. If the GUI's randomize
        # toggle is ON, or a plan was executed successfully just before reset,
        # then force randomization (ignore the original seed) so positions change.
        should_randomize = gui.randomize_enabled or getattr(gui, 'last_execution_success', False)
        reset_seed = None if should_randomize else gui.seed
        new_env, new_robots, new_packages = setup_scenario(randomize=should_randomize, seed=reset_seed)
        
        env.width, env.height = new_env.width, new_env.height
        env.obstacles = new_env.obstacles 
        
        robots.clear()
        robots.extend(new_robots)
        packages.clear()
        packages.extend(new_packages)
        
        # clear the last execution flag after a Reset
        try:
            gui.last_execution_success = False
        except Exception:
            pass
        # Clean up any lingering (:init ...) block from the repository template
        # so problem.pddl doesn't retain a stale initial-state between runs.
        try:
            # If we now write extracted state into domain.pddl, clear any lingering
            # (:init ...) block there as well to avoid stale initial states.
            clear_problem_init(problem_file)
        except Exception:
            pass
        gui.update_info("Simulation reset to initial state.")
        return

    # If dynamic obstacle placement is enabled and the click is inside the grid,
    # toggle obstacle presence at the clicked cell. Clicking on occupied cells
    # (robots/packages) will be rejected to avoid inconsistent states.
    try:
        # pixel bounds check
        gx = gui.grid_width
        gy = gui.grid_height
        px, py = pos
        if 0 <= px < gx and 0 <= py < gy and getattr(gui, 'dynamic_obstacles_enabled', False):
            cell_x = px // gui.cell_size
            cell_y = gui.environment.height - 1 - (py // gui.cell_size)
            # don't toggle obstacle on a robot or package
            occupied_by_robot = any(r.position == (cell_x, cell_y) for r in robots)
            occupied_by_pkg = any((not p.is_carried and p.position == (cell_x, cell_y)) for p in packages)
            if occupied_by_robot or occupied_by_pkg:
                gui.update_info("Cannot place obstacle: cell occupied by robot or package")
                return
            if gui.environment.is_obstacle(cell_x, cell_y):
                gui.environment.obstacles.discard((cell_x, cell_y))
                gui.update_info(f"Removed obstacle at {(cell_x, cell_y)}")
            else:
                gui.environment.add_obstacle(cell_x, cell_y)
                gui.update_info(f"Added obstacle at {(cell_x, cell_y)}")
    except Exception as e:
        try:
            gui.update_info(f"Error toggling obstacle: {e}")
        except Exception:
            pass


if __name__ == "__main__":
    def setup_workflow(force_recreate: bool = False, build_planner: bool = False) -> bool:
        """Create a local virtualenv (./.venv), install requirements, and optionally build Fast Downward.

        This function is idempotent by default: if `./.venv` exists it will be reused unless
        `force_recreate` is True.
        """
        repo_root = os.getcwd()
        venv_dir = os.path.join(repo_root, '.venv')

        # 1) create or recreate venv
        if os.path.isdir(venv_dir) and not force_recreate:
            print("Found existing .venv — reusing it. Use --force-recreate to recreate.")
        else:
            if os.path.isdir(venv_dir) and force_recreate:
                print("Removing existing .venv (force recreate)...")
                try:
                    shutil.rmtree(venv_dir)
                except Exception as e:
                    print(f"Failed to remove .venv: {e}")
                    return False

            print("Creating virtualenv at .venv...")
            try:
                subprocess.run([sys.executable, '-m', 'venv', venv_dir], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed creating virtualenv: {e}")
                return False

        # 2) ensure pip is upgraded and install requirements
        venv_python = os.path.join(venv_dir, 'bin', 'python')
        if not os.path.exists(venv_python):
            print("Error: created venv does not contain python at expected path:", venv_python)
            return False

        print("Upgrading pip in venv...")
        try:
            subprocess.run([venv_python, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to upgrade pip: {e}")
            return False

        req_file = os.path.join(repo_root, 'requirements.txt')
        if os.path.exists(req_file):
            # Check installed packages first (pip freeze)
            print(f"Checking installed packages against {req_file}...")
            try:
                freeze = subprocess.run([venv_python, '-m', 'pip', 'freeze'], capture_output=True, text=True, check=True)
                installed_lines = [line.strip() for line in freeze.stdout.splitlines() if line.strip()]
                installed = {}
                for line in installed_lines:
                    if '==' in line:
                        name, ver = line.split('==', 1)
                        installed[name.lower()] = ver
                    else:
                        # non-standard freeze line, ignore or skip
                        pass

                # parse requirements.txt
                with open(req_file, 'r') as rf:
                    req_lines = [ln.strip() for ln in rf.readlines() if ln.strip() and not ln.strip().startswith('#')]

                need_install = False
                for r in req_lines:
                    if '==' in r:
                        name, want_ver = r.split('==', 1)
                        name = name.strip().lower()
                        if installed.get(name) != want_ver.strip():
                            need_install = True
                            break
                    else:
                        # If requirement is unpinned (e.g. `pygame`), check presence only
                        name = r.split()[0].strip().lower()
                        if name not in installed:
                            need_install = True
                            break

                if not need_install:
                    print("All requirements satisfied in .venv — skipping pip install.")
                else:
                    print(f"Installing requirements from {req_file}...")
                    try:
                        subprocess.run([venv_python, '-m', 'pip', 'install', '-r', req_file], check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to install requirements: {e}")
                        return False
            except subprocess.CalledProcessError as e:
                print(f"Failed to check installed packages (pip freeze): {e}. Will attempt install.")
                try:
                    subprocess.run([venv_python, '-m', 'pip', 'install', '-r', req_file], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Failed to install requirements: {e}")
                    return False
        else:
            print("No requirements.txt found — skipping pip install.")

        # 3) optionally build Fast Downward
        if build_planner:
            downward_dir = os.path.join(repo_root, 'downward')
            build_script = os.path.join(downward_dir, 'build.py')
            if os.path.exists(build_script):
                print("Building Fast Downward (this may take some time)...")
                try:
                    subprocess.run([venv_python, build_script, 'release'], cwd=downward_dir, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Fast Downward build failed: {e}")
                    return False
            else:
                print("Fast Downward build script not found — skipping planner build.")

        print("Setup complete. To run the app use: ./.venv/bin/python main.py")
        return True

    if not os.path.exists("domain.pddl"):
        print("CRITICAL ERROR: 'domain.pddl' file not found. Please create it using the provided content.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Warehouse planner')
    parser.add_argument('--random', action='store_true', help='Randomize robot and package positions')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducible scenarios')
    parser.add_argument('--setup', action='store_true', help='Create virtualenv and install project requirements')
    parser.add_argument('--build-planner', action='store_true', help='Attempt to build Fast Downward during setup')
    parser.add_argument('--force-recreate', action='store_true', help='Recreate the .venv even if it exists')
    args = parser.parse_args()

    if args.setup:
        ok = setup_workflow(force_recreate=args.force_recreate, build_planner=args.build_planner)
        sys.exit(0 if ok else 2)

    RANDOMIZE = args.random
    SEED = args.seed

    env, robots, packages = setup_scenario(randomize=RANDOMIZE, seed=SEED)
    gui = GUI(env, robots, packages)
    # initialize GUI runtime flags to reflect CLI options
    gui.randomize_enabled = RANDOMIZE
    gui.seed = SEED
    
    print("Application launched. Use the buttons to Extract, Plan, and Execute.")
    gui.run(lambda pos: handle_gui_click(pos, gui, env, robots, packages))