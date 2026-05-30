import sys, os, threading, time, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tkinter as tk
from config import *

class FuzzySet:
    def __init__(self, lo, mid, hi):
        self.lo = lo; self.mid = mid; self.hi = hi
    def membership(self, x):
        if x <= self.lo or x >= self.hi: return 0.0
        if x <= self.mid: return (x - self.lo) / (self.mid - self.lo + 1e-9)
        return (self.hi - x) / (self.hi - self.mid + 1e-9)

class FuzzyResourceManager:
    def __init__(self):
        self.e_low  = FuzzySet( 0,  0, 35)
        self.e_med  = FuzzySet(20, 50, 75)
        self.e_high = FuzzySet(60,100,100)
        self.h_crit = FuzzySet( 0,  0, 25)
        self.h_low  = FuzzySet(15, 35, 55)
        self.h_ok   = FuzzySet(45,100,100)
    def evaluate(self, energy, health):
        e_lo = self.e_low.membership(energy)
        e_med = self.e_med.membership(energy)
        e_hi = self.e_high.membership(energy)
        h_cr = self.h_crit.membership(health)
        h_lo = self.h_low.membership(health)
        h_ok = self.h_ok.membership(health)
        rule1 = max(e_lo, h_cr)
        rule2 = min(e_med, h_lo)
        rule3 = min(e_hi, h_ok)
        rest_u = max(rule1, rule2 * 0.6)
        proc_u = rule3
        total = rest_u + proc_u + 1e-9
        return rest_u / total, proc_u / total

class Cell:
    def __init__(self, t=EMPTY):
        self.type = t
        self.aph_int = 0.0
        self.has_taum = False

class Grid:
    def __init__(self, seed):
        random.seed(seed)
        self.W = GRID_WIDTH
        self.H = GRID_HEIGHT
        self.cells = [[Cell() for _ in range(self.W)] for _ in range(self.H)]
        self._setup()

    def c(self, x, y):
        return self.cells[y % self.H][x % self.W]

    def passable(self, x, y):
        return self.c(x, y).type != PLANET_ADRIAN

    def _setup(self):
        gx, gy = GRACE_START
        rx, ry = ROCKY_START
        ax, ay = ADRIAN_POS

        self.c(gx, gy).type = HAIL_MARY
        self.c(rx, ry).type = BLIP_A

        self.tunnel_y = gy
        self.tunnel_x_start = gx + 1
        self.tunnel_x_end = gx + 10
        for tx in range(self.tunnel_x_start, self.tunnel_x_end + 1):
            self.cells[self.tunnel_y][tx].type = TUNNEL
        for ty in range(min(gy, ry), max(gy, ry) + 1):
            self.cells[ty][gx + 2].type = TUNNEL
            self.cells[ty][gx + 8].type = TUNNEL

        cx = self.W // 2
        for y in range(self.H):
            for dx in [-1, 0, 1]:
                nx = cx + dx
                if 0 <= nx < self.W and self.cells[y][nx].type == EMPTY:
                    self.cells[y][nx].type = PETROVA_LINE
                    self.cells[y][nx].aph_int = random.uniform(0.7 + abs(dx)*0.05, 1.0)

        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = ax + dx, ay + dy
                if 0 <= nx < self.W and 0 <= ny < self.H:
                    cc = self.cells[ny][nx]
                    cc.type = PLANET_ADRIAN
                    cc.aph_int = 0.5
                    cc.has_taum = True

        for dy in range(-4, 5):
            for dx in range(-4, 5):
                nx, ny = ax + dx, ay + dy
                if 0 <= nx < self.W and 0 <= ny < self.H:
                    cc = self.cells[ny][nx]
                    if cc.type == EMPTY and random.random() < 0.45:
                        cc.has_taum = True

        for _ in range(12):
            x2 = random.randint(0, self.W - 1)
            y2 = random.randint(0, self.H - 1)
            if self.cells[y2][x2].type == EMPTY:
                self.cells[y2][x2].type = ASTROPHAGE_CLOUD
                self.cells[y2][x2].aph_int = random.uniform(0.2, 0.55)

        for _ in range(5):
            x2 = random.randint(0, self.W - 1)
            y2 = random.randint(0, self.H - 1)
            if self.cells[y2][x2].type == EMPTY:
                self.cells[y2][x2].type = RADIATION_ZONE
        for _ in range(5):
            x2 = random.randint(0, self.W - 1)
            y2 = random.randint(0, self.H - 1)
            if self.cells[y2][x2].type == EMPTY:
                self.cells[y2][x2].type = DEBRIS_FIELD

    def step(self, taum_deployed):
        new = []
        for y in range(self.H):
            for x in range(self.W):
                cc = self.cells[y][x]
                if cc.type == PETROVA_LINE:
                    cc.aph_int = min(1.0, cc.aph_int + 0.003)
                elif cc.type == ASTROPHAGE_CLOUD:
                    if taum_deployed:
                        cc.aph_int = max(0, cc.aph_int - 0.012)
                        if cc.aph_int <= 0:
                            cc.type = EMPTY
                            continue
                    cc.aph_int = min(1.0, cc.aph_int + 0.007)
                    for dx2, dy2 in [(0,1),(0,-1),(1,0),(-1,0)]:
                        nx2 = (x + dx2) % self.W
                        ny2 = (y + dy2) % self.H
                        if self.cells[ny2][nx2].type == EMPTY and random.random() < 0.03:
                            new.append((nx2, ny2, cc.aph_int * 0.4))
        for nx2, ny2, ai in new:
            self.cells[ny2][nx2].type = ASTROPHAGE_CLOUD
            self.cells[ny2][nx2].aph_int = ai

    def hazard_dmg(self, x, y):
        cc = self.c(x, y)
        if cc.type == PETROVA_LINE:
            return max(5, int(ASTROPHAGE_DAMAGE * cc.aph_int * 2))
        if cc.type == ASTROPHAGE_CLOUD:
            return max(4, int(ASTROPHAGE_DAMAGE * cc.aph_int * 2))
        if cc.type == RADIATION_ZONE: return RADIATION_DAMAGE
        if cc.type == DEBRIS_FIELD: return DEBRIS_DAMAGE
        return 0

    def count_aph(self):
        return sum(1 for row in self.cells for cc in row if cc.type == ASTROPHAGE_CLOUD)

    def find_sample_near(self, cx, cy, radius=8):
        best = None; bd = 999
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx2 = (cx + dx) % self.W
                ny2 = (cy + dy) % self.H
                if self.cells[ny2][nx2].has_taum:
                    d = abs(dx) + abs(dy)
                    if d < bd: bd = d; best = (nx2, ny2)
        return best

    def collect_at(self, x, y):
        for dx2, dy2 in [(0,0),(0,1),(0,-1),(1,0),(-1,0)]:
            nx2 = (x + dx2) % self.W
            ny2 = (y + dy2) % self.H
            if self.cells[ny2][nx2].has_taum:
                self.cells[ny2][nx2].has_taum = False
                return True
        return False

