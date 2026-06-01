"""
Headless test — runs 20 simulations without GUI and shows terminal output.
Usage: python test_headless.py
"""
import sys, os, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *

DIRS = [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
SIM_MAX_TURNS = 90

class Cell:
    def __init__(self,t=EMPTY): self.type=t; self.aph_int=0.0; self.has_taum=False

class Grid:
    def __init__(self,seed):
        random.seed(seed); self.W=GRID_WIDTH; self.H=GRID_HEIGHT
        self.cells=[[Cell() for _ in range(self.W)] for _ in range(self.H)]
        self._setup()
    def c(self,x,y): return self.cells[y%self.H][x%self.W]
    def passable(self,x,y): return self.c(x,y).type!=PLANET_ADRIAN
    def hazard_dmg(self,x,y):
        cc=self.c(x,y)
        if cc.type==ASTROPHAGE_CLOUD: return max(3,int(ASTROPHAGE_DAMAGE*cc.aph_int*2))
        if cc.type==RADIATION_ZONE: return RADIATION_DAMAGE
        if cc.type==DEBRIS_FIELD: return DEBRIS_DAMAGE
        return 0
    def count_aph(self): return sum(1 for row in self.cells for cc in row if cc.type==ASTROPHAGE_CLOUD)
    def _setup(self):
        gx,gy=GRACE_START; rx,ry=ROCKY_START; ax,ay=ADRIAN_POS
        self.c(gx,gy).type=HAIL_MARY; self.c(rx,ry).type=BLIP_A
        for tx in range(min(gx,rx)+1,max(gx,rx)): self.c(tx,gy).type=TUNNEL
        for dy in range(-3,4):
            for dx in range(-3,4):
                nx,ny=ax+dx,ay+dy
                if 0<=nx<self.W and 0<=ny<self.H and math.sqrt(dx*dx+dy*dy)<=3:
                    cc=self.cells[ny][nx]; cc.type=PLANET_ADRIAN; cc.aph_int=0.5; cc.has_taum=True
        for dy in range(-5,6):
            for dx in range(-5,6):
                nx,ny=ax+dx,ay+dy
                if 0<=nx<self.W and 0<=ny<self.H and self.cells[ny][nx].type==EMPTY and random.random()<0.45:
                    self.cells[ny][nx].has_taum=True
        # Full Petrova line through grid center
        for step in range(max(self.W,self.H)):
            for offset in range(-1,2):
                x1=step%self.W; y1=(step+offset)%self.H
                cc=self.cells[y1][x1]
                if cc.type==EMPTY: cc.type=ASTROPHAGE_CLOUD; cc.aph_int=random.uniform(0.6,1.0)
                x2=(self.W-1-step)%self.W; y2=(step+offset)%self.H
                cc2=self.cells[y2][x2]
                if cc2.type==EMPTY: cc2.type=ASTROPHAGE_CLOUD; cc2.aph_int=random.uniform(0.6,1.0)
        for _ in range(8):
            x2,y2=random.randint(0,self.W-1),random.randint(0,self.H-1)
            if self.cells[y2][x2].type==EMPTY: self.cells[y2][x2].type=ASTROPHAGE_CLOUD; self.cells[y2][x2].aph_int=random.uniform(0.3,0.6)
        for _ in range(4):
            x2,y2=random.randint(0,self.W-1),random.randint(0,self.H-1)
            if self.cells[y2][x2].type==EMPTY: self.cells[y2][x2].type=RADIATION_ZONE
        for _ in range(4):
            x2,y2=random.randint(0,self.W-1),random.randint(0,self.H-1)
            if self.cells[y2][x2].type==EMPTY: self.cells[y2][x2].type=DEBRIS_FIELD
    def step(self,td):
        new=[]
        for y in range(self.H):
            for x in range(self.W):
                cc=self.cells[y][x]
                if cc.type==ASTROPHAGE_CLOUD:
                    if td: cc.aph_int=max(0,cc.aph_int-0.015)
                    if cc.aph_int<=0: cc.type=EMPTY; continue
                    cc.aph_int=min(1.0,cc.aph_int+0.008)
                    for dx2,dy2 in[(0,1),(0,-1),(1,0),(-1,0)]:
                        nx2,ny2=(x+dx2)%self.W,(y+dy2)%self.H
                        if self.cells[ny2][nx2].type==EMPTY and random.random()<0.035:
                            new.append((nx2,ny2,cc.aph_int*0.45))
        for nx2,ny2,ai in new: self.cells[ny2][nx2].type=ASTROPHAGE_CLOUD; self.cells[ny2][nx2].aph_int=ai
    def find_sample_near(self,cx,cy,r=8):
        best=None;bd=999
        for dy in range(-r,r+1):
            for dx in range(-r,r+1):
                nx2,ny2=(cx+dx)%self.W,(cy+dy)%self.H
                cc=self.cells[ny2][nx2]
                if cc.has_taum:
                    d=abs(dx)+abs(dy)
                    if d<bd: bd=d; best=(nx2,ny2)
        return best
    def collect_at(self,x,y):
        for dx2,dy2 in[(0,0),(0,1),(0,-1),(1,0),(-1,0)]:
            nx2,ny2=(x+dx2)%self.W,(y+dy2)%self.H
            cc=self.cells[ny2][nx2]
            if cc.has_taum: cc.has_taum=False; return True
        return False

class TauSample:
    def __init__(self): self.compat=0.0; self.gen=0; self.n_exp=0

class Grace:
    def __init__(self):
        self.x,self.y=GRACE_START; self.hp=100; self.energy=100; self.alive=True
        self.knowledge=0; self.mscore=0; self.samples=[]; self.best=None
        self.taum_dep=False; self.beetles_left=list(BEETLE_NAMES); self.beetles_out=[]
        self.exp_total=0; self.exp_ok=0; self.flashbacks=[]; self.lr=0.1
        self.wander_count=0
        self.q={"go_adrian":2.0,"collect":2.0,"experiment":1.5,"breed":1.2,
                "beetle":1.0,"rest":0.6,"communicate":0.8,"wander":0.5}
    def viable(self): return self.best is not None and self.best.compat>=0.8
    def act(self,grid,rocky):
        for thresh,txt in FLASHBACK_EVENTS.items():
            if self.knowledge>=thresh and thresh not in self.flashbacks:
                self.flashbacks.append(thresh); self.knowledge+=KNOWLEDGE_FLASHBACK
                return "flashback",f"[FLASHBACK] {txt}"
        if self.energy<10 or self.hp<12:
            self.energy=min(100,self.energy+ENERGY_REST_GAIN)
            if self.hp<30: self.hp=min(100,self.hp+6)
            return "rest",f"Resting HP={self.hp} E={self.energy}"
        dmg=grid.hazard_dmg(self.x,self.y)
        if dmg>0: return "escape",self._escape(grid)
        act=self._pick(grid,rocky); msg=self._exec(act,grid,rocky)
        return act,msg
    def _pick(self,grid,rocky):
        s=dict(self.q); ax,ay=ADRIAN_POS; dist=abs(self.x-ax)+abs(self.y-ay)
        has_s=len(self.samples)>0; can_b=self.knowledge>=TAUMOEBA_BREED_THRESHOLD and has_s
        if dist>4: s["go_adrian"]+=2.5
        if dist<=7: s["collect"]+=2.0
        if has_s: s["experiment"]+=2.5
        else: s["experiment"]-=3.0; s["breed"]-=3.0
        if can_b: s["breed"]+=3.0
        if self.viable(): s["beetle"]+=4.0
        if not has_s: s["collect"]+=1.5
        if self.wander_count>5: s["wander"]+=1.5; self.wander_count=0
        for k in s: s[k]+=random.uniform(0,0.25)
        return max(s,key=s.get)
    def _exec(self,act,grid,rocky):
        if act=="go_adrian": return self._go_adrian(grid)
        if act=="collect": return self._collect(grid)
        if act=="experiment": return self._experiment()
        if act=="breed": return self._breed()
        if act=="beetle": return self._beetle()
        if act=="communicate": gained=rocky.share_knowledge(); self.knowledge+=gained; return f"<>Rocky +{gained}"
        if act=="wander": dx2,dy2=random.choice(DIRS); return self._move(dx2,dy2,grid)
        self.energy=min(100,self.energy+ENERGY_REST_GAIN); return "Rested"
    def _move(self,dx2,dy2,grid):
        if self.energy<ENERGY_MOVE: self.energy=min(100,self.energy+ENERGY_REST_GAIN); return "Resting"
        nx2,ny2=(self.x+dx2)%grid.W,(self.y+dy2)%grid.H
        if not grid.passable(nx2,ny2):
            for adx,ady in[(dy2,dx2),(-dy2,-dx2)]:
                nnx,nny=(self.x+adx)%grid.W,(self.y+ady)%grid.H
                if grid.passable(nnx,nny): nx2,ny2=nnx,nny; break
            else: return "Blocked"
        self.x,self.y=nx2,ny2; self.energy-=ENERGY_MOVE; self.wander_count+=1
        dmg=grid.hazard_dmg(self.x,self.y)
        if dmg>0:
            self.hp=max(0,self.hp-dmg)
            if self.hp==0: self.alive=False
        return f"->({self.x},{self.y}) HP={self.hp}"
    def _step_toward(self,tx,ty,grid):
        dx2=tx-self.x; dy2=ty-self.y
        if abs(dx2)>grid.W//2: dx2=-dx2
        if abs(dy2)>grid.H//2: dy2=-dy2
        if dx2==0 and dy2==0: return "At target"
        step=(1 if dx2>0 else -1,0) if abs(dx2)>=abs(dy2) else (0,1 if dy2>0 else -1)
        return self._move(step[0],step[1],grid)
    def _escape(self,grid):
        best_d=None;bv=9999
        for dx2,dy2 in DIRS:
            nx2,ny2=(self.x+dx2)%grid.W,(self.y+dy2)%grid.H
            if grid.passable(nx2,ny2):
                d=grid.hazard_dmg(nx2,ny2)
                if d<bv: bv=d; best_d=(dx2,dy2)
        if best_d: return self._move(best_d[0],best_d[1],grid)
        return "Trapped!"
    def _go_adrian(self,grid):
        ax,ay=ADRIAN_POS; best=None; bd=999
        for dy in range(-5,6):
            for dx in range(-5,6):
                nx2,ny2=(ax+dx)%grid.W,(ay+dy)%grid.H; cc=grid.cells[ny2][nx2]
                if cc.type not in(PLANET_ADRIAN,ASTROPHAGE_CLOUD):
                    if any(grid.cells[(ny2+dd[1])%grid.H][(nx2+dd[0])%grid.W].type==PLANET_ADRIAN for dd in[(0,1),(0,-1),(1,0),(-1,0)]):
                        d=abs(self.x-nx2)+abs(self.y-ny2)
                        if d<bd: bd=d; best=(nx2,ny2)
        if best: return self._step_toward(best[0],best[1],grid)
        return self._step_toward(ax,ay,grid)
    def _collect(self,grid):
        if self.energy<ENERGY_EVA: self.energy=min(100,self.energy+ENERGY_REST_GAIN); return "Resting EVA"
        if grid.collect_at(self.x,self.y):
            self.energy-=ENERGY_EVA; s=TauSample(); self.samples.append(s)
            self.knowledge+=KNOWLEDGE_SAMPLE_COLLECTED; return f"Sample! K={self.knowledge}"
        near=grid.find_sample_near(self.x,self.y,8)
        if near: return self._step_toward(near[0],near[1],grid)
        return self._go_adrian(grid)
    def _experiment(self):
        if not self.samples: return "No samples"
        if self.energy<ENERGY_EXPERIMENT: self.energy=min(100,self.energy+ENERGY_REST_GAIN); return "Resting"
        self.energy-=ENERGY_EXPERIMENT; self.exp_total+=1; s=self.samples[-1]; s.n_exp+=1
        thresh=min(0.65,0.25+self.knowledge/300); r=random.random()
        if r<thresh: d=random.uniform(0.10,0.22); s.compat=min(1.0,s.compat+d); self.knowledge+=KNOWLEDGE_EXPERIMENT_SUCCESS; self.exp_ok+=1; res="OK"
        elif r<thresh+0.25: d=random.uniform(0.03,0.08); s.compat=min(1.0,s.compat+d); self.knowledge+=KNOWLEDGE_EXPERIMENT_PARTIAL; res="PART"
        else: self.knowledge+=KNOWLEDGE_EXPERIMENT_FAIL; res="FAIL"
        return f"Exp#{s.n_exp} {res} compat={s.compat:.2f}"
    def _breed(self):
        if self.knowledge<TAUMOEBA_BREED_THRESHOLD: return "Need more K"
        if not self.samples: return "No samples"
        if self.energy<ENERGY_EXPERIMENT*2: self.energy=min(100,self.energy+ENERGY_REST_GAIN); return "Resting"
        self.energy-=ENERGY_EXPERIMENT*2; best=max(self.samples,key=lambda s2:s2.compat)
        best.gen+=1; best.compat=min(1.0,best.compat+0.14); self.knowledge+=KNOWLEDGE_EXPERIMENT_PARTIAL
        if best.compat>=0.8: self.best=best; self.mscore+=30; return f"VIABLE! compat={best.compat:.2f}"
        return f"Breed gen{best.gen} compat={best.compat:.2f}"
    def _beetle(self):
        if not self.beetles_left: return "No beetles"
        if not self.viable(): return "Need viable Taumoeba"
        if self.energy<ENERGY_DEPLOY_BEETLE: self.energy=min(100,self.energy+ENERGY_REST_GAIN); return "Resting"
        self.energy-=ENERGY_DEPLOY_BEETLE; name=self.beetles_left.pop(0); self.beetles_out.append(name)
        self.knowledge+=KNOWLEDGE_BEETLE_DEPLOYED; self.mscore+=25; return f"Beetle '{name}' LAUNCHED!"

class Rocky:
    def __init__(self):
        self.x,self.y=ROCKY_START; self.hp=120; self.energy=110; self.alive=True
        self.trust=0; self.fuel=100; self.maps_shared=False; self.aph_shared=False
        self.talk_count=0; self.wander_dir=random.choice(DIRS); self.wander_steps=0
    def share_knowledge(self):
        b=KNOWLEDGE_ROCKY_SHARE
        if self.trust>=3: return int(b*1.5)
        if self.trust>=2: return b
        if self.trust>=1: return int(b*0.5)
        return 0
    def act(self,grid,grace):
        dist=abs(self.x-grace.x)+abs(self.y-grace.y)
        if (grace.hp<25 or grace.energy<15) and self.fuel>20:
            amt=min(25,self.fuel//3); self.fuel-=amt; grace.energy=min(100,grace.energy+amt)
            return "share_energy",f"Shared {amt}E"
        if dist<=5 and self.trust<3:
            self.talk_count+=1
            if self.talk_count%4==0 and self.trust<3: self.trust+=1
            chord=random.choice(list(ROCKY_PHRASES.values()))
            return "communicate",f"[{chord}] trust={self.trust}"
        if not self.maps_shared and self.trust>=1: grace.knowledge+=20; self.maps_shared=True; return "share_maps","Maps shared"
        if not self.aph_shared and self.trust>=2: grace.knowledge+=25; self.aph_shared=True; return "share_aph","Aph data shared"
        if grace.exp_total>0 and dist<=6:
            bonus=3*self.trust; grace.knowledge+=bonus; return "assist",f"+{bonus}K"
        if dist>4: return "move",self._step_toward(grace.x,grace.y,grid)
        # Wander freely
        self.wander_steps+=1
        if self.wander_steps>random.randint(3,7): self.wander_dir=random.choice(DIRS); self.wander_steps=0
        dx2,dy2=self.wander_dir; nx2,ny2=(self.x+dx2)%grid.W,(self.y+dy2)%grid.H
        if not grid.passable(nx2,ny2): self.wander_dir=random.choice(DIRS); dx2,dy2=self.wander_dir
        if self.energy>=ENERGY_MOVE:
            nx2,ny2=(self.x+dx2)%grid.W,(self.y+dy2)%grid.H
            if grid.passable(nx2,ny2): self.x,self.y=nx2,ny2; self.energy-=ENERGY_MOVE
        else: self.energy=min(110,self.energy+ENERGY_REST_GAIN)
        return "wander",f"Rocky->({self.x},{self.y})"
    def _step_toward(self,tx,ty,grid):
        dx2=tx-self.x; dy2=ty-self.y
        if abs(dx2)>grid.W//2: dx2=-dx2
        if abs(dy2)>grid.H//2: dy2=-dy2
        if abs(dx2)>=abs(dy2): step=(1 if dx2>0 else -1,0)
        else: step=(0,1 if dy2>0 else -1)
        nx2,ny2=(self.x+step[0])%grid.W,(self.y+step[1])%grid.H
        if grid.passable(nx2,ny2) and self.energy>=ENERGY_MOVE:
            self.x,self.y=nx2,ny2; self.energy-=ENERGY_MOVE
        return f"Rocky->({self.x},{self.y})"

class Sim:
    def __init__(self,run_id,seed):
        self.run_id=run_id; self.seed=seed; self.turn=0; self.done=False; self.cause="running"
        self.grid=Grid(seed); self.grace=Grace(); self.rocky=Rocky()
        self.hist_k=[]; self.hist_hp=[]; self.hist_aph=[]
    def tick(self):
        if self.done: return []
        self.turn+=1; lines=[]
        if self.grace.alive:
            act,msg=self.grace.act(self.grid,self.rocky)
            lines.append(f"[T{self.turn:03d}] Grace [{act}]: {msg}")
            if not self.grace.alive: self.done=True; self.cause="grace_died"; self._rec(); return lines
            if self._complete(): self.done=True; self.cause="mission_complete"; lines.append(f"[T{self.turn:03d}] MISSION COMPLETE!"); self._rec(); return lines
        if self.rocky.alive: act,msg=self.rocky.act(self.grid,self.grace); lines.append(f"[T{self.turn:03d}] Rocky [{act}]: {msg}")
        self.grid.step(self.grace.taum_dep); self._rec()
        if self.turn>=SIM_MAX_TURNS: self.done=True; self.cause="timeout"; lines.append(f"[T{self.turn:03d}] Timeout")
        return lines
    def _rec(self): self.hist_k.append(self.grace.knowledge); self.hist_hp.append(self.grace.hp); self.hist_aph.append(self.grid.count_aph())
    def _complete(self): return len(self.grace.beetles_out)>=2 and self.grace.viable() and self.grace.knowledge>=50
    def summary(self):
        g=self.grace; rk=self.rocky
        return {"run":self.run_id,"turns":self.turn,"cause":self.cause,"knowledge":g.knowledge,
                "mscore":g.mscore,"beetles":len(g.beetles_out),"viable":g.viable(),
                "exp_total":g.exp_total,"exp_ok":g.exp_ok,"flashbacks":len(g.flashbacks),
                "trust":rk.trust,"aph_final":self.grid.count_aph(),"grace_hp":g.hp,
                "grace_alive":g.alive,"hist_k":self.hist_k,"hist_hp":self.hist_hp,"hist_aph":self.hist_aph}

if __name__=="__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    print(f"Running 20 simulations ({SIM_MAX_TURNS} turns each)...\n")
    results=[]
    for i in range(20):
        sim=Sim(i+1,2000+i)
        while not sim.done: sim.tick()
        r=sim.summary()
        results.append(r)
        mark="✓" if r["cause"]=="mission_complete" else "✗"
        print(f"  Run {i+1:2d} {mark}  T={r['turns']:3d}  K={r['knowledge']:3d}  HP={r['grace_hp']:3d}  B={r['beetles']}  {r['cause']}")

    n=len(results); c=sum(1 for r in results if r["cause"]=="mission_complete")
    print(f"\n{'='*50}")
    print(f"  Earth Saved:    {'YES' if c==n else f'{c}/{n}'}")
    print(f"  Complete:       {c}/{n} ({c/n*100:.0f}%)")
    print(f"  Avg turns:      {sum(r['turns'] for r in results)/n:.1f}")
    print(f"  Avg knowledge:  {sum(r['knowledge'] for r in results)/n:.1f}")
    print(f"  Avg HP (end):   {sum(r['grace_hp'] for r in results)/n:.1f}")
    print(f"  Taumoeba bred:  {sum(1 for r in results if r['viable'])/n*100:.0f}%")
    print(f"{'='*50}")

    # Save graph
    fig,axes=plt.subplots(2,3,figsize=(15,9))
    fig.patch.set_facecolor("#0d1117")
    fig.suptitle(f"Project Hail Mary — 20 Simulation Analysis (90 turns each)\nMission Complete: {c}/{n}",
                 color="#58a6ff",fontsize=13)
    for ax in axes.flat:
        ax.set_facecolor("#161b22"); ax.tick_params(colors="#8b949e",labelsize=8)
        for sp in ax.spines.values(): sp.set_color("#30363d")
        ax.xaxis.label.set_color("#c9d1d9"); ax.yaxis.label.set_color("#c9d1d9")
        ax.title.set_color("#58a6ff")

    # 1 Knowledge
    ax=axes[0,0]
    for r in results: ax.plot(r["hist_k"],alpha=0.3,lw=1,color="#00ff88" if r["cause"]=="mission_complete" else "#555")
    ml=max(len(r["hist_k"]) for r in results)
    padded=[r["hist_k"]+[r["hist_k"][-1]]*(ml-len(r["hist_k"])) for r in results]
    ax.plot(np.mean(padded,axis=0),color="#58a6ff",lw=2.5,label="Mean")
    ax.axhline(50,color="#ffd700",lw=1,ls="--",label="Mission threshold")
    ax.set_title("Knowledge Progression"); ax.set_xlabel("Turn"); ax.set_ylabel("Knowledge")
    ax.legend(facecolor="#161b22",labelcolor="#c9d1d9",fontsize=7)

    # 2 HP
    ax=axes[0,1]
    for r in results: ax.plot(r["hist_hp"],alpha=0.3,lw=1,color="#00ff88" if r["grace_alive"] else "#f85149")
    padded=[r["hist_hp"]+[r["hist_hp"][-1]]*(ml-len(r["hist_hp"])) for r in results]
    ax.plot(np.mean(padded,axis=0),color="#ff6b35",lw=2.5,label="Mean HP")
    ax.set_title("Grace HP Over Time"); ax.set_xlabel("Turn"); ax.set_ylabel("HP")
    ax.legend(facecolor="#161b22",labelcolor="#c9d1d9",fontsize=7)

    # 3 Astrophage
    ax=axes[0,2]
    for r in results: ax.plot(r["hist_aph"],alpha=0.3,lw=1,color="#8B0000")
    padded=[r["hist_aph"]+[r["hist_aph"][-1]]*(ml-len(r["hist_aph"])) for r in results]
    ax.plot(np.mean(padded,axis=0),color="#ff4444",lw=2.5,label="Mean")
    ax.set_title("Astrophage Spread"); ax.set_xlabel("Turn"); ax.set_ylabel("Cells")
    ax.legend(facecolor="#161b22",labelcolor="#c9d1d9",fontsize=7)

    # 4 Pie
    ax=axes[1,0]
    ends={}
    for r in results: ends[r["cause"]]=ends.get(r["cause"],0)+1
    lbls=list(ends.keys()); szs=[ends[k] for k in lbls]
    cols=["#00ff88","#f85149","#8b949e"][:len(lbls)]
    ax.pie(szs,labels=lbls,colors=cols,autopct="%1.0f%%",textprops={"color":"#c9d1d9","fontsize":8})
    ax.set_title("Simulation Outcomes")

    # 5 Scatter experiments
    ax=axes[1,1]
    for r in results:
        rate=r["exp_ok"]/max(1,r["exp_total"])*100
        ax.scatter(r["exp_total"],rate,c="#00ff88" if r["viable"] else "#8b949e",alpha=0.8,s=60,edgecolors="#30363d")
    ax.set_title("Experiments vs Success Rate"); ax.set_xlabel("Total Exp"); ax.set_ylabel("Success %")

    # 6 Final knowledge bar
    ax=axes[1,2]
    runs=[r["run"] for r in results]; knows=[r["knowledge"] for r in results]
    bar_cols=["#00ff88" if r["cause"]=="mission_complete" else "#f85149" for r in results]
    ax.bar(runs,knows,color=bar_cols,edgecolor="#30363d",lw=0.5)
    ax.axhline(sum(knows)/len(knows),color="#58a6ff",lw=1.5,ls="--",label=f"Mean={sum(knows)/len(knows):.0f}")
    ax.set_title("Final Knowledge per Run"); ax.set_xlabel("Run #"); ax.set_ylabel("Knowledge")
    ax.legend(facecolor="#161b22",labelcolor="#c9d1d9",fontsize=7)

    plt.tight_layout()
    out="analysis_output/simulation_analysis.png"
    os.makedirs("analysis_output",exist_ok=True)
    plt.savefig(out,dpi=150,bbox_inches="tight",facecolor="#0d1117")
    print(f"\nGraph saved: {out}")
