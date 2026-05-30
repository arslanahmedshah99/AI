"""
Project Hail Mary — Complete Simulation
All logic in one file for reliability.
"""
import random
import math

# ═══════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════
GRID_W  = 28
GRID_H  = 24
MAX_SIM_RUNS = 20
MAX_TURNS    = 150

# Cell types
EMPTY  = 0; ACLOUD = 1; ADRIAN = 2; HAILMARY = 3
BLIPA  = 4; TUNNEL = 5; HAZARD = 6

GRACE_START = (2, 12)
ROCKY_START = (5, 12)
ADRIAN_POS  = (20, 12)

BEETLE_NAMES = ["John", "Paul", "George", "Ringo"]

FLASHBACKS = {
    15: "You are Dr. Ryland Grace, a biologist...",
    30: "Eva Stratt recruited you for this mission...",
    50: "Astrophage threatens to dim the Sun...",
    75: "You volunteered knowing you'd never return...",
   100: "Earth has 30 years before climate collapse...",
   130: "You are humanity's last hope.",
}

# ═══════════════════════════════════════════════════════
#  ENVIRONMENT
# ═══════════════════════════════════════════════════════
class Cell:
    __slots__ = ("ctype","intensity","has_sample","taumoeba")
    def __init__(self, ctype=EMPTY):
        self.ctype      = ctype
        self.intensity  = 0.0
        self.has_sample = False
        self.taumoeba   = False

class Env:
    def __init__(self, seed):
        random.seed(seed)
        self.W = GRID_W; self.H = GRID_H
        self.g = [[Cell() for _ in range(self.W)] for _ in range(self.H)]
        self.turn = 0
        self._setup()

    def _setup(self):
        # Ships
        gx,gy = GRACE_START; self.g[gy][gx].ctype = HAILMARY
        rx,ry = ROCKY_START;  self.g[ry][rx].ctype = BLIPA
        for tx in range(gx+1,rx): self.g[gy][tx].ctype = TUNNEL
        # Adrian planet (radius 3)
        ax,ay = ADRIAN_POS
        for dy in range(-3,4):
            for dx in range(-3,4):
                nx,ny = ax+dx, ay+dy
                if 0<=nx<self.W and 0<=ny<self.H and math.sqrt(dx*dx+dy*dy)<=3:
                    c = self.g[ny][nx]
                    c.ctype=ADRIAN; c.has_sample=True; c.taumoeba=True; c.intensity=0.4
        # Taumoeba halo around Adrian
        for dy in range(-5,6):
            for dx in range(-5,6):
                nx,ny = ax+dx, ay+dy
                if 0<=nx<self.W and 0<=ny<self.H:
                    c=self.g[ny][nx]
                    if c.ctype==EMPTY and random.random()<0.35:
                        c.has_sample=True; c.taumoeba=True
        # Small Astrophage clusters (NOT covering whole map)
        for _ in range(5):
            cx=random.randint(0,self.W-1); cy=random.randint(0,self.H-1)
            c=self.g[cy][cx]
            if c.ctype==EMPTY:
                c.ctype=ACLOUD; c.intensity=random.uniform(0.3,0.7)
                # Small cluster
                for ddx,ddy in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nx2,ny2=(cx+ddx)%self.W,(cy+ddy)%self.H
                    nc=self.g[ny2][nx2]
                    if nc.ctype==EMPTY and random.random()<0.4:
                        nc.ctype=ACLOUD; nc.intensity=random.uniform(0.2,0.5)
        # 2 hazards
        for _ in range(2):
            hx=random.randint(0,self.W-1); hy=random.randint(0,self.H-1)
            if self.g[hy][hx].ctype==EMPTY: self.g[hy][hx].ctype=HAZARD

    def step(self):
        self.turn += 1
        # Spread Astrophage slowly
        if self.turn % 8 == 0:
            new=[]
            for y in range(self.H):
                for x in range(self.W):
                    if self.g[y][x].ctype==ACLOUD and random.random()<0.12:
                        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                            nx2,ny2=(x+dx)%self.W,(y+dy)%self.H
                            if self.g[ny2][nx2].ctype==EMPTY:
                                new.append((nx2,ny2,self.g[y][x].intensity*0.4))
            for nx2,ny2,i in new:
                self.g[ny2][nx2].ctype=ACLOUD; self.g[ny2][nx2].intensity=i

    def cell(self,x,y): return self.g[y%self.H][x%self.W]
    def passable(self,x,y): return self.cell(x,y).ctype not in (ADRIAN,)
    def aph_count(self): return sum(1 for row in self.g for c in row if c.ctype==ACLOUD)
    def damage_at(self,x,y):
        ct=self.cell(x,y).ctype
        if ct==ACLOUD:  return int(4*self.cell(x,y).intensity)
        if ct==HAZARD:  return 6
        return 0