ALL_DIRS = [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
CARD_DIRS = [(0,1),(0,-1),(1,0),(-1,0)]

class TauSample:
    def __init__(self):
        self.compat = 0.0
        self.gen = 0
        self.n_exp = 0

class BeetleProbe:
    def __init__(self, name, x, y):
        self.name = name
        self.x = x
        self.y = y

class Grace:
    def __init__(self):
        self.x, self.y = GRACE_START
        self.hp = 100
        self.energy = 100
        self.alive = True
        self.knowledge = 0
        self.mscore = 0
        self.samples = []
        self.best = None
        self.taum_dep = False
        self.beetles_left = list(BEETLE_NAMES)
        self.beetle_probes = []
        self.exp_total = 0
        self.exp_ok = 0
        self.flashbacks = []
        self.tunnel_found = False
        self.comms_enabled = False
        self.fuzzy = FuzzyResourceManager()
        self.q = {
            "go_adrian": 2.0, "collect": 2.0, "experiment": 1.5,
            "breed": 1.2, "beetle": 1.0, "communicate": 0.4, "rest": 0.5,
        }
        self.lr = 0.12
        wp_idx = random.randint(0, len(WAYPOINT_SETS) - 1)
        self._waypoints = list(WAYPOINT_SETS[wp_idx])
        self._wp_target = 0

    def viable(self):
        return self.best is not None and self.best.compat >= 0.8

    def act(self, grid, rocky):
        # Tunnel is at y=tunnel_y, x=tunnel_x_start..tunnel_x_end
        if (hasattr(grid, 'tunnel_y') and 
            self.y == grid.tunnel_y and
            grid.tunnel_x_start <= self.x <= grid.tunnel_x_end):
            if not self.tunnel_found:
                self.tunnel_found = True
                self.q["communicate"] = 1.8
        elif grid.cells[self.y % grid.H][self.x % grid.W].type == TUNNEL:
            if not self.tunnel_found:
                self.tunnel_found = True
                self.q["communicate"] = 1.8
        if self.tunnel_found and abs(self.x - rocky.x) + abs(self.y - rocky.y) <= 6:
            self.comms_enabled = True

        for thresh, txt in FLASHBACK_EVENTS.items():
            if self.knowledge >= thresh and thresh not in self.flashbacks:
                self.flashbacks.append(thresh)
                self.knowledge += KNOWLEDGE_FLASHBACK
                return "flashback", f"[FLASHBACK] {txt}"

        rest_u, proc_u = self.fuzzy.evaluate(self.energy, self.hp)
        if rest_u > 0.65:
            self.energy = min(100, self.energy + ENERGY_REST_GAIN)
            if self.hp < 40: self.hp = min(100, self.hp + 8)
            self._update_q("rest", 0.3)
            return "rest", f"Grace [FUZZY] rest_u={rest_u:.2f} HP={self.hp} E={self.energy}"

        current_cell = grid.cells[self.y % grid.H][self.x % grid.W]
        if current_cell.type != PETROVA_LINE and grid.hazard_dmg(self.x, self.y) > 0:
            return "escape", self._escape(grid)

        act = self._pick(grid, rocky)
        msg = self._exec(act, grid, rocky)
        return act, msg

    def _pick(self, grid, rocky):
        s = dict(self.q)
        ax, ay = ADRIAN_POS
        dist = abs(self.x - ax) + abs(self.y - ay)
        has_s = len(self.samples) > 0
        can_b = self.knowledge >= TAUMOEBA_BREED_THRESHOLD and has_s

        if dist > 6: s["go_adrian"] += 2.5
        if dist <= 8: s["collect"] += 2.0
        if has_s: s["experiment"] += 2.5
        else: s["experiment"] -= 3.0; s["breed"] -= 3.0
        if can_b: s["breed"] += 3.0
        if self.viable(): s["beetle"] += 4.0
        if not has_s: s["collect"] += 1.5
        if self.comms_enabled: s["communicate"] += 2.0
        else: s["communicate"] = -99

        for k in s: s[k] += random.uniform(0, 0.3)
        return max(s, key=s.get)

    def _exec(self, act, grid, rocky):
        if act == "go_adrian": return self._go_adrian(grid)
        if act == "collect": return self._collect(grid)
        if act == "experiment": return self._experiment()
        if act == "breed": return self._breed()
        if act == "beetle": return self._beetle()
        if act == "communicate": return self._communicate(rocky)
        self.energy = min(100, self.energy + ENERGY_REST_GAIN)
        return f"Grace rested. E={self.energy}"

    def _go_adrian(self, grid):
        # Phase 1: reach tunnel (mandatory first step)
        if not self.tunnel_found:
            tx = grid.tunnel_x_start + 4
            ty = grid.tunnel_y
            return self._move_toward(tx, ty, grid)

        # Phase 2: follow waypoints (each gives a unique path through space)
        if self._wp_target < len(self._waypoints):
            wx, wy = self._waypoints[self._wp_target]
            dist_wp = abs(self.x - wx) + abs(self.y - wy)
            if dist_wp <= 2:
                self._wp_target += 1
                if self._wp_target < len(self._waypoints):
                    wx, wy = self._waypoints[self._wp_target]
            return self._move_toward(wx, wy, grid)

        # Phase 3: arrive at Adrian
        ax, ay = ADRIAN_POS
        best = None; bd = 999
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                nx2 = (ax + dx) % grid.W
                ny2 = (ay + dy) % grid.H
                cc = grid.cells[ny2][nx2]
                if cc.type not in (PLANET_ADRIAN,):
                    adj = any(
                        grid.cells[(ny2 + d[1]) % grid.H][(nx2 + d[0]) % grid.W].type == PLANET_ADRIAN
                        for d in CARD_DIRS
                    )
                    if adj:
                        d = abs(self.x - nx2) + abs(self.y - ny2)
                        if d < bd: bd = d; best = (nx2, ny2)
        if best:
            return self._move_toward(best[0], best[1], grid)
        return self._move_toward(ax, ay, grid)

    def _move_toward(self, tx, ty, grid):
        dx2 = tx - self.x; dy2 = ty - self.y
        if abs(dx2) > grid.W // 2: dx2 = -dx2
        if abs(dy2) > grid.H // 2: dy2 = -dy2
        if dx2 == 0 and dy2 == 0: return f"Grace at target ({tx},{ty})"

        sx = (1 if dx2 > 0 else -1) if dx2 != 0 else 0
        sy = (1 if dy2 > 0 else -1) if dy2 != 0 else 0

        if abs(dx2) >= abs(dy2):
            candidates = [(sx, 0), (sx, sy), (0, sy), (sx, -sy), (0, -sy), (-sx, 0)]
        else:
            candidates = [(0, sy), (sx, sy), (sx, 0), (-sx, sy), (0, -sy), (-sx, 0)]

        for cdx, cdy in candidates:
            nx2 = (self.x + cdx) % grid.W
            ny2 = (self.y + cdy) % grid.H
            if grid.passable(nx2, ny2):
                return self._do_move(nx2, ny2, grid)
        return self._move_random(grid)

    def _move_random(self, grid):
        dirs = list(ALL_DIRS)
        random.shuffle(dirs)
        for dx2, dy2 in dirs:
            nx2 = (self.x + dx2) % grid.W
            ny2 = (self.y + dy2) % grid.H
            if grid.passable(nx2, ny2):
                return self._do_move(nx2, ny2, grid)
        return "Grace: No passable cell"

    def _do_move(self, nx2, ny2, grid):
        if self.energy < ENERGY_MOVE:
            self.energy = min(100, self.energy + ENERGY_REST_GAIN)
            return f"Grace: Low E, resting. E={self.energy}"
        self.x, self.y = nx2, ny2
        self.energy -= ENERGY_MOVE
        dmg = grid.hazard_dmg(self.x, self.y)
        if dmg > 0:
            self.hp = max(0, self.hp - dmg)
            if self.hp == 0: self.alive = False
            return f"Grace->({self.x},{self.y}) HAZARD -{dmg}HP={self.hp}"
        return f"Grace->({self.x},{self.y}) E={self.energy}"

    def _escape(self, grid):
        dirs = list(ALL_DIRS); random.shuffle(dirs)
        best_pos = None; bv = 9999
        for dx2, dy2 in dirs:
            nx2 = (self.x + dx2) % grid.W
            ny2 = (self.y + dy2) % grid.H
            if grid.passable(nx2, ny2):
                d = grid.hazard_dmg(nx2, ny2)
                if d < bv: bv = d; best_pos = (nx2, ny2)
        if best_pos:
            return self._do_move(best_pos[0], best_pos[1], grid)
        return "Grace: TRAPPED!"

    def _collect(self, grid):
        if self.energy < ENERGY_EVA:
            self.energy = min(100, self.energy + ENERGY_REST_GAIN)
            return f"Grace: Resting before EVA. E={self.energy}"
        if grid.collect_at(self.x, self.y):
            self.energy -= ENERGY_EVA
            s = TauSample(); self.samples.append(s)
            self.knowledge += KNOWLEDGE_SAMPLE_COLLECTED
            self._update_q("collect", 0.5)
            return f"Grace: Taumoeba COLLECTED! Samples={len(self.samples)} K={self.knowledge}"
        near = grid.find_sample_near(self.x, self.y, 8)
        if near: return self._move_toward(near[0], near[1], grid)
        return self._go_adrian(grid)

    def _experiment(self):
        if not self.samples: return "Grace: No samples."
        if self.energy < ENERGY_EXPERIMENT:
            self.energy = min(100, self.energy + ENERGY_REST_GAIN)
            return f"Grace: Resting before experiment. E={self.energy}"
        self.energy -= ENERGY_EXPERIMENT
        self.exp_total += 1
        s = self.samples[-1]; s.n_exp += 1
        thresh = min(0.65, 0.25 + self.knowledge / 300)
        r = random.random()
        if r < thresh:
            d = random.uniform(0.10, 0.22)
            s.compat = min(1.0, s.compat + d)
            self.knowledge += KNOWLEDGE_EXPERIMENT_SUCCESS
            self.exp_ok += 1; res = "SUCCESS"
            self._update_q("experiment", 1.0)
        elif r < thresh + 0.25:
            d = random.uniform(0.03, 0.08)
            s.compat = min(1.0, s.compat + d)
            self.knowledge += KNOWLEDGE_EXPERIMENT_PARTIAL
            res = "PARTIAL"; self._update_q("experiment", 0.3)
        else:
            self.knowledge += KNOWLEDGE_EXPERIMENT_FAIL
            res = "FAIL"; self._update_q("experiment", -0.2)
        return f"Grace: Exp#{s.n_exp} {res} compat={s.compat:.2f} K={self.knowledge}"

    def _breed(self):
        if self.knowledge < TAUMOEBA_BREED_THRESHOLD:
            return f"Grace: Need {TAUMOEBA_BREED_THRESHOLD}K (have {self.knowledge})"
        if not self.samples: return "Grace: No samples."
        if self.energy < ENERGY_EXPERIMENT * 2:
            self.energy = min(100, self.energy + ENERGY_REST_GAIN)
            return f"Grace: Resting before breed. E={self.energy}"
        self.energy -= ENERGY_EXPERIMENT * 2
        best = max(self.samples, key=lambda s2: s2.compat)
        best.gen += 1; best.compat = min(1.0, best.compat + 0.14)
        self.knowledge += KNOWLEDGE_EXPERIMENT_PARTIAL
        if best.compat >= 0.8:
            self.best = best; self.mscore += 30
            self._update_q("breed", 2.0)
            return f"Grace: *** VIABLE TAUMOEBA BRED! *** compat={best.compat:.2f} MScore={self.mscore}"
        return f"Grace: Breed gen{best.gen} compat={best.compat:.2f} (need 0.8)"

    def _beetle(self):
        if not self.beetles_left: return "Grace: No beetles left."
        if not self.viable(): return "Grace: Need viable Taumoeba first."
        if self.energy < ENERGY_DEPLOY_BEETLE:
            self.energy = min(100, self.energy + ENERGY_REST_GAIN)
            return f"Grace: Resting before beetle. E={self.energy}"
        self.energy -= ENERGY_DEPLOY_BEETLE
        name = self.beetles_left.pop(0)
        probe = BeetleProbe(name, self.x, self.y)
        self.beetle_probes.append(probe)
        self.knowledge += KNOWLEDGE_BEETLE_DEPLOYED
        self.mscore += 25
        self._update_q("beetle", 2.0)
        return f"Grace: Beetle '{name}' LAUNCHED at ({self.x},{self.y})! K={self.knowledge} MScore={self.mscore}"

    def _communicate(self, rocky):
        if not self.comms_enabled:
            return "Grace: Comms blocked — tunnel not yet reached."
        gained = rocky.share_knowledge()
        self.knowledge += gained
        self._update_q("communicate", 0.8)
        return f"Grace<>Rocky (tunnel): +{gained}K total={self.knowledge} [{random.choice(list(ROCKY_PHRASES.values()))}]"

    def _update_q(self, action, reward):
        if action in self.q:
            self.q[action] += self.lr * (reward - self.q[action])


class Rocky:
    def __init__(self):
        self.x, self.y = ROCKY_START
        self.hp = 120
        self.energy = 110
        self.alive = True
        self.trust = 0
        self.fuel = 100
        self.maps_shared = False
        self.aph_shared = False
        self.talk_count = 0
        self.tunnel_found = False

    def share_knowledge(self):
        b = KNOWLEDGE_ROCKY_SHARE
        if self.trust >= 3: return int(b * 1.5)
        if self.trust >= 2: return b
        if self.trust >= 1: return int(b * 0.5)
        return 0

    def act(self, grid, grace):
        if grid.cells[self.y % grid.H][self.x % grid.W].type == TUNNEL:
            self.tunnel_found = True

        dist = abs(self.x - grace.x) + abs(self.y - grace.y)
        tunnel_comms = (self.tunnel_found or grace.tunnel_found) and dist <= 7

        if (grace.hp < 22 or grace.energy < 12) and self.fuel > 20:
            amt = min(25, self.fuel // 3)
            self.fuel -= amt; grace.energy = min(100, grace.energy + amt)
            return "share_energy", f"Rocky: Shared {amt}E -> Grace E={grace.energy}"

        if tunnel_comms and self.trust < 3:
            self.talk_count += 1
            if self.talk_count % 4 == 0: self.trust += 1
            chord = random.choice(list(ROCKY_PHRASES.values()))
            meaning = [k for k, v in ROCKY_PHRASES.items() if v == chord][0]
            return "communicate", f"Rocky [{chord}]={meaning} Trust={self.trust}/3"

        if not self.maps_shared and self.trust >= 1:
            grace.knowledge += 20; self.maps_shared = True
            return "share_maps", f"Rocky: Star maps shared! Grace K={grace.knowledge}"

        if not self.aph_shared and self.trust >= 2:
            grace.knowledge += 25; self.aph_shared = True
            return "share_aph", f"Rocky: Astrophage data shared! Grace K={grace.knowledge}"

        if grace.exp_total > 0 and dist <= 8 and self.trust >= 1:
            bonus = 3 * self.trust; grace.knowledge += bonus
            return "assist", f"Rocky: Experiment assist +{bonus}K={grace.knowledge}"

        return "wander", self._wander(grid)

    def _wander(self, grid):
        dirs = list(ALL_DIRS); random.shuffle(dirs)
        for dx2, dy2 in dirs:
            nx2 = (self.x + dx2) % grid.W
            ny2 = (self.y + dy2) % grid.H
            if grid.passable(nx2, ny2):
                if self.energy >= ENERGY_MOVE:
                    self.x, self.y = nx2, ny2
                    self.energy -= ENERGY_MOVE
                    dmg = grid.hazard_dmg(self.x, self.y)
                    if dmg > 0:
                        self.hp = max(0, self.hp - dmg)
                        if self.hp == 0: self.alive = False
                    return f"Rocky->({self.x},{self.y}) E={self.energy}"
                else:
                    self.energy = min(110, self.energy + ENERGY_REST_GAIN)
                    return f"Rocky resting. E={self.energy}"
        return "Rocky: blocked"


class Sim:
    def __init__(self, run_id, seed):
        self.run_id = run_id
        self.seed = seed
        self.turn = 0
        self.done = False
        self.cause = "running"
        self.grid = Grid(seed)
        self.grace = Grace()
        self.rocky = Rocky()
        self.hist_k = []
        self.hist_hp = []
        self.hist_aph = []

    def tick(self):
        if self.done: return []
        self.turn += 1
        lines = []

        if self.grace.alive:
            act, msg = self.grace.act(self.grid, self.rocky)
            lines.append(f"[T{self.turn:03d}] Grace [{act}]: {msg}")
            if not self.grace.alive:
                self.done = True; self.cause = "grace_died"
                lines.append(f"[T{self.turn:03d}] MISSION ABORT: Grace died.")
                self._rec(); return lines
            if self._complete():
                self.done = True; self.cause = "mission_complete"
                lines.append(f"[T{self.turn:03d}] *** MISSION COMPLETE — EARTH SAVED! ***")
                self._rec(); return lines

        if self.rocky.alive:
            act, msg = self.rocky.act(self.grid, self.grace)
            lines.append(f"[T{self.turn:03d}] Rocky [{act}]: {msg}")

        self.grid.step(self.grace.taum_dep)
        self._rec()

        if self.turn >= SIM_MAX_TURNS:
            self.done = True; self.cause = "timeout"
            lines.append(f"[T{self.turn:03d}] Simulation ended at {SIM_MAX_TURNS} turns.")

        return lines

    def _rec(self):
        self.hist_k.append(self.grace.knowledge)
        self.hist_hp.append(self.grace.hp)
        self.hist_aph.append(self.grid.count_aph())

    def _complete(self):
        return (len(self.grace.beetle_probes) >= 2
                and self.grace.viable()
                and self.grace.knowledge >= 50)

    def summary(self):
        g = self.grace; rk = self.rocky
        return {
            "run": self.run_id, "turns": self.turn, "cause": self.cause,
            "knowledge": g.knowledge, "mscore": g.mscore,
            "beetles": len(g.beetle_probes), "viable": g.viable(),
            "exp_total": g.exp_total, "exp_ok": g.exp_ok,
            "flashbacks": len(g.flashbacks), "trust": rk.trust,
            "aph_final": self.grid.count_aph(), "grace_hp": g.hp,
            "grace_alive": g.alive, "tunnel_found": g.tunnel_found,
            "comms_enabled": g.comms_enabled,
            "hist_k": self.hist_k, "hist_hp": self.hist_hp, "hist_aph": self.hist_aph,
        }


def show_graphs(results):
    try:
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.patches import Patch
    except ImportError:
        print("pip install matplotlib numpy")
        return

    n = len(results)
    complete = sum(1 for r in results if r["cause"] == "mission_complete")
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.patch.set_facecolor("#0d1117")
    fig.suptitle(
        f"Project Hail Mary — {n}-Run Analysis  |  "
        f"Mission Complete: {complete}/{n} ({complete/n*100:.0f}%)  |  "
        f"Earth {'SAVED' if complete == n else 'at risk'}",
        color="#58a6ff", fontsize=13, fontweight="bold"
    )
    for ax in axes.flat:
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e", labelsize=8)
        for sp in ax.spines.values(): sp.set_color("#30363d")
        ax.xaxis.label.set_color("#c9d1d9")
        ax.yaxis.label.set_color("#c9d1d9")
        ax.title.set_color("#58a6ff")

    ml = max((len(r["hist_k"]) for r in results), default=1)

    def pad(lst):
        return lst + [lst[-1]] * (ml - len(lst)) if lst else [0] * ml

    ax = axes[0, 0]
    for r in results:
        c = "#00ff88" if r["cause"] == "mission_complete" else "#555"
        ax.plot(r["hist_k"], alpha=0.35, lw=1, color=c)
    ax.plot(np.mean([pad(r["hist_k"]) for r in results], axis=0), color="#58a6ff", lw=2.5, label="Mean")
    ax.axhline(50, color="#ffd700", lw=1, ls="--", label="Mission threshold")
    ax.set_title("Knowledge Score Progression"); ax.set_xlabel("Turn"); ax.set_ylabel("Knowledge")
    ax.legend(facecolor="#161b22", labelcolor="#c9d1d9", fontsize=7)

    ax = axes[0, 1]
    for r in results:
        c = "#00ff88" if r["grace_alive"] else "#f85149"
        ax.plot(r["hist_hp"], alpha=0.35, lw=1, color=c)
    ax.plot(np.mean([pad(r["hist_hp"]) for r in results], axis=0), color="#ff6b35", lw=2.5, label="Mean HP")
    ax.set_title("Grace HP Over Time"); ax.set_xlabel("Turn"); ax.set_ylabel("HP")
    ax.legend(facecolor="#161b22", labelcolor="#c9d1d9", fontsize=7)

    ax = axes[0, 2]
    for r in results:
        ax.plot(r["hist_aph"], alpha=0.3, lw=1, color="#8B0000")
    ax.plot(np.mean([pad(r["hist_aph"]) for r in results], axis=0), color="#ff4444", lw=2.5, label="Mean")
    ax.set_title("Astrophage Spread"); ax.set_xlabel("Turn"); ax.set_ylabel("Cells")
    ax.legend(facecolor="#161b22", labelcolor="#c9d1d9", fontsize=7)

    ax = axes[1, 0]
    ends = {}
    for r in results: ends[r["cause"]] = ends.get(r["cause"], 0) + 1
    lbls = list(ends.keys()); szs = [ends[k] for k in lbls]
    pie_cols = ["#00ff88", "#f85149", "#8b949e", "#ffd700"][:len(lbls)]
    ax.pie(szs, labels=lbls, colors=pie_cols, autopct="%1.0f%%", textprops={"color": "#c9d1d9", "fontsize": 8})
    ax.set_title("Simulation Outcomes")

    ax = axes[1, 1]
    for r in results:
        rate = r["exp_ok"] / max(1, r["exp_total"]) * 100
        c = "#00ff88" if r["viable"] else "#8b949e"
        ax.scatter(r["exp_total"], rate, color=c, alpha=0.8, s=60, edgecolors="#30363d")
    ax.set_title("Experiments vs Success Rate"); ax.set_xlabel("Total Experiments"); ax.set_ylabel("Success %")
    ax.legend(handles=[Patch(color="#00ff88", label="Taumoeba bred"), Patch(color="#8b949e", label="Not bred")],
              facecolor="#161b22", labelcolor="#c9d1d9", fontsize=7)

    ax = axes[1, 2]
    runs = [r["run"] for r in results]; knows = [r["knowledge"] for r in results]
    bar_c = ["#00ff88" if r["cause"] == "mission_complete" else "#f85149" for r in results]
    ax.bar(runs, knows, color=bar_c, edgecolor="#30363d", linewidth=0.5)
    avg = sum(knows) / len(knows)
    ax.axhline(avg, color="#58a6ff", lw=1.5, ls="--", label=f"Mean={avg:.0f}")
    ax.set_title("Final Knowledge per Run"); ax.set_xlabel("Run #"); ax.set_ylabel("Knowledge Score")
    ax.legend(facecolor="#161b22", labelcolor="#c9d1d9", fontsize=7)

    plt.tight_layout()
    plt.show()


CELL_PX = 16
CW = GRID_WIDTH * CELL_PX
CH = GRID_HEIGHT * CELL_PX
BG = "#0d1117"; PANEL = "#161b22"; FG = "#c9d1d9"; ACC = "#58a6ff"

TYPE_COL = {
    EMPTY: "#0d1117",
    ASTROPHAGE_CLOUD: "#8B0000",
    PETROVA_LINE: "#6a0dad",
    PLANET_ADRIAN: "#1a5c3a",
    HAIL_MARY: "#1a6bb5",
    BLIP_A: "#b5621a",
    BEETLE_PROBE: "#d4a017",
    RADIATION_ZONE: "#2d5016",
    DEBRIS_FIELD: "#3d4142",
    TUNNEL: "#1b6ca8",
}


class App:
    MAX_AUTO_RUNS = 20

    def __init__(self):
        self.sim = None
        self.run_num = 0
        self.all_results = []
        self.auto_mode = False
        self._running = False
        self._paused = False
        self._build_ui()

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("Project Hail Mary — AI Simulation")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        tk.Label(self.root, text="⚡  PROJECT HAIL MARY — MULTI-AGENT AI SIMULATION  ⚡",
                 bg=BG, fg=ACC, font=("Courier New", 12, "bold"), pady=4).pack(fill=tk.X)

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        left = tk.Frame(main, bg=BG); left.pack(side=tk.LEFT)
        self.canvas = tk.Canvas(left, width=CW, height=CH, bg=BG,
                                highlightthickness=1, highlightbackground=ACC)
        self.canvas.pack()
        self._build_controls(left)
        self._build_legend(left)

        right = tk.Frame(main, bg=PANEL, width=280, padx=8, pady=6)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(6, 0))
        right.pack_propagate(False)
        self._build_stats(right)

    def _build_controls(self, parent):
        bar = tk.Frame(parent, bg=BG, pady=3); bar.pack(fill=tk.X)
        bs = dict(bg="#21262d", fg=FG, activebackground="#30363d", activeforeground="#fff",
                  relief=tk.FLAT, padx=7, pady=3, font=("Courier New", 9), cursor="hand2")
        tk.Button(bar, text="▶ Step",     command=self._step,  **bs).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="⏩ Run",     command=self._start, **bs).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="⏸ Pause",   command=self._pause, **bs).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="↺ New Sim",  command=self._new,   **bs).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="📊 20 Runs", command=self._batch, **bs).pack(side=tk.LEFT, padx=2)
        tk.Label(bar, text=" Speed:", bg=BG, fg=FG, font=("Courier New", 8)).pack(side=tk.LEFT)
        self.spd = tk.DoubleVar(value=0.08)
        tk.Scale(bar, from_=0.01, to=0.5, resolution=0.01, orient=tk.HORIZONTAL,
                 variable=self.spd, length=70, bg=BG, fg=FG,
                 troughcolor="#21262d", highlightthickness=0, showvalue=False).pack(side=tk.LEFT)

    def _build_legend(self, parent):
        leg = tk.Frame(parent, bg=BG, pady=1); leg.pack(fill=tk.X)
        items = [(HAIL_MARY,"Hail Mary"),(BLIP_A,"Blip-A"),(PLANET_ADRIAN,"Adrian"),
                 (PETROVA_LINE,"Petrova"),(ASTROPHAGE_CLOUD,"Astrophage"),
                 (RADIATION_ZONE,"Radiation"),(DEBRIS_FIELD,"Debris"),(TUNNEL,"Tunnel")]
        for ct, lbl in items:
            f = tk.Frame(leg, bg=BG); f.pack(side=tk.LEFT, padx=2)
            tk.Canvas(f, width=10, height=10, bg=TYPE_COL[ct], highlightthickness=0).pack(side=tk.LEFT)
            tk.Label(f, text=lbl, bg=BG, fg=FG, font=("Courier New", 7)).pack(side=tk.LEFT)
        for col, nm in [("#00ff88","Grace"),("#ff6b35","Rocky"),("#f1c40f","Beetle")]:
            f = tk.Frame(leg, bg=BG); f.pack(side=tk.LEFT, padx=2)
            tk.Canvas(f, width=10, height=10, bg=col, highlightthickness=0).pack(side=tk.LEFT)
            tk.Label(f, text=nm, bg=BG, fg=FG, font=("Courier New", 7)).pack(side=tk.LEFT)

    def _build_stats(self, parent):
        tk.Label(parent, text="MISSION STATUS", bg=PANEL, fg=ACC,
                 font=("Courier New", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.sv = {}
        fields = [
            ("run","Simulation"), ("turn","Turn"), ("hp","Grace HP"),
            ("energy","Grace Energy"), ("fuzzy","Fuzzy Logic"),
            ("k","Knowledge"), ("ms","Mission Score"), ("beetles","Beetles"),
            ("viable","Taumoeba Viable"), ("exp","Experiments"),
            ("tunnel","Tunnel Found"), ("comms","Comms"), ("trust","Rocky Trust"),
            ("aph","Astrophage Cells"), ("fb","Flashbacks"), ("status","Status"),
        ]
        for key, lbl in fields:
            row = tk.Frame(parent, bg=PANEL); row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{lbl}:", bg=PANEL, fg="#8b949e",
                     font=("Courier New", 8), width=16, anchor="w").pack(side=tk.LEFT)
            v = tk.StringVar(value="—"); self.sv[key] = v
            tk.Label(row, textvariable=v, bg=PANEL, fg=FG,
                     font=("Courier New", 8, "bold"), anchor="w").pack(side=tk.LEFT)
        tk.Label(parent, text="\n(Full log in terminal)", bg=PANEL, fg="#444",
                 font=("Courier New", 7)).pack(anchor="w")

    def _make_sim(self, run_id):
        self.run_num = run_id
        seed = random.randint(0, 99999)
        self.sim = Sim(run_id, seed)
        self._draw(); self._refresh()
        print(f"\n{'='*55}\n  Run #{run_id}  seed={seed}\n{'='*55}")

    def _new(self):
        self._running = False; time.sleep(0.05)
        self.auto_mode = False; self.all_results = []
        self._make_sim(1)

    def _step(self):
        if not self.sim or self.sim.done:
            self._make_sim((self.run_num or 0) + 1)
        lines = self.sim.tick()
        for l in lines: print(l)
        self._draw(); self._refresh()

    def _start(self):
        if not self.sim: self._make_sim(1)
        if not self._running:
            self._running = True; self._paused = False
            threading.Thread(target=self._loop, daemon=True).start()

    def _pause(self):
        self._paused = not self._paused

    def _batch(self):
        self._running = False; time.sleep(0.1)
        self.auto_mode = True; self.all_results = []
        self._make_sim(1)
        print("\n=== 20-run batch starting ===")
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._running:
            if self._paused: time.sleep(0.1); continue

            if not self.sim or self.sim.done:
                if self.sim:
                    r = self.sim.summary()
                    self.all_results.append(r)
                    mark = "✓" if r["cause"] == "mission_complete" else "✗"
                    print(f"Run {r['run']:2d} {mark}  T={r['turns']:3d}  K={r['knowledge']:3d}  "
                          f"HP={r['grace_hp']:3d}  B={r['beetles']}  "
                          f"tunnel={'Y' if r['tunnel_found'] else 'N'}  "
                          f"trust={r['trust']}  {r['cause']}")

                if self.auto_mode and len(self.all_results) < self.MAX_AUTO_RUNS:
                    nid = len(self.all_results) + 1
                    self.root.after(0, self._make_sim, nid)
                    time.sleep(0.3); continue
                elif self.auto_mode and len(self.all_results) >= self.MAX_AUTO_RUNS:
                    self._running = False
                    self.root.after(0, self._finish_batch); return
                else:
                    self._running = False; return

            lines = self.sim.tick()
            for l in lines: print(l)
            self.root.after(0, self._draw)
            self.root.after(0, self._refresh)
            time.sleep(self.spd.get())

    def _finish_batch(self):
        rs = self.all_results; n = len(rs)
        complete = sum(1 for r in rs if r["cause"] == "mission_complete")
        lines = [
            "", "=" * 55, f"  BATCH COMPLETE — {n} SIMULATIONS", "=" * 55,
            f"  Earth Saved?         {'YES' if complete == n else f'PARTIAL {complete}/{n}'}",
            f"  Mission Complete:    {complete}/{n} ({complete/n*100:.0f}%)",
            f"  Avg Turns:           {sum(r['turns'] for r in rs)/n:.1f} / {SIM_MAX_TURNS}",
            f"  Avg Knowledge:       {sum(r['knowledge'] for r in rs)/n:.1f}",
            f"  Avg Grace HP (end):  {sum(r['grace_hp'] for r in rs)/n:.1f}",
            f"  Taumoeba Bred:       {sum(1 for r in rs if r['viable'])/n*100:.0f}%",
            f"  Avg Rocky Trust:     {sum(r['trust'] for r in rs)/n:.1f}/3",
            f"  Tunnel Found:        {sum(1 for r in rs if r['tunnel_found'])/n*100:.0f}%",
            f"  Comms Enabled:       {sum(1 for r in rs if r['comms_enabled'])/n*100:.0f}%",
            "=" * 55, "",
        ]
        for l in lines: print(l)

        win = tk.Toplevel(self.root)
        win.title("Batch Summary"); win.configure(bg=PANEL)
        tk.Label(win, text="\n".join(lines[1:-1]), bg=PANEL, fg=FG,
                 font=("Courier New", 9), justify=tk.LEFT, padx=20, pady=10).pack()
        tk.Button(win, text="Close", command=win.destroy,
                  bg="#21262d", fg=FG, relief=tk.FLAT, padx=12).pack(pady=8)

        threading.Thread(target=show_graphs, args=(rs,), daemon=True).start()

    def _draw(self):
        if not self.sim: return
        self.canvas.delete("all")
        g = self.sim.grid; gr = self.sim.grace; rk = self.sim.rocky

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cc = g.cells[y][x]
                if cc.type == PETROVA_LINE:
                    v = int(80 + cc.aph_int * 120)
                    col = f"#{v:02x}00{min(255,v+60):02x}"
                elif cc.type == ASTROPHAGE_CLOUD:
                    rv = int(60 + cc.aph_int * 140)
                    col = f"#{rv:02x}0000"
                else:
                    col = TYPE_COL.get(cc.type, BG)
                x1 = x * CELL_PX; y1 = y * CELL_PX
                self.canvas.create_rectangle(x1, y1, x1 + CELL_PX, y1 + CELL_PX,
                                             fill=col, outline="#111", width=0.3)
                if cc.type == PETROVA_LINE:
                    cx2 = x1 + CELL_PX // 2; cy2 = y1 + CELL_PX // 2
                    r2 = int(3 + cc.aph_int * 3)
                    self.canvas.create_oval(cx2-r2, cy2-r2, cx2+r2, cy2+r2,
                                           fill="#cc44ff", outline="")
                if cc.has_taum:
                    cx2 = x1 + CELL_PX // 2; cy2 = y1 + CELL_PX // 2
                    self.canvas.create_oval(cx2 - 2, cy2 - 2, cx2 + 2, cy2 + 2,
                                           fill="#00ff44", outline="")

        self._dot(gr.x, gr.y, "#00ff88", "G")
        if rk.alive: self._dot(rk.x, rk.y, "#ff6b35", "R")

        for probe in gr.beetle_probes:
            self._dot(probe.x, probe.y, "#f1c40f", "B")

    def _dot(self, x, y, color, letter):
        x1 = x * CELL_PX + 1; y1 = y * CELL_PX + 1
        self.canvas.create_oval(x1, y1, x1 + CELL_PX - 2, y1 + CELL_PX - 2,
                                fill=color, outline="#fff", width=1.5)
        self.canvas.create_text(x1 + CELL_PX // 2 - 1, y1 + CELL_PX // 2 - 1,
                                text=letter, fill="#000", font=("Courier New", 7, "bold"))

    def _refresh(self):
        if not self.sim: return
        g = self.sim.grace; rk = self.sim.rocky
        rest_u, proc_u = g.fuzzy.evaluate(g.energy, g.hp)
        names = {0: "Strangers", 1: "Colleagues", 2: "Friends", 3: "Allies"}
        self.sv["run"].set(str(self.sim.run_id))
        self.sv["turn"].set(f"{self.sim.turn} / {SIM_MAX_TURNS}")
        self.sv["hp"].set(f"{g.hp}/100")
        self.sv["energy"].set(f"{g.energy}/100")
        self.sv["fuzzy"].set(f"rest={rest_u:.2f} proc={proc_u:.2f}")
        self.sv["k"].set(str(g.knowledge))
        self.sv["ms"].set(str(g.mscore))
        self.sv["beetles"].set(f"{len(g.beetle_probes)}/4")
        self.sv["viable"].set("YES ✓" if g.viable() else "No")
        self.sv["exp"].set(f"{g.exp_total} ({g.exp_ok} ok)")
        self.sv["tunnel"].set("YES ✓" if g.tunnel_found else "No")
        self.sv["comms"].set("YES ✓" if g.comms_enabled else "BLOCKED")
        self.sv["trust"].set(f"{names[rk.trust]} ({rk.trust}/3)")
        self.sv["aph"].set(str(self.sim.grid.count_aph()))
        self.sv["fb"].set(f"{len(g.flashbacks)}/{len(FLASHBACK_EVENTS)}")
        cause_map = {
            "running": "Running...", "mission_complete": "✓ EARTH SAVED!",
            "grace_died": "✗ Grace died", "timeout": f"Timeout ({SIM_MAX_TURNS}T)",
        }
        self.sv["status"].set(cause_map.get(self.sim.cause, self.sim.cause))

    def _quit(self):
        self._running = False
        self.root.destroy()

    def start(self):
        self._make_sim(1)
        self.root.mainloop()


if __name__ == "__main__":
    app = App()
    app.start()
