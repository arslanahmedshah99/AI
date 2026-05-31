"""Base Agent"""
from config import *

class Agent:
    def __init__(self, name, x, y, health=100, energy=100):
        self.name       = name
        self.x          = x
        self.y          = y
        self.health     = health
        self.energy     = energy
        self.max_health = health
        self.max_energy = energy
        self.alive      = True
        self.turn_count = 0

    def move(self, dx, dy, environment):
        if self.energy < ENERGY_MOVE:
            return False, f"{self.name}: No energy to move"
        nx = (self.x + dx) % environment.width
        ny = (self.y + dy) % environment.height
        if not environment.is_passable(nx, ny):
            return False, f"{self.name}: Cell blocked"
        self.x = nx
        self.y = ny
        self.energy -= ENERGY_MOVE
        dmg = environment.get_hazard_damage(self.x, self.y)
        if dmg > 0:
            self.take_damage(dmg)
        return True, f"{self.name} -> ({self.x},{self.y})"

    def move_toward(self, tx, ty, environment):
        dx = 0; dy = 0
        diffx = tx - self.x
        diffy = ty - self.y
        # wrap-aware
        if abs(diffx) > environment.width // 2:
            diffx = -diffx
        if abs(diffy) > environment.height // 2:
            diffy = -diffy
        if abs(diffx) >= abs(diffy):
            dx = 1 if diffx > 0 else (-1 if diffx < 0 else 0)
        else:
            dy = 1 if diffy > 0 else (-1 if diffy < 0 else 0)
        if dx == 0 and dy == 0:
            return True, f"{self.name}: already at target"
        return self.move(dx, dy, environment)

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        if self.health == 0:
            self.alive = False

    def rest(self):
        self.energy = min(self.max_energy, self.energy + ENERGY_REST_GAIN)
        if self.health < 30:
            self.health = min(self.max_health, self.health + 5)
        return True, f"{self.name} rested. E={self.energy}"

    def distance_to(self, tx, ty):
        dx = min(abs(self.x-tx), GRID_WIDTH  - abs(self.x-tx))
        dy = min(abs(self.y-ty), GRID_HEIGHT - abs(self.y-ty))
        return dx + dy

    def status(self):
        return {"name": self.name, "pos": (self.x, self.y),
                "health": self.health, "energy": self.energy, "alive": self.alive}