# ═══════════════════════════════════════════════════════
#  AGENTS
# ═══════════════════════════════════════════════════════
class TauSample:
    def __init__(self):
        self.compat=0.0; self.viability=1.0; self.gen=0; self.exps=0
    def viable(self): return self.compat>=0.8 and self.viability>0.3

class Grace:
    def __init__(self):
        self.x,self.y = GRACE_START
        self.hp=100; self.energy=100; self.alive=True
        self.knowledge=0; self.mscore=0
        self.samples=[]; self.best=None; self.tmb_deployed=False
        self.beetles_left=list(BEETLE_NAMES); self.beetles_out=[]
        self.exps=0; self.exps_ok=0; self.flashbacks=[]
        self.turn=0
        # Q-values
        self.q={"go_adrian":1.8,"collect":2.0,"experiment":1.6,
                "breed":1.5,"deploy_beetle":1.3,"deploy_tmb":1.0,
                "talk":1.1,"rest":0.7}

    def dist(self,tx,ty):
        dx=min(abs(self.x-tx),GRID_W-abs(self.x-tx))
        dy=min(abs(self.y-ty),GRID_H-abs(self.y-ty))
        return dx+dy

    def move_toward(self,tx,ty,env):
        if self.energy<1: return False,"no energy"
        dx=tx-self.x; dy=ty-self.y
        if abs(dx)>GRID_W//2: dx=-dx
        if abs(dy)>GRID_H//2: dy=-dy
        sx=0 if dx==0 else (1 if dx>0 else -1)
        sy=0 if dy==0 else (1 if dy>0 else -1)
        # try horizontal first then vertical
        for ddx,ddy in [(sx,0),(0,sy),(sx,sy)]:
            if ddx==0 and ddy==0: continue
            nx=(self.x+ddx)%GRID_W; ny=(self.y+ddy)%GRID_H
            if env.passable(nx,ny):
                self.x=nx; self.y=ny; self.energy-=1
                dmg=env.damage_at(self.x,self.y)
                if dmg: self.hp=max(0,self.hp-dmg)
                if self.hp==0: self.alive=False
                return True,f"Grace→({self.x},{self.y})"
        return False,"blocked"

    def decide(self, env, rocky):
        self.turn+=1
        # Flashback check
        for thresh,txt in FLASHBACKS.items():
            if self.knowledge>=thresh and thresh not in self.flashbacks:
                self.flashbacks.append(thresh)
                self.knowledge+=5
                return "flashback",f"[FLASHBACK] {txt}"
        # Critical rest
        if self.energy<12 or self.hp<15:
            self.energy=min(100,self.energy+22)
            if self.hp<15: self.hp=min(100,self.hp+5)
            return "rest",f"Grace resting. E={self.energy} HP={self.hp}"
        # Escape hazard
        if env.damage_at(self.x,self.y)>0:
            return "escape",self._escape(env)
        # Pick action
        act=self._pick(env,rocky)
        msg=self._do(act,env,rocky)
        return act,msg

    def _pick(self,env,rocky):
        d=self.dist(*ADRIAN_POS)
        has=len(self.samples)>0
        can_breed=self.knowledge>=40 and has
        viable=self.best and self.best.viable()
        q=dict(self.q)
        if d>4:   q["go_adrian"]+=2.0
        if d<=5:  q["collect"]+=2.5
        if has:   q["experiment"]+=2.5
        if can_breed: q["breed"]+=3.0
        if viable and self.beetles_left: q["deploy_beetle"]+=4.0
        if viable and env.aph_count()>20: q["deploy_tmb"]+=2.5
        if not has: q["experiment"]-=4; q["breed"]-=4
        if not viable: q["deploy_beetle"]-=4
        for k in q: q[k]+=random.uniform(0,0.1)
        return max(q,key=q.get)

    def _do(self,act,env,rocky):
        if act=="go_adrian":    return self._go_adrian(env)
        if act=="collect":      return self._collect(env)
        if act=="experiment":   return self._experiment()
        if act=="breed":        return self._breed()
        if act=="deploy_beetle":return self._deploy_beetle()
        if act=="deploy_tmb":   return self._deploy_tmb(env)
        if act=="talk":         return self._talk(rocky)
        # rest fallback
        self.energy=min(100,self.energy+22)
        return f"Grace resting. E={self.energy}"

    def _go_adrian(self,env):
        ax,ay=ADRIAN_POS
        # Find best adjacent cell to Adrian
        target=None; bd=999
        for dy in range(-4,5):
            for dx in range(-4,5):
                nx,ny=ax+dx,ay+dy
                if 0<=nx<GRID_W and 0<=ny<GRID_H:
                    c=env.g[ny][nx]
                    if c.ctype not in (ADRIAN,ACLOUD):
                        # adjacent to Adrian with sample?
                        adj=False
                        for adx,ady in [(0,1),(0,-1),(1,0),(-1,0)]:
                            anx,any=nx+adx,ny+ady
                            if 0<=anx<GRID_W and 0<=any<GRID_H:
                                ac=env.g[any][anx]
                                if ac.ctype==ADRIAN and ac.has_sample: adj=True
                        if not adj and c.taumoeba and c.has_sample: adj=True
                        if adj:
                            dd=self.dist(nx,ny)
                            if dd<bd: bd=dd; target=(nx,ny)
        if target:
            if self.x==target[0] and self.y==target[1]:
                return self._collect(env)
            ok,msg=self.move_toward(target[0],target[1],env)
            return msg
        ok,msg=self.move_toward(ax,ay,env)
        return msg

    def _collect(self,env):
        # Check current cell
        cc=env.cell(self.x,self.y)
        if cc.has_sample and cc.ctype!=ADRIAN:
            return self._take(cc,self.x,self.y)
        # Check adjacent cells (including Adrian)
        for ddx,ddy in [(0,1),(0,-1),(1,0),(-1,0),(0,0)]:
            nx=(self.x+ddx)%GRID_W; ny=(self.y+ddy)%GRID_H
            nc=env.g[ny][nx]
            if nc.has_sample:
                if self.energy<3:
                    self.energy=min(100,self.energy+22)
                    return f"Grace resting before EVA. E={self.energy}"
                self.energy-=3
                return self._take(nc,nx,ny)
        # nothing near — go closer
        return self._go_adrian(env)

    def _take(self,cell,nx,ny):
        cell.has_sample=False
        if cell.taumoeba:
            s=TauSample(); self.samples.append(s)
            self.knowledge+=8
            return f"Grace: Taumoeba sample! ({nx},{ny}) K={self.knowledge}"
        self.knowledge+=4
        return f"Grace: Sample collected ({nx},{ny}) K={self.knowledge}"

    def _experiment(self):
        if not self.samples: return "Grace: no samples"
        if self.energy<7:
            self.energy=min(100,self.energy+22)
            return f"Grace resting. E={self.energy}"
        self.energy-=7; self.exps+=1
        s=self.samples[-1]; s.exps+=1
        thr=min(0.65, 0.25+self.knowledge/300)
        r=random.random()
        if r<thr:
            d=random.uniform(0.10,0.22); s.compat=min(1.0,s.compat+d)
            self.knowledge+=20; self.exps_ok+=1
            self.q["experiment"]=min(3.0,self.q["experiment"]+0.1)
            return f"Grace: Exp SUCCESS compat={s.compat:.2f} K={self.knowledge}"
        elif r<thr+0.25:
            d=random.uniform(0.04,0.09); s.compat=min(1.0,s.compat+d)
            self.knowledge+=8
            return f"Grace: Exp PARTIAL compat={s.compat:.2f} K={self.knowledge}"
        else:
            s.viability=max(0.1,s.viability-0.07); self.knowledge+=2
            self.q["experiment"]=max(0.5,self.q["experiment"]-0.05)
            return f"Grace: Exp FAIL compat={s.compat:.2f} K={self.knowledge}"

    def _breed(self):
        if self.knowledge<40: return f"Grace: need 40K (have {self.knowledge})"
        if not self.samples:  return "Grace: no samples"
        if self.energy<14:
            self.energy=min(100,self.energy+22)
            return f"Grace resting. E={self.energy}"
        self.energy-=14
        best=max(self.samples,key=lambda s:s.compat)
        if best.viable():
            self.best=best; self.mscore+=30
            return f"Grace: *** VIABLE TAUMOEBA! *** compat={best.compat:.2f}"
        best.gen+=1; best.compat=min(1.0,best.compat+0.13)
        self.knowledge+=8
        return f"Grace: Breeding gen{best.gen} compat={best.compat:.2f}"

    def _deploy_beetle(self):
        if not self.beetles_left: return "Grace: all beetles deployed"
        if not (self.best and self.best.viable()): return "Grace: need viable taumoeba"
        if self.energy<10:
            self.energy=min(100,self.energy+22)
            return f"Grace resting. E={self.energy}"
        self.energy-=10
        name=self.beetles_left.pop(0)
        self.beetles_out.append(name)
        self.knowledge+=25; self.mscore+=25
        return f"Grace: Beetle '{name}' LAUNCHED! Score={self.mscore}"

    def _deploy_tmb(self,env):
        if not (self.best and self.best.viable()): return "Grace: no viable taumoeba"
        # Clear astrophage in radius 3
        cleared=0
        ax,ay=ADRIAN_POS
        for dy in range(-3,4):
            for dx in range(-3,4):
                nx=(self.x+dx)%GRID_W; ny=(self.y+dy)%GRID_H
                if env.g[ny][nx].ctype==ACLOUD and random.random()<0.6:
                    env.g[ny][nx].ctype=EMPTY; cleared+=1
        self.tmb_deployed=True; self.mscore+=20
        return f"Grace: Taumoeba deployed! Cleared {cleared} cells. Score={self.mscore}"

    def _talk(self,rocky):
        g=rocky.share_k()
        self.knowledge+=g
        return f"Grace↔Rocky: +{g}K total={self.knowledge}"

    def _escape(self,env):
        best=None; bscore=-999
        for ddx,ddy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx=(self.x+ddx)%GRID_W; ny=(self.y+ddy)%GRID_H
            if env.passable(nx,ny):
                sc=-env.damage_at(nx,ny)
                if sc>bscore: bscore=sc; best=(ddx,ddy)
        if best:
            ok,msg=self.move_toward(self.x+best[0],self.y+best[1],env)
            return f"Grace ESCAPING! {msg}"
        return "Grace: trapped!"


