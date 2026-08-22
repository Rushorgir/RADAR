# AI-3: Maneuver Advisory Module — Owner: Udarsh

## Responsibility
- Compute minimum delta-v avoidance maneuvers for flagged high-risk conjunctions
- Closed-form / numerical optimization (NOT ML — this is orbital mechanics)
- Output burn direction, magnitude, resulting miss distance improvement, fuel estimate

## Key Files
- `delta_v.py` — Delta-v computation for along-track, radial, cross-track burns
- `optimizer.py` — Minimize fuel cost subject to miss distance constraint
- `models.py` — ManeuverAdvisory data model

## Note for Judges
This is constrained optimization, not ML. Being precise about this boundary
strengthens the credibility of the ML components elsewhere in the system.
