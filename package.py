# package.py
class Package: # FIX: Uppercase 'P'
    def __init__(self, pkg_id, position, destination):
        self.id = pkg_id
        self.position = position  # (x, y)
        self.destination = destination  # (x, y)
        self.is_carried = False
        self.carrier_id = None
        # id of robot assigned (string) — set by scenario setup when needed
        self.assigned_robot_id = None
        self.state = "Waiting"

    def __repr__(self):
        return f"Package({self.id}, Pos:{self.position}, Dest:{self.destination}, Carried:{self.is_carried})"