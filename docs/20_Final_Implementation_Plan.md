# 20 — Final Implementation Plan

## Checkpoints

1. Foundation: environment/config/tests/docs reproducible.
2. Safe runtime: pipeline, camera, UI và virtual output fail closed.
3. Trusted model: governed dataset, evaluation và signed-off bundle.
4. Optional agent: isolated, observable, denylisted private data.
5. Release candidate: package, clean-machine/hardware/privacy acceptance.

## Handoff template

- Objective và phase
- Files/config/schema changed
- Commands/tests và exact result
- Runtime/hardware evidence
- Artifacts/hashes
- Known failures/limitations
- Next safe action

## Definition of Final

- Clean Python 3.12 environment installs from locked requirements.
- Full automated suite passes and high-risk modules have meaningful coverage.
- Custom model bundle validates, cold-loads and has published per-class metrics.
- Raw frame never reaches disk/log/virtual output on tested failure paths.
- Camera disconnect, model exception và output exception fail closed.
- Face template consent/reset/delete lifecycle works.
- OBS/Zoom and clean Windows package are manually accepted.
- Agent is optional and cannot ingest secrets/frames/biometrics.
- README/docs/changelog match actual release, including unresolved limitations.