class Rocky:
    def __init__(self):
        self.x,self.y=ROCKY_START
        self.hp=120; self.energy=110; self.alive=True
        self.trust=0; self.fuel=100
        self.maps_shared=False; self.aph_shared=False
        self.interactions=0; self.fluency=0.0
        self.turn=0

    def dist(self,tx,ty):
        dx=min(abs(self.x-tx),GRID_W-abs(self.x-tx))
        dy=min(abs(self.y-ty),GRID_H-abs(self.y-ty))
        return dx+dy

    def move_toward(self,tx,ty,env):
        if self.energy<1: return False,"no energy"
        dx=tx-self.x; dy=ty-self.y
        if abs(dx)>GRID_W//2: dx=-dx
        if abs(dy)>GRID_H//2: dy=-dy
        sx=0 if dx==0 else(1 if dx>0 else -1)
        sy=0 if dy==0 else(1 if dy>0 else -1)
        for ddx,ddy in [(sx,0),(0,sy)]:
            if ddx==0 and ddy==0: continue
            nx=(self.x+ddx)%GRID_W; ny=(self.y+ddy)%GRID_H
            if env.passable(nx,ny):
                self.x=nx; self.y=ny; self.energy-=1
                return True,f"Rocky→({self.x},{self.y})"
        return False,"blocked"

    def decide(self,env,grace):
        self.turn+=1
        dg=self.dist(grace.x,grace.y)
        # Help if grace critical
        if (grace.hp<25 or grace.energy<15) and self.fuel>20:
            return "share_e",self._share_e(grace)
        # Build trust if close
        if dg<=5 and self.trust<3:
            return "talk",self._talk(grace)
        # Share data
        if not self.maps_shared and self.trust>=1:
            return "maps",self._maps(grace)
        if not self.aph_shared and self.trust>=2:
            return "aph",self._aph(grace)
        # Assist experiments
        if grace.exps>0 and dg<=5 and self.trust>=1:
            return "assist",self._assist(grace)
        # Move toward grace
        if dg>3:
            ok,msg=self.move_toward(grace.x,grace.y,env)
            return "move",msg
        # Rest
        self.energy=min(110,self.energy+18)
        return "rest",f"Rocky resting. E={self.energy}"

    def _share_e(self,grace):
        amt=min(20,self.fuel//3); self.fuel-=amt
        grace.energy=min(100,grace.energy+amt)
        return f"Rocky: shared {amt}E → Grace E={grace.energy}"

    def _talk(self,grace):
        self.interactions+=1; self.fluency=min(1.0,self.fluency+0.07)
        import random as rr
        chords=["Do-Mi-Sol","La-La-Re","Mi-Sol-Mi","Do-Re-Mi-Fa-Sol"]
        chord=rr.choice(chords)
        if self.interactions%4==0 and self.trust<3:
            self.trust+=1
        return f"Rocky [{chord}] trust={self.trust}/3 fluency={self.fluency:.0%}"

    def _maps(self,grace):
        grace.knowledge+=18; self.maps_shared=True
        return f"Rocky: star maps shared! Grace K={grace.knowledge}"

    def _aph(self,grace):
        grace.knowledge+=22; self.aph_shared=True
        return f"Rocky: Astrophage data shared! Grace K={grace.knowledge}"

    def _assist(self,grace):
        b=3*self.trust; grace.knowledge+=b
        return f"Rocky: assisted +{b}K → Grace K={grace.knowledge}"

    def share_k(self):
        if self.trust>=3: return 18
        if self.trust>=2: return 12
        if self.trust>=1: return 6
        return 0

# ═══════════════════════════════════════════════════════
#  SINGLE RUN
# ═══════════════════════════════════════════════════════
class Run:
    def __init__(self, run_id, seed):
        self.id=run_id; self.seed=seed
        self.env=Env(seed); self.grace=Grace(); self.rocky=Rocky()
        self.turn=0; self.active=True
        self.cause="timeout"
        self.log=[]
        self.k_hist=[]; self.aph_hist=[]

    def _log(self,msg):
        self.log.append(f"[T{self.turn:03d}] {msg}")

    def tick(self):
        """Execute one turn. Returns True if still running."""
        if not self.active: return False
        self.turn+=1

        # Grace acts
        if self.grace.alive:
            act,msg=self.grace.decide(self.env,self.rocky)
            self._log(f"Grace [{act}]: {msg}")
            if not self.grace.alive:
                self.active=False; self.cause="grace_died"; return False
            if self._complete():
                self.active=False; self.cause="mission_complete"
                self._log("=== MISSION COMPLETE — Earth saved! ===")
                return False

        # Rocky acts
        if self.rocky.alive:
            act,msg=self.rocky.decide(self.env,self.grace)
            self._log(f"Rocky [{act}]: {msg}")

        # Environment
        self.env.step()

        # History
        if self.turn%10==0:
            self.k_hist.append(self.grace.knowledge)
            self.aph_hist.append(self.env.aph_count())

        if self.turn>=MAX_TURNS:
            self.active=False; self.cause="timeout"
        return self.active

    def _complete(self):
        return (len(self.grace.beetles_out)>=2
                and self.grace.best and self.grace.best.viable()
                and self.grace.knowledge>=50)

    def result(self):
        g=self.grace; r=self.rocky
        return {
            "run":        self.id,
            "turns":      self.turn,
            "cause":      self.cause,
            "earth_saved": self.cause=="mission_complete",
            "knowledge":  g.knowledge,
            "mscore":     g.mscore,
            "beetles":    len(g.beetles_out),
            "taumoeba":   g.best is not None and g.best.viable(),
            "exps":       g.exps,
            "exps_ok":    g.exps_ok,
            "flashbacks": len(g.flashbacks),
            "trust":      r.trust,
            "aph_final":  self.env.aph_count(),
            "k_hist":     self.k_hist,
            "aph_hist":   self.aph_hist,
        }
