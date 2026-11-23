# Contributing and local checks

The installable solver is tested with Python's standard-library `unittest`; run the same fast suite as CI with:

```sh
python -m unittest discover -s tests -t .
python scripts/run_doctests.py
python -m buttcrack selftest --quick
```

For the longer search checks, use `BUTTCRACK_SLOW=1 python -m unittest discover -s tests -t .` and `python -m buttcrack selftest --slow`. Kryptos research scripts and their focused tests are a separate research archive; some require optional native tools or lengthy searches. See `.github/workflows/ci.yml` for the authoritative split between per-change checks and scheduled checks.

Lint with `pip install -e ".[dev]" && ruff check .`. Browser tests are optional for Python-only changes: install Node dependencies with `npm install`, install Chromium with `npx playwright install chromium`, then run `npx playwright test`. JavaScript unit tests can be run separately with `npm run test:web` and `npm run test:research`.

The release workflow creates checksums after building release artifacts. A source checkout has no release artifact checksum manifest; do not treat a missing manifest as a checksum for a published release.
