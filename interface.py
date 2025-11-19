# interface.py - lightweight pygame GUI for the warehouse simulator
import pygame
from environment import Environment


class GUI:
    def __init__(self, environment: Environment, robots, packages):
        pygame.init()
        self.environment = environment
        self.robots = robots
        self.packages = packages

        # Layout
        self.cell_size = 60
        self.grid_width = environment.width * self.cell_size
        self.grid_height = environment.height * self.cell_size
        self.info_panel_height = 120
        self.width = self.grid_width + 240
        self.height = self.grid_height + self.info_panel_height

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Robot Warehouse planner")
        self.clock = pygame.time.Clock()

        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (60, 130, 200)
        self.ORANGE = (255, 165, 0)
        self.RED = (200, 40, 40)
        self.GRAY = (160, 160, 160)
        self.LIGHT_GRAY = (230, 230, 230)

        # Buttons and flags
        self.buttons = {}
        self.info_message = "Ready to plan."
        self.randomize_enabled = False
        self.dynamic_obstacles_enabled = False
        self.keep_problem = False
        self.last_execution_success = False
        self.seed = None

        # Confirmation modal for mode switching
        self.pending_mode_confirm = False
        self.pending_mode_target = None

    def _grid_to_pixel_center(self, x, y):
        cx = x * self.cell_size + self.cell_size // 2
        cy = (self.environment.height - 1 - y) * self.cell_size + self.cell_size // 2
        return cx, cy

    def draw(self):
        self.screen.fill(self.WHITE)

        # draw grid cells
        for x in range(self.environment.width):
            for y in range(self.environment.height):
                rx = x * self.cell_size
                ry = (self.environment.height - 1 - y) * self.cell_size
                rect = pygame.Rect(rx, ry, self.cell_size, self.cell_size)
                color = self.GRAY if self.environment.is_obstacle(x, y) else self.LIGHT_GRAY
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, self.BLACK, rect, 1)

        # package destinations
        for pkg in self.packages:
            if getattr(pkg, 'state', None) == 'Delivered':
                continue
            dx, dy = pkg.destination
            cx, cy = self._grid_to_pixel_center(dx, dy)
            pygame.draw.circle(self.screen, self.RED, (cx, cy), 8, 2)

        # packages
        for pkg in self.packages:
            if getattr(pkg, 'state', None) == 'Delivered':
                continue
            if not pkg.is_carried:
                x, y = pkg.position
                cx, cy = self._grid_to_pixel_center(x, y)
                pygame.draw.circle(self.screen, self.ORANGE, (cx, cy), 12)

        # robots
        font = pygame.font.Font(None, 24)
        for r in self.robots:
            x, y = r.position
            cx, cy = self._grid_to_pixel_center(x, y)
            pygame.draw.circle(self.screen, self.BLUE, (cx, cy), 16)
            txt = font.render(str(len(r.carrying)), True, self.WHITE)
            tr = txt.get_rect(center=(cx, cy))
            self.screen.blit(txt, tr)

        # controls
        self._draw_controls()
        # info panel
        self._draw_info()

        # If a modal is active, draw it on top (and populate Confirm buttons)
        if self.pending_mode_confirm:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            modal_w, modal_h = 380, 150
            mx = (self.width - modal_w) // 2
            my = (self.height - modal_h) // 2
            modal = pygame.Rect(mx, my, modal_w, modal_h)
            pygame.draw.rect(self.screen, self.WHITE, modal)
            pygame.draw.rect(self.screen, self.BLACK, modal, 2)

            title = font.render(f"Confirm switch to {self.pending_mode_target} mode?", True, self.BLACK)
            self.screen.blit(title, (mx + 20, my + 20))

            yes = pygame.Rect(mx + 40, my + 80, 120, 40)
            no = pygame.Rect(mx + 220, my + 80, 120, 40)
            pygame.draw.rect(self.screen, (0, 140, 0), yes)
            pygame.draw.rect(self.screen, (180, 30, 30), no)
            ytxt = font.render("Yes", True, self.WHITE)
            ntxt = font.render("No", True, self.WHITE)
            self.screen.blit(ytxt, (yes.x + 46, yes.y + 8))
            self.screen.blit(ntxt, (no.x + 50, no.y + 8))

            # expose to click handler
            self.buttons['ConfirmYes'] = yes
            self.buttons['ConfirmNo'] = no

        pygame.display.flip()

    def _draw_controls(self):
        font = pygame.font.Font(None, 28)
        panel_y = self.grid_height + 10
        labels = ["Extract State", "Plan", "Execute Plan", "Reset", "Toggle Mode"]
        x = 10
        for label in labels:
            surf = font.render(label, True, self.WHITE)
            rect = pygame.Rect(x, panel_y, surf.get_width() + 20, surf.get_height() + 10)

            # special color for Toggle Mode to indicate state
            if label == 'Toggle Mode':
                color = (34, 139, 34) if self.randomize_enabled else (30, 90, 160)
            else:
                color = self.BLACK
            pygame.draw.rect(self.screen, color, rect)
            self.screen.blit(surf, (x + 10, panel_y + 5))
            self.buttons[label] = rect
            x += rect.width + 14

        # status text (show only current mode; dynamic-obstacles label removed)
        status = 'Random' if self.randomize_enabled else 'Manual'
        mode_txt = font.render(f"Mode: {status}", True, self.BLACK)
        self.screen.blit(mode_txt, (x + 10, panel_y + 5))

    def _draw_info(self):
        font = pygame.font.Font(None, 22)
        info_y = self.grid_height + 60
        try:
            msg = self.info_message
        except Exception:
            msg = ""
        self.screen.blit(font.render(msg, True, self.BLACK), (10, info_y))

        info_y += 28
        # simple debug lines
        if len(self.robots) > 0:
            r = self.robots[0]
            self.screen.blit(font.render(f"Robot {r.id}: {r.position} carrying:{len(r.carrying)}", True, self.BLACK), (10, info_y))
            info_y += 20
        if len(self.packages) > 0:
            p = self.packages[0]
            st = getattr(p, 'state', 'Idle')
            self.screen.blit(font.render(f"Package {p.id}: {p.position} -> {p.destination} state:{st}", True, self.BLACK), (10, info_y))

    def update_info(self, message: str):
        self.info_message = message

    def run(self, click_handler):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    # reset the buttons map so stale rects aren't reused
                    # click handler may rely on buttons populated in the last draw
                    click_handler(pos)
            self.draw()
            self.clock.tick(30)

        pygame.quit()
        return True