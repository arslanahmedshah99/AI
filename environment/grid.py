"""Environment Grid — 20x20 space near Tau Ceti"""
import random, math
from config import *

class Cell:
    def __init__(self, cell_type=EMPTY):
        self.cell_type        = cell_type
        self.astrophage_intensity = 0.0
        self.taumoeba_present = False
        self.has_sample       = False
        self.resistance       = 0.0

class Environment:
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.width  = GRID_WIDTH
        self.height = GRID_HEIGHT
        self.grid   = [[Cell() for _ in range(self.width)] for _ in range(self.height)]
        self.turn   = 0
        self._place_structures()
        self._generate_petrova_line()
        self._scatter_astrophage()
        self._place_hazards()
        self._place_taumoeba()

    def _place_structures(self):
        gx, gy = GRACE_START
        self.grid[gy][gx].cell_type = HAIL_MARY
        rx, ry = ROCKY_START
        self.grid[ry][rx].cell_type = BLIP_A
        for tx in range(gx+1, rx):
            self.grid[gy][tx].cell_type = TUNNEL
        # Adrian planet
        ax, ay = ADRIAN_POS
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                nx, ny = ax+dx, ay+dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if math.sqrt(dx*dx+dy*dy) <= 3:
                        self.grid[ny][nx].cell_type   = PLANET_ADRIAN
                        self.grid[ny][nx].astrophage_intensity = 0.5
                        self.grid[ny][nx].taumoeba_present     = True
                        self.grid[ny][nx].has_sample           = True

    def _generate_petrova_line(self):
        # Diagonal astrophage stripe
        for i in range(self.width):
            y = (10 + i) % self.height
            c = self.grid[y][i]
            if c.cell_type == EMPTY:
                c.cell_type = ASTROPHAGE_CLOUD
                c.astrophage_intensity = random.uniform(0.6, 1.0)

    def _scatter_astrophage(self):
        placed = 0
        attempts = 0
        while placed < INITIAL_ASTROPHAGE_CLOUDS and attempts < 500:
            attempts += 1
            x = random.randint(0, self.width-1)
            y = random.randint(0, self.height-1)
            c = self.grid[y][x]
            if c.cell_type == EMPTY:
                c.cell_type = ASTROPHAGE_CLOUD
                c.astrophage_intensity = random.uniform(0.2, 0.5)
                placed += 1

    def _place_hazards(self):
        for _ in range(3):
            x,y = random.randint(0,self.width-1), random.randint(0,self.height-1)
            if self.grid[y][x].cell_type == EMPTY:
                self.grid[y][x].cell_type = RADIATION_ZONE
        for _ in range(3):
            x,y = random.randint(0,self.width-1), random.randint(0,self.height-1)
            if self.grid[y][x].cell_type == EMPTY:
                self.grid[y][x].cell_type = DEBRIS_FIELD

    def _place_taumoeba(self):
        ax, ay = ADRIAN_POS
        for dy in range(-5,6):
            for dx in range(-5,6):
                nx, ny = ax+dx, ay+dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    c = self.grid[ny][nx]
                    if c.cell_type == EMPTY and random.random() < 0.4:
                        c.taumoeba_present = True
                        c.has_sample       = True

    def _neighbors(self, x, y):
        return [((x+dx)%self.width, (y+dy)%self.height)
                for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]]

    def get_cell(self, x, y):
        return self.grid[y % self.height][x % self.width]

    def is_passable(self, x, y):
        return self.get_cell(x, y).cell_type != PLANET_ADRIAN

    def step(self, taumoeba_active=False):
        self.turn += 1
        new_clouds = []
        for y in range(self.height):
            for x in range(self.width):
                c = self.grid[y][x]
                if c.cell_type == ASTROPHAGE_CLOUD:
                    if taumoeba_active:
                        c.resistance = min(1.0, c.resistance + ASTROPHAGE_INTENSITY_INCREASE)
                    rate = ASTROPHAGE_SPREAD_RATE * (1 - c.resistance * 0.5)
                    for nx, ny in self._neighbors(x, y):
                        if self.grid[ny][nx].cell_type == EMPTY and random.random() < rate:
                            new_clouds.append((nx, ny, c.astrophage_intensity * 0.4))
                    c.astrophage_intensity = min(1.0, c.astrophage_intensity + 0.01)
        for nx, ny, inten in new_clouds:
            self.grid[ny][nx].cell_type = ASTROPHAGE_CLOUD
            self.grid[ny][nx].astrophage_intensity = inten

    def apply_taumoeba(self, x, y, radius=3):
        cleared = 0
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                nx, ny = (x+dx)%self.width, (y+dy)%self.height
                c = self.grid[ny][nx]
                if c.cell_type == ASTROPHAGE_CLOUD:
                    eff = 1.0 - c.resistance
                    if random.random() < eff * 0.7:
                        c.astrophage_intensity -= 0.4
                        if c.astrophage_intensity <= 0:
                            c.cell_type = EMPTY
                            c.astrophage_intensity = 0.0
                            cleared += 1
        return cleared

    def get_hazard_damage(self, x, y):
        c = self.get_cell(x, y)
        if c.cell_type == ASTROPHAGE_CLOUD:  return int(ASTROPHAGE_DAMAGE * c.astrophage_intensity)
        if c.cell_type == RADIATION_ZONE:    return RADIATION_DAMAGE
        if c.cell_type == DEBRIS_FIELD:      return DEBRIS_DAMAGE
        return 0

    def count_astrophage_cells(self):
        return sum(1 for row in self.grid for c in row if c.cell_type == ASTROPHAGE_CLOUD)

    def get_grid_snapshot(self):
        return [[self.grid[y][x].cell_type for x in range(self.width)] for y in range(self.height)]
