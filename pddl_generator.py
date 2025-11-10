# pddl_generator.py
import math
import os

def get_zone_name(x, y):
    # FIX 1: Use underscore, not hyphen (zone_x_y)
    return f"zone_{x}_{y}"

def extract_state_to_pddl(environment, robots, packages , output_file = "problem.pddl"):
    template_path = 'problem_template.pddl'
    # Build dynamic facts
    robot_lines = []
    for robot in robots:
        x, y = robot.position
        zone = get_zone_name(x, y)
        robot_lines.append(f"  (at-robot {robot.id.lower()} {zone})")
        if robot.can_carry_more():
            robot_lines.append(f"  (robot-free {robot.id.lower()})")

    pkg_lines = []
    for pkg in packages:
        if pkg.is_carried:
            pkg_lines.append(f"  (carrying {pkg.carrier_id.lower()} {pkg.id.lower()})")
        else:
            x, y = pkg.position
            zone = get_zone_name(x, y)
            pkg_lines.append(f"  (at-package {pkg.id.lower()} {zone})")
        assigned = getattr(pkg, 'assigned_robot_id', None)
        if assigned:
            pkg_lines.append(f"  (assigned {pkg.id.lower()} {assigned.lower()})")

    goal_lines = []
    for pkg in packages:
        dest_x, dest_y = pkg.destination
        dest_zone = get_zone_name(dest_x, dest_y)
        goal_lines.append(f"  (at-package {pkg.id.lower()} {dest_zone})")

    if os.path.exists(template_path):
        # Merge dynamic facts into template
        with open(template_path, 'r') as tf:
            tpl = tf.read()

        # Insert dynamic init facts at marker
        init_marker = ';; DYNAMIC_INIT_MARKER'
        goal_marker = ';; DYNAMIC_GOAL_MARKER'
        if init_marker in tpl:
            tpl = tpl.replace(init_marker, '\n'.join(robot_lines + pkg_lines))
        else:
            # as fallback append at end of (:init ...)
            tpl = tpl.replace(':init\n', ':init\n' + '\n'.join(robot_lines + pkg_lines) + '\n')

        if goal_marker in tpl:
            tpl = tpl.replace(goal_marker, '\n'.join(goal_lines))
        else:
            # fallback: naive replace of goal section
            tpl = tpl.replace('(:goal (and\n', '(:goal (and\n' + '\n'.join(goal_lines) + '\n')

        with open(output_file, 'w') as f:
            f.write(tpl)
    else:
        # old behavior: write full problem.pddl
        with open(output_file , 'w') as f:
            f.write("(define (problem warehouse-delivery)\n")
            f.write(" (:domain warehouse)\n\n")

            # 1. Objects
            f.write(" (:objects\n")
            # Write objects using lowercase IDs to match parser/plan executor normalization
            robot_objects = " ".join(f"{r.id.lower()}" for r in robots)
            f.write(f"  {robot_objects} - robot\n")

            package_objects = " ".join(f"{p.id.lower()}" for p in packages)
            f.write(f"  {package_objects} - package\n")

            zone_objects = [get_zone_name(x, y) for x, y in environment.get_locations()] 
            f.write(f"  {' '.join(zone_objects)} - location\n")

            f.write(" )\n\n")

            # 2. Initial State (:init)
            f.write(" (:init\n")

            # Robot positions and capacity
            for line in robot_lines:
                f.write(line + "\n")

            # Package positions (on ground or in robot) + assigned
            for line in pkg_lines:
                f.write(line + "\n")

            # Connections between adjacent zones
            for x, y in environment.get_locations():
                current_zone = get_zone_name(x, y)
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx , ny = x + dx, y + dy
                    if environment.is_valid_position(nx, ny):
                        neighbor_zone = get_zone_name(nx, ny)
                        f.write(f"  (connected {current_zone} {neighbor_zone})\n")

            f.write(" )\n\n")

            # 3. Goal (:goal)
            f.write(" (:goal (and\n")
            for line in goal_lines:
                f.write(line + "\n")
            f.write(" ))\n")
            f.write(")\n")