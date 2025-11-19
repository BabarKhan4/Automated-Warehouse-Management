# pddl_generator.py
import math

def get_zone_name(x, y):
    # FIX 1: Use underscore, not hyphen (zone_x_y)
    return f"zone_{x}_{y}"


def parse_connectivity_from_domain(domain_path='domain.pddl', env=None):
    """Parse commented connectivity facts from domain.pddl and return a list
    of (zone_a, zone_b) tuples filtered by the provided environment.

    The function looks for lines that contain a commented connectivity fact,
    e.g. ';; (connected zone_0_0 zone_0_1)'. If none are found, returns an
    empty list.
    """
    conns = []
    try:
        with open(domain_path, 'r') as df:
            for line in df:
                s = line.strip()
                # accept both commented copies and raw facts
                if s.startswith(';;'):
                    s2 = s[2:].strip()
                else:
                    s2 = s
                if s2.startswith('(connected '):
                    # naive parse: split tokens inside the parentheses
                    try:
                        tokens = s2.strip('()').split()
                        # tokens[0] == 'connected'
                        if len(tokens) >= 3:
                            a = tokens[1]
                            b = tokens[2]
                            # if env is provided, ensure both zones map to valid positions
                            if env is not None:
                                def zone_to_coords(z):
                                    parts = z.split('_')
                                    try:
                                        x = int(parts[1])
                                        y = int(parts[2])
                                        return x, y
                                    except Exception:
                                        return None
                                ca = zone_to_coords(a)
                                cb = zone_to_coords(b)
                                if ca is None or cb is None:
                                    continue
                                if not env.is_valid_position(*ca) or not env.is_valid_position(*cb):
                                    # skip connections that involve obstacle/invalid cells
                                    continue
                            conns.append((a, b))
                    except Exception:
                        continue
    except FileNotFoundError:
        return []
    return conns

def extract_state_to_pddl(environment, robots, packages, output_file = "problem.pddl", include_connectivity: bool = False):
    """Write the current environment, robots and packages to a PDDL problem file.

    Collision management: this function will emit `(occupied <location>)`
    facts for every location currently occupied by a robot. The planner can
    then use the `(occupied ?l - location)` predicate (declared in
    `domain.pddl`) to prevent two robots from being in the same cell at the
    same time. When a robot moves, the domain's `move` action should update
    occupied facts accordingly (origin becomes free, destination becomes
    occupied).

    Parameters
    - environment: Environment instance exposing `get_locations()` and
      `is_valid_position(x,y)`.
    - robots: list of Robot objects with `.id`, `.position`, `.can_carry_more()`.
    - packages: list of Package objects with `.id`, `.position`, `.is_carried`,
      `.carrier_id`, `.destination`, and optional `.assigned_robot_id`.
    - output_file: path to write the PDDL problem.
    - include_connectivity: if True, include (connected ...) facts; otherwise
      omit them (used for repository template extraction).
    """
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

            # Mark the location as occupied by a robot so planners can
            # prevent collision (no two robots should occupy the same cell).
            f.write(f"  (occupied {zone})\n")

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

        # Package assignments (optional)
        for pkg in packages:
            assigned = getattr(pkg, 'assigned_robot_id', None)
            if assigned:
                f.write(f"  (assigned {pkg.id.lower()} {assigned.lower()})\n")
        
        # Optionally include connections between zones. By default (when called
        # from the GUI's "Extract State" action) we do NOT include connectivity
        # facts in the repository template `problem.pddl`. The planner uses
        # `write_planner_problem` which will inject connectivity before planning.
        if include_connectivity:
            # Prefer the connectivity documented in domain.pddl (as comments)
            # if available, otherwise compute from the environment.
            conns = parse_connectivity_from_domain('domain.pddl', env=environment)
            if conns:
                for a, b in conns:
                    f.write(f"  (connected {a} {b})\n")
            else:
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