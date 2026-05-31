"""Rocky — Eridian Alien Agent"""
import random
from agents.base_agent import Agent
from config import *

class Rocky(Agent):
    def __init__(self):
        rx, ry = ROCKY_START
        super().__init__("Rocky", rx, ry, health=120, energy=110)
        self.trust_level        = 0
        self.fuel_reserves      = 100
        self.star_maps_shared   = False
        self.aph_data_shared    = False
        self.vocab              = {}
        self.fluency            = 0.0
        self.interactions       = 0
        for meaning, chord in ROCKY_PHRASES.items():
            self.vocab[chord] = meaning

    def decide_action(self, env, grace):
        self.turn_count += 1
        state = {
            "grace_critical": grace.health < 25 or grace.energy < 15,
            "grace_close":    self.distance_to(grace.x, grace.y) <= 4,
            "trust_low":      self.trust_level < 2,
            "can_maps":       not self.star_maps_shared and self.trust_level >= 1,
            "can_aph":        not self.aph_data_shared and self.trust_level >= 2,
            "grace_has_exp":  grace.experiments_total > 0,
        }
        if state["grace_critical"] and self.fuel_reserves > 20:
            msg = self._share_energy(grace)
            return "share_energy", msg
        if state["grace_close"] and state["trust_low"]:
            msg = self._communicate(grace)
            return "communicate", msg
        if state["can_maps"]:
            msg = self._share_star_maps(grace)
            return "share_maps", msg
        if state["can_aph"]:
            msg = self._share_aph_data(grace)
            return "share_aph", msg
        if state["grace_has_exp"] and state["grace_close"] and self.trust_level >= 1:
            msg = self._assist(grace)
            return "assist", msg
        if not state["grace_close"]:
            ok, msg = self.move_toward(grace.x, grace.y, env)
            return "move", msg
        _, msg = self.rest()
        return "rest", msg

    def _communicate(self, grace):
        self.interactions += 1
        self.fluency = min(1.0, self.fluency + 0.06)
        chord = random.choice(list(ROCKY_PHRASES.values()))
        meaning = [k for k,v in ROCKY_PHRASES.items() if v==chord][0]
        if self.interactions % 4 == 0 and self.trust_level < 3:
            self.trust_level += 1
        trust_names = {0:"strangers",1:"colleagues",2:"friends",3:"allies"}
        return (f"Rocky [{chord}]={meaning}. Trust={trust_names[self.trust_level]} "
                f"Fluency={self.fluency:.0%}")

    def _share_energy(self, grace):
        amt = min(25, self.fuel_reserves // 3)
        self.fuel_reserves -= amt
        grace.energy = min(grace.max_energy, grace.energy + amt)
        return f"Rocky: Shared {amt} energy. Grace E={grace.energy}"

    def _share_star_maps(self, grace):
        grace.knowledge_score += 20
        self.star_maps_shared = True
        self.energy -= 3
        return f"Rocky: Shared star maps! Grace K={grace.knowledge_score}"

    def _share_aph_data(self, grace):
        grace.knowledge_score += 25
        self.aph_data_shared = True
        self.energy -= 3
        return f"Rocky: Shared Astrophage data! Grace K={grace.knowledge_score}"

    def _assist(self, grace):
        bonus = 3 * self.trust_level
        grace.knowledge_score += bonus
        return f"Rocky: Assisted experiment. Grace K +{bonus}={grace.knowledge_score}"

    def share_knowledge(self):
        base = KNOWLEDGE_ROCKY_SHARE
        if self.trust_level >= 3: return int(base * 1.5)
        if self.trust_level >= 2: return base
        if self.trust_level >= 1: return int(base * 0.5)
        return 0

    def get_stats(self):
        return {**self.status(), "trust": self.trust_level,
                "fuel": self.fuel_reserves, "fluency": f"{self.fluency:.0%}"}
