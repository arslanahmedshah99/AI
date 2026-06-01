# Project Hail Mary — Multi-Agent AI Simulation
## CPS7004 Artificial Intelligence — Assessment 1

### Requirements
- Python 3.12+
- `pip install matplotlib numpy`
- `tkinter` (included with Python on Windows/Mac; `sudo apt install python3-tk` on Linux)

### How to Run

```bash
# Real-time GUI visualisation
python main.py

# Headless batch run (20 simulations, prints stats)
python main.py --headless

# Generate analysis graphs (saves to analysis_output/)
python main.py --analyse
```

### Project Structure
```
hail_mary_sim/
├── main.py               ← Entry point
├── config.py             ← All constants & parameters
├── simulation.py         ← Simulation engine + BatchRunner
├── visualisation.py      ← Tkinter GUI
├── analysis.py           ← Matplotlib graphs (20-run analysis)
├── agents/
│   ├── base_agent.py     ← Abstract Agent class
│   ├── grace.py          ← Dr. Ryland Grace (Q-learning AI)
│   └── rocky.py          ← Rocky (cooperative Eridian AI)
└── environment/
    └── grid.py           ← 30×30 space grid, Astrophage spreading
```

### Key AI Features
- **Grace**: Q-learning-inspired adaptive strategy, flashback memory system,
  Taumoeba breeding experiments with scientific log
- **Rocky**: Rule-based cooperative AI, progressive sonar translation system,
  trust-level mechanics
- **Environment**: Procedural Astrophage spreading with adaptive resistance
  when Taumoeba is deployed
- **Beetle Probes**: John, Paul, George, Ringo — autonomous data-relay drones
