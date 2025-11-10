# pddl_generator.py
import math

def get_zone_name(x, y):
    # FIX 1: Use underscore, not hyphen (zone_x_y)
    return f"zone_{x}_{y}"

def extract_state_to_pddl(environment, robots, packages , output_file = "problem.pddl"):
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
        for robot in robots:
            x, y = robot.position
            zone = get_zone_name(x, y)
            # Write robot facts using lowercase IDs
            f.write(f"  (at-robot {robot.id.lower()} {zone})\n") 

            if robot.can_carry_more():
                f.write(f"  (robot-free {robot.id.lower()})\n")

        # Package positions (on ground or in robot)
        for pkg in packages:
            if pkg.is_carried:
                # Domain defines (carrying ?r - robot ?p - package)
                # Write robot first, then package, and use lowercase IDs
                f.write(f"  (carrying {pkg.carrier_id.lower()} {pkg.id.lower()})\n")
            else:
                x, y = pkg.position
                zone = get_zone_name(x, y)
                f.write(f"  (at-package {pkg.id.lower()} {zone})\n")
        
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
        for pkg in packages:
            dest_x, dest_y = pkg.destination
            dest_zone = get_zone_name(dest_x, dest_y)
            f.write(f"  (at-package {pkg.id.lower()} {dest_zone})\n")
        f.write(" ))\n")
        f.write(")\n")