"""Dr. Ryland Grace — Human Agent with Q-learning adaptive AI"""
import random
from agents.base_agent import Agent
from config import *

class TaumoebaSample:
    def __init__(self):
        self.generation          = 0
        self.earth_compatibility = 0.0
        self.viability           = 1.0
        self.experiments_run     = 0
        self.log                 = []
    def is_viable(self):
        return self.earth_compatibility >= 0.8 and self.viability > 0.3

class BeetleProbe:
    def __init__(self, name, x, y, payload):
        self.name    = name;  self.x = x;  self.y = y;  self.payload = payload

class Grace(Agent):
    def __init__(self):
        gx, gy = GRACE_START
        super().__init__("Grace", gx, gy, health=100, energy=100)
        self.knowledge_score     = 0
        self.mission_score       = 0
        self.flashbacks_seen     = []
        self.astrophage_samples  = 0
        self.taumoeba_samples    = []
        self.best_taumoeba       = None
        self.taumoeba_deployed   = False
        self.available_beetles   = list(BEETLE_NAMES)
        self.deployed_beetles    = []
        self.experiments_total   = 0
        self.experiments_success = 0
        # Q-values (start equal, learn from rewards)
        self.q = {
            "move_to_adrian": 1.5,
            "collect_sample": 1.8,
            "experiment":     1.6,
            "breed":          1.4,
            "deploy_beetle":  1.2,
            "deploy_taumoeba":1.0,
            "communicate":    1.1,
            "rest":           0.8,
        }
        self.lr = 0.1

    # ── MAIN DECISION ──────────────────────────────────────────────────
    def decide_action(self, env, rocky):
        self.turn_count += 1
        fb = self._check_flashback()
        if fb:
            return "flashback", fb
        if self.energy < 15 or self.health < 20:
            _, msg = self.rest()
            return "rest", msg
        action = self._pick_action(env, rocky)
        msg    = self._execute(action, env, rocky)
        return action, msg

    def _pick_action(self, env, rocky):
        dist_adrian  = self.distance_to(*ADRIAN_POS)
        has_samples  = len(self.taumoeba_samples) > 0
        can_breed    = self.knowledge_score >= TAUMOEBA_BREED_THRESHOLD and has_samples
        has_viable   = self.best_taumoeba and self.best_taumoeba.is_viable()
        beetles_left = len(self.available_beetles) > 0
        rocky_close  = self.distance_to(rocky.x, rocky.y) <= 4

        scores = dict(self.q)

        if dist_adrian > 3:
            scores["move_to_adrian"] += 2.0
        if dist_adrian <= 6:
            scores["collect_sample"] += 2.5
        if has_samples:
            scores["experiment"] += 2.5
        if can_breed:
            scores["breed"] += 3.0
        if has_viable and beetles_left:
            scores["deploy_beetle"] += 4.0
        if has_viable and env.count_astrophage_cells() > 25:
            scores["deploy_taumoeba"] += 2.5
        if rocky_close and rocky.trust_level >= 2:
            scores["communicate"] += 1.0
        # Don't experiment/breed without samples
        if not has_samples:
            scores["experiment"] -= 3.0
            scores["breed"] -= 3.0

        for k in scores:
            scores[k] += random.uniform(0, 0.15)
        return max(scores, key=scores.get)

    def _execute(self, action, env, rocky):
        if action == "move_to_adrian":  return self._move_to_adrian(env)
        if action == "collect_sample":  return self._collect(env)
        if action == "experiment":      return self._experiment()
        if action == "breed":           return self._breed()
        if action == "deploy_beetle":   return self._deploy_beetle()
        if action == "deploy_taumoeba": return self._deploy_taumoeba(env)
        if action == "communicate":     return self._communicate(rocky)
        _, msg = self.rest()
        return msg

    # ── ACTIONS ────────────────────────────────────────────────────────
    def _move_to_adrian(self, env):
        ax, ay = ADRIAN_POS
        # Find nearest Adrian-adjacent passable cell
        target = self._find_adjacent_to_adrian(env)
        if target is None:
            # Already adjacent or no path — just move toward center
            ok, msg = self.move_toward(ax, ay, env)
            return msg
        tx, ty = target
        if self.x == tx and self.y == ty:
            return self._collect(env)
        ok, msg = self.move_toward(tx, ty, env)
        self._update_q("move_to_adrian", 0.1 if ok else -0.1)
        return msg

    def _find_adjacent_to_adrian(self, env):
        """Find nearest passable cell adjacent to Adrian planet cells."""
        ax, ay = ADRIAN_POS
        # Check cells just outside Adrian radius (distance ~4 from center)
        best = None; best_dist = 999
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                nx, ny = ax+dx, ay+dy
                if 0 <= nx < env.width and 0 <= ny < env.height:
                    c = env.grid[ny][nx]
                    # Cell must be passable (not Adrian itself) but next to Adrian
                    if c.cell_type != PLANET_ADRIAN and c.cell_type != ASTROPHAGE_CLOUD:
                        # Check if adjacent to an Adrian cell with sample
                        for ddx, ddy in [(0,1),(0,-1),(1,0),(-1,0)]:
                            nnx, nny = nx+ddx, ny+ddy
                            if 0<=nnx<env.width and 0<=nny<env.height:
                                nc = env.grid[nny][nnx]
                                if nc.cell_type == PLANET_ADRIAN and nc.has_sample:
                                    d = self.distance_to(nx, ny)
                                    if d < best_dist:
                                        best_dist = d; best = (nx, ny)
        return best

    def _collect(self, env):
        """
        Collect from adjacent Adrian cell, OR if sample on current cell.
        Grace doesn't need to walk INTO Adrian — she reaches in from outside.
        """
        # First check current cell
        cc = env.get_cell(self.x, self.y)
        if cc.has_sample and cc.cell_type != PLANET_ADRIAN:
            return self._do_collect_cell(cc, env)

        # Check all 4 adjacent cells (including Adrian cells)
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx = (self.x+dx) % env.width
            ny = (self.y+dy) % env.height
            nc = env.grid[ny][nx]
            if nc.has_sample:
                if self.energy < ENERGY_EVA:
                    _, msg = self.rest()
                    return f"Low energy, resting. {msg}"
                self.energy -= ENERGY_EVA
                return self._do_collect_from(nc, nx, ny)

        # No adjacent sample — move closer
        target = self._find_adjacent_to_adrian(env)
        if target:
            tx, ty = target
            ok, msg = self.move_toward(tx, ty, env)
            return f"Moving to Adrian adj. {msg}"
        ax, ay = ADRIAN_POS
        ok, msg = self.move_toward(ax, ay, env)
        return f"Moving toward Adrian. {msg}"

    def _do_collect_cell(self, cell, env):
        if self.energy < ENERGY_EVA:
            _, msg = self.rest()
            return f"Resting before EVA. {msg}"
        self.energy -= ENERGY_EVA
        return self._do_collect_from(cell, self.x, self.y)

    def _do_collect_from(self, cell, nx, ny):
        if cell.taumoeba_present:
            s = TaumoebaSample()
            self.taumoeba_samples.append(s)
            self.knowledge_score += KNOWLEDGE_SAMPLE_COLLECTED
            cell.has_sample = False
            self._update_q("collect_sample", 0.5)
            return f"Grace: Taumoeba sample collected from ({nx},{ny})! K={self.knowledge_score}"
        elif cell.cell_type == ASTROPHAGE_CLOUD:
            self.astrophage_samples += 1
            self.knowledge_score    += KNOWLEDGE_SAMPLE_COLLECTED
            self._update_q("collect_sample", 0.3)
            return f"Grace: Astrophage sample from ({nx},{ny}). K={self.knowledge_score}"
        cell.has_sample = False
        self.knowledge_score += 2
        return f"Grace: Sample collected from ({nx},{ny}). K={self.knowledge_score}"

    def _experiment(self):
        if not self.taumoeba_samples:
            return "Grace: No samples."
        if self.energy < ENERGY_EXPERIMENT:
            _, msg = self.rest()
            return f"Resting before exp. {msg}"
        self.energy -= ENERGY_EXPERIMENT
        self.experiments_total += 1
        sample = self.taumoeba_samples[-1]
        sample.experiments_run += 1
        thresh = min(0.65, 0.25 + self.knowledge_score / 250)
        roll   = random.random()
        if roll < thresh:
            delta = random.uniform(0.10, 0.20)
            sample.earth_compatibility = min(1.0, sample.earth_compatibility + delta)
            self.knowledge_score += KNOWLEDGE_EXPERIMENT_SUCCESS
            self.experiments_success += 1
            result = "SUCCESS"
            self._update_q("experiment", 1.0)
        elif roll < thresh + 0.25:
            delta = random.uniform(0.03, 0.08)
            sample.earth_compatibility = min(1.0, sample.earth_compatibility + delta)
            self.knowledge_score += KNOWLEDGE_EXPERIMENT_PARTIAL
            result = "PARTIAL"
            self._update_q("experiment", 0.3)
        else:
            sample.viability = max(0.1, sample.viability - 0.08)
            self.knowledge_score += KNOWLEDGE_EXPERIMENT_FAIL
            result = "FAIL"
            self._update_q("experiment", -0.2)
        sample.log.append({"result": result, "compat": sample.earth_compatibility})
        return (f"Grace: Exp#{sample.experiments_run} {result} "
                f"compat={sample.earth_compatibility:.2f} K={self.knowledge_score}")

    def _breed(self):
        if self.knowledge_score < TAUMOEBA_BREED_THRESHOLD:
            return f"Grace: Need {TAUMOEBA_BREED_THRESHOLD} K to breed (have {self.knowledge_score})."
        if not self.taumoeba_samples:
            return "Grace: No samples to breed."
        if self.energy < ENERGY_EXPERIMENT * 2:
            _, msg = self.rest()
            return f"Resting before breed. {msg}"
        self.energy -= ENERGY_EXPERIMENT * 2
        best = max(self.taumoeba_samples, key=lambda s: s.earth_compatibility)
        if best.is_viable():
            self.best_taumoeba  = best
            self.mission_score += 30
            self._update_q("breed", 2.0)
            return (f"Grace: *** VIABLE TAUMOEBA BRED! *** "
                    f"compat={best.earth_compatibility:.2f} MissionScore={self.mission_score}")
        best.generation += 1
        best.earth_compatibility = min(1.0, best.earth_compatibility + 0.12)
        self.knowledge_score    += KNOWLEDGE_EXPERIMENT_PARTIAL
        self._update_q("breed", 0.5)
        return (f"Grace: Breeding gen{best.generation} "
                f"compat={best.earth_compatibility:.2f} (need 0.8)")

    def _deploy_beetle(self):
        if not self.available_beetles:
            return "Grace: All beetles deployed."
        if not (self.best_taumoeba and self.best_taumoeba.is_viable()):
            return "Grace: Need viable Taumoeba first."
        if self.energy < ENERGY_DEPLOY_BEETLE:
            _, msg = self.rest()
            return f"Resting before beetle. {msg}"
        self.energy -= ENERGY_DEPLOY_BEETLE
        name = self.available_beetles.pop(0)
        probe = BeetleProbe(name, self.x, self.y, self.knowledge_score)
        self.deployed_beetles.append(probe)
        self.knowledge_score += KNOWLEDGE_BEETLE_DEPLOYED
        self.mission_score   += 25
        self._update_q("deploy_beetle", 2.0)
        return (f"Grace: Beetle '{name}' LAUNCHED! payload={probe.payload} "
                f"MissionScore={self.mission_score}")

    def _deploy_taumoeba(self, env):
        if not (self.best_taumoeba and self.best_taumoeba.is_viable()):
            return "Grace: No viable Taumoeba."
        cleared = env.apply_taumoeba(self.x, self.y)
        self.taumoeba_deployed = True
        self.mission_score    += 20
        self._update_q("deploy_taumoeba", 1.5)
        return f"Grace: Taumoeba deployed! Cleared {cleared} cells."

    def _communicate(self, rocky):
        if not rocky.alive:
            return "Grace: Rocky unavailable."
        gained = rocky.share_knowledge()
        self.knowledge_score += gained
        return f"Grace<>Rocky: +{gained} K. Total={self.knowledge_score}"

    def _check_flashback(self):
        for thresh, text in FLASHBACK_EVENTS.items():
            if self.knowledge_score >= thresh and thresh not in self.flashbacks_seen:
                self.flashbacks_seen.append(thresh)
                self.knowledge_score += KNOWLEDGE_FLASHBACK
                return f"[FLASHBACK] {text}"
        return None

    def _update_q(self, action, reward):
        if action in self.q:
            self.q[action] += self.lr * (reward - self.q[action])

    def get_stats(self):
        return {
            **self.status(),
            "knowledge":     self.knowledge_score,
            "mission_score": self.mission_score,
            "samples":       len(self.taumoeba_samples),
            "viable":        self.best_taumoeba is not None and self.best_taumoeba.is_viable(),
            "beetles_out":   len(self.deployed_beetles),
            "exp_total":     self.experiments_total,
            "exp_ok":        self.experiments_success,
            "flashbacks":    len(self.flashbacks_seen),
            "deployed_tmb":  self.taumoeba_deployed,
        }
