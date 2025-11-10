# main.py
import sys
import os 
import argparse
import random
from environment import Environment
from robot import Robot
from package import Package
from interface import GUI 
from pddl_generator import extract_state_to_pddl
from planner_interface import call_planner
from plan_executor import PlanExecutor, parse_plan

# --- SCENARIO SETUP ---
def setup_scenario(randomize: bool = False, seed: int | None = None):
    """Defines the simplest possible scenario to ensure planning works.

    If `randomize` is True, robot and package positions (and package destination)
    will be chosen randomly from free cells. `seed` can be provided for
    reproducible randomness.
    """
    env = Environment(width=7, height=7)
    # fixed obstacles
    env.add_obstacle(3, 3)
    env.add_obstacle(3, 4)

    if randomize:
        if seed is not None:
            random.seed(seed)

        free_locs = env.get_locations()
        # choose a robot position
        robot_pos = random.choice(free_locs)

        # remove robot_pos from available locations for packages/destinations
        remaining = [loc for loc in free_locs if loc != robot_pos]

        # choose package start and destination distinct from each other and the robot
        pkg_start = random.choice(remaining)
        remaining = [loc for loc in remaining if loc != pkg_start]
        pkg_dest = random.choice(remaining)

        robot2 = Robot("R2", position=robot_pos, capacity=1)
        pkg2 = Package("p2", position=pkg_start, destination=pkg_dest)
    else:
        # deterministic default scenario
        robot2 = Robot("R2", position=(6, 6), capacity=1)
        pkg2 = Package("p2", position=(5, 5), destination=(0, 0))

    robots = [robot2]
    packages = [pkg2]

    return env, robots, packages

# --- BUTTON HANDLER (Complete Logic) ---
def handle_gui_click(pos, gui, env, robots, packages):
    domain_file = "domain.pddl"
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
            
    # --- 2. PLANNING LOGIC ---
    elif 'Plan' in gui.buttons and gui.buttons['Plan'].collidepoint(pos):
        extract_state_to_pddl(env, robots, packages, problem_file) 
        
        gui.update_info("Calling planner (Fast Downward)...")
        
        if call_planner(domain_file, problem_file, plan_output_file):
            gui.update_info(f"Plan found! Ready to execute.")
        else:
            gui.update_info("Planning failed (No solution found or error).")
            
    # --- 3. EXECUTE PLAN LOGIC ---
    elif 'Execute Plan' in gui.buttons and gui.buttons['Execute Plan'].collidepoint(pos):
        try:
            plan = parse_plan(plan_output_file)
            if plan is None or not plan:
                gui.update_info("Error: Plan not found or could not be parsed.")
                return

            gui.update_info(f"Executing plan of {len(plan)} steps...")
            
            executor = PlanExecutor(env, robots, packages, gui)
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
        gui.update_info("Simulation reset to initial state.")


if __name__ == "__main__":
    if not os.path.exists("domain.pddl"):
        print("CRITICAL ERROR: 'domain.pddl' file not found. Please create it using the provided content.")
        sys.exit(1)
        
    parser = argparse.ArgumentParser(description='Warehouse planner')
    parser.add_argument('--random', action='store_true', help='Randomize robot and package positions')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducible scenarios')
    args = parser.parse_args()

    RANDOMIZE = args.random
    SEED = args.seed

    env, robots, packages = setup_scenario(randomize=RANDOMIZE, seed=SEED)
    gui = GUI(env, robots, packages)
    # initialize GUI runtime flags to reflect CLI options
    gui.randomize_enabled = RANDOMIZE
    gui.seed = SEED
    
    print("Application launched. Use the buttons to Extract, Plan, and Execute.")
    gui.run(lambda pos: handle_gui_click(pos, gui, env, robots, packages))