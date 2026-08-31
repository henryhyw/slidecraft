# Contributing

Start by reading `AGENTS.md`, `slidepoise/SKILL.md`, and `slidepoise/references/maintenance.md`.

Before opening a pull request, run these checks.

```bash
python -m pytest -q
node --test tests/console_interactions.test.mjs tests/panel_interactions.test.mjs
python slidepoise/scripts/preflight_config.py framework/defaults/slidepoise-config.json
python slidepoise/scripts/preflight_catalogs.py --profiles-root profiles
python slidepoise/scripts/audit_skill_boundaries.py
```

Changes to the workflow must preserve the three human approval gates. Mechanical tools may measure, validate, transform, and construct. Visual and semantic judgement remains with the host Agent.
