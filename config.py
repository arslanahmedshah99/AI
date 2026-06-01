GRID_WIDTH  = 40
GRID_HEIGHT = 30

EMPTY=0; ASTROPHAGE_CLOUD=1; PLANET_ADRIAN=2; HAIL_MARY=3
BLIP_A=4; BEETLE_PROBE=5; RADIATION_ZONE=6; DEBRIS_FIELD=7
TUNNEL=8; PETROVA_LINE=9

GRACE_START = (1, 12)
ROCKY_START = (1, 10)
ADRIAN_POS  = (33, 22)

ENERGY_MOVE=1; ENERGY_EVA=4; ENERGY_EXPERIMENT=7
ENERGY_DEPLOY_BEETLE=10; ENERGY_REST_GAIN=22
ASTROPHAGE_DAMAGE=4; RADIATION_DAMAGE=3; DEBRIS_DAMAGE=1

KNOWLEDGE_SAMPLE_COLLECTED=5; KNOWLEDGE_EXPERIMENT_SUCCESS=20
KNOWLEDGE_EXPERIMENT_PARTIAL=8; KNOWLEDGE_EXPERIMENT_FAIL=2
KNOWLEDGE_ROCKY_SHARE=15; KNOWLEDGE_BEETLE_DEPLOYED=25; KNOWLEDGE_FLASHBACK=10

SIM_MAX_TURNS=120
TAUMOEBA_BREED_THRESHOLD=40

ROCKY_PHRASES={
    "experiment_result":"Do-Mi-Sol-Do","danger_warning":"La-La-Re",
    "resource_share":"Mi-Sol-Mi","knowledge_transfer":"Do-Re-Mi-Fa-Sol",
    "greeting":"Do-Mi-Sol","help_request":"Re-Fa-La-Re",
}
BEETLE_NAMES=["John","Paul","George","Ringo"]
FLASHBACK_EVENTS={
    10:"You are Dr. Ryland Grace, a biologist...",
    25:"Eva Stratt recruited you for this mission...",
    40:"Astrophage threatens to dim the Sun...",
    60:"You volunteered knowing you'd never return...",
    80:"Earth has 30 years before climate collapse...",
    100:"You are Earth's last hope.",
}

WAYPOINT_SETS = [
    [(10, 24), (17, 25), (23, 24), (30, 23), (33, 22)],
    [(9,  23), (17, 24), (23, 23), (30, 22), (33, 22)],
    [(10, 22), (17, 23), (23, 22), (31, 22), (33, 22)],
    [(9,  25), (17, 25), (23, 24), (30, 24), (33, 23)],
    [(11, 26), (17, 26), (23, 25), (31, 23), (33, 22)],
    [(8,  21), (17, 22), (23, 21), (30, 21), (33, 21)],
    [(10, 27), (17, 27), (23, 26), (30, 24), (33, 22)],
    [(9,  20), (17, 21), (23, 20), (31, 21), (33, 21)],
]
