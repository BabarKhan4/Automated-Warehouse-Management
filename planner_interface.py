# planner_interface.py
import subprocess
import os
import sys
from typing import Optional

def call_planner(domain_file, problem_file, output_file="solution.txt"):
    """
    Calls Fast Downward to solve the PDDL problem using the absolute path.
    Returns True if a plan was found, False otherwise.

    Notes:
    - Fast Downward saves the plan in a file named 'sas_plan' by default.
    - Fast Downward does NOT print "Solution found", so we check the plan file instead.
    """
    
    # Use the repository's downward/fast-downward.py script if present.
    # Run it with the current Python interpreter (sys.executable) so the venv is used.
    PLANNER_PATH = os.path.join(os.getcwd(), "downward", "fast-downward.py")

    if not os.path.exists(PLANNER_PATH):
        print(f"❌ Planner script not found at {PLANNER_PATH}.\nMake sure the `downward/fast-downward.py` script exists in the repo.")
        return False
    
    # Fast Downward requires compiled planner builds under downward/builds/release/bin
    build_bin_dir = os.path.join(os.getcwd(), "downward", "builds", "release", "bin")
    if not os.path.isdir(build_bin_dir):
        print("❌ Fast Downward build not found.")
        print(f"Expected build directory: {build_bin_dir}")
        print("To build Fast Downward, run the following in the 'downward' folder:")
        print("  cd downward && python build.py release")
        print("Note: building requires a C/C++ toolchain (cmake, make, a compiler).")
        return False

    python_exec = sys.executable or "python"

    # Use absolute paths for the domain and problem so the planner can find them.
    domain_file = os.path.abspath(domain_file)
    problem_file = os.path.abspath(problem_file)

    cmd = [
        python_exec,
        PLANNER_PATH,
        domain_file,
        problem_file,
        "--search",
        "astar(lmcut())",
    ]
    
    try:
        # Run Fast Downward
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # increase timeout to 120s
            cwd=os.getcwd(),
        )
        
        # --- FIXED SUCCESS CHECK ---
        # Fast Downward doesn't always print "Plan found"; check for the output plan file.
        if os.path.exists("sas_plan"):
            print("✅ Plan found successfully! (sas_plan created)")

            # Rename the plan file to the desired output
            if os.path.exists("sas_plan"):
                try:
                    os.rename("sas_plan", output_file)
                except FileExistsError:
                    # If output_file already exists, remove and rename
                    os.remove(output_file)
                    os.rename("sas_plan", output_file)
            return True
        else:
            print("❌ No plan found.")
            print("--- Planner Output ---")
            print(result.stdout)
            print("--- End Output ---")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️ Timeout: Planner took too long.")
        return False
    except FileNotFoundError:
        print("❌ Error: Planner not found. Verify the absolute path is correct.")
        return False
    except Exception as e:
        print(f"❌ Error calling planner: {e}")
        return False
