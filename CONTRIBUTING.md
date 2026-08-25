# Contributing

Use Python 3.10 or newer and Node.js 22 for constructor development.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev,cv]"
npm install
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/slidecraft check-install
```

Changes to a schema or scene route require a versioned contract update and a generic fixture. Slide-specific IDs, titles, layouts, and asset choices must not enter reusable compiler code. Constructor changes require package validation and, where available, a native Microsoft PowerPoint render comparison.

Never weaken a quality gate to make a fixture pass. Add a supported route or return a clear unsupported-capability result before publication.
