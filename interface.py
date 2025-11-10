# interface.py (formerly gui.py)
import pygame 
import time
from environment import Environment
from robot import Robot 
from package import Package
# NOTE: Removed confusing self-import (e.g., from interface import GUI)

class GUI:
    def __init__(self, environment, robots, packages):
        pygame.init()
        self.environment = environment
        self.robots = robots
        self.packages = packages
        self.info_message = "Ready to plan."
        
        self.cell_size = 60
        self.grid_width = environment.width * self.cell_size
        self.grid_height = environment.height * self.cell_size 
        self.info_panel_height = 100
        
        # FIX: Increase width to fit all four buttons plus padding
        self.WIDTH_BUFFER = 230 
        self.width = self.grid_width + self.WIDTH_BUFFER
        
        self.height = self.grid_height + self.info_panel_height 

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Robot Warehouse planner")
        self.clock = pygame.time.Clock()

        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (100, 150, 255)  
        self.ORANGE = (255, 165, 0) 
        self.RED = (255, 50, 50)    
        self.GRAY = (128, 128, 128) 
        self.LIGHT_GRAY = (220, 220, 220) 

        self.buttons = {}
        # runtime GUI options
        self.randomize_enabled = False
        self.seed = None

    def _get_draw_coords(self,x, y):
        center_x  = x * self.cell_size + self.cell_size // 2
        center_y = (self.environment.height - 1 - y) * self.cell_size + self.cell_size // 2
        return center_x, center_y
    
    def draw(self):
        self.screen.fill(self.WHITE)
        for x in range(self.environment.width):
            for y in range(self.environment.height):
                rect_x = x * self.cell_size
                rect_y = (self.environment.height - 1 - y) * self.cell_size 
                
                rect = pygame.Rect(rect_x, rect_y, self.cell_size, self.cell_size)

                color = self.GRAY if self.environment.is_obstacle(x, y) else self.LIGHT_GRAY
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, self.BLACK, rect, 1) 

        for pkg in self.packages:
            dest_x, dest_y = pkg.destination
            center_x, center_y = self._get_draw_coords(dest_x, dest_y)
            pygame.draw.circle(self.screen, self.RED, (center_x, center_y), 10, 2)

        for pkg in self.packages:
            if not pkg.is_carried:
                x, y = pkg.position
                center_x, center_y = self._get_draw_coords(x, y)
                pygame.draw.circle(self.screen, self.ORANGE, (center_x, center_y), 15)

        font = pygame.font.Font(None, 24)
        for robot in self.robots:
            x, y = robot.position
            center_x, center_y = self._get_draw_coords(x, y)
            
            pygame.draw.circle(self.screen, self.BLUE, (center_x, center_y), 20)
            
            text = font.render(str(len(robot.carrying)), True, self.WHITE)
            text_rect = text.get_rect(center=(center_x, center_y))
            self.screen.blit(text, text_rect)
        
        self._draw_controls()
        self._draw_info()

        pygame.display.flip()

    def _draw_controls(self):
        panel_y = self.grid_height + 10
        font = pygame.font.Font(None, 30)
        
        button_labels = ["Extract State", "Plan", "Execute Plan", "Reset"]
        current_x = 10
        for label in button_labels:
            text_surface = font.render(label, True, self.WHITE)
            button_rect = pygame.Rect(current_x, panel_y, 
                                      text_surface.get_width() + 20, text_surface.get_height() + 10)
            
            pygame.draw.rect(self.screen, self.BLACK, button_rect)
            self.screen.blit(text_surface, (current_x + 10, panel_y + 5))
            
            self.buttons[label] = button_rect
            # Adjusted spacing since the window is wider
            current_x += button_rect.width + 20 
        # no Randomize button in UI per user preference

    def _draw_info(self):
        info_y = self.grid_height + 60
        font = pygame.font.Font(None, 24)
        
        delivered = sum(1 for p in self.packages if p.position == p.destination and not p.is_carried)
        info_text = f"Packages delivered: {delivered}/{len(self.packages)}"
        text = font.render(info_text, True, self.BLACK)
        self.screen.blit(text, (10, info_y))
        
        status_text = f"Status: {self.info_message}"
        text_status = font.render(status_text, True, self.BLACK)
        self.screen.blit(text_status, (10, info_y + 20))

        # Show robot/package locations for quick debugging
        info_y2 = info_y + 50
        try:
            if len(self.robots) > 0:
                r = self.robots[0]
                robot_text = f"Robot {r.id}: {r.position} carrying:{len(r.carrying)}"
                self.screen.blit(font.render(robot_text, True, self.BLACK), (10, info_y2))
                info_y2 += 20
            if len(self.packages) > 0:
                p = self.packages[0]
                pkg_text = f"Package {p.id}: {p.position} -> {p.destination} state:{p.state}"
                self.screen.blit(font.render(pkg_text, True, self.BLACK), (10, info_y2))
        except Exception:
            pass

    def update_info(self, message):
        self.info_message = message

    def run(self, game_loop_handler):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    game_loop_handler(pos)
            
            self.draw()
            self.clock.tick(60) 
        
        pygame.quit()
        return True