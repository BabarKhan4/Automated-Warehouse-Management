class Environment:
    def __init__(self, width=7, height=7):
        self.width = max(5, width)
        self.height = max(5, height)
        self.obstacles = set()

    def is_obstacle(self, x, y):
        return (x, y) in self.obstacles
    
    
    def is_valid_position(self, x, y):
        in_bounds = 0 <= x <self.width and 0 <= y <self.height
        return in_bounds and not self.is_obstacle(x, y)
    
    def add_obstacle(self, x, y):
        self.obstacles.add((x, y))

    def get_locations(self):
        locations = []
        for x in range(self.width):
            for y in range(self.height):
                if not self.is_obstacle(x, y):
                    locations.append((x, y))
        return locations