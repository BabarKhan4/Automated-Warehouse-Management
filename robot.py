class Robot:
    def __init__(self, robot_id, position, capacity=2):
        self.id = robot_id
        self.position = position  # (x, y)
        self.capacity = capacity
        self.carrying = []  # List of package IDs

    def move(self, direction, environment):
        x, y = self.position
        moves = {'up': (x, y+1), 'down': (x, y-1), 'left': (x-1, y), 'right': (x+1, y)}
        new_pos = moves.get(direction)

        if new_pos and environment.is_valid_position(*new_pos):
            self.position = new_pos

            for pkg in self.carrying:
                pkg.position = new_pos
            return True
        return False
    
    def pickup(self, package):
        if self.can_carry_more() and package.position == self.position and not package.is_carried:
            self.carrying.append(package)
            package.is_carried = True
            package.carrier_id = self.id
            package.state = "Transported"
            return True
        return False
    
    def drop(self, package):
        if package in self.carrying:
            self.carrying.remove(package)
            package.is_carried = False
            package.carrier_id = None
            package.position = self.position

            if package.position == package.destination:
                package.state = "Delivered"
            else:
                package.state = "Waiting"
            return True
        return False
    
    def can_carry_more(self):
        return len(self.carrying) < self.capacity
           