"""Rebuild the whole USIUBOT dataset in order, then validate it.

  1. extract_documents.py         Stage 2: the two local PDFs (calendar, handbook)
  2. import_collection_reports.py  only with --reimport: re-split the 2026-11-01 collection reports into snapshots
                                   (this overwrites the manifest, so do not use it after collect_web_sources.py)
  3. build_web_dataset.py         website, external and register files
  4. validate_dataset.py          final checks (exit code 1 if a blocking check fails)

Windows PowerShell, from the project root:
  $env:PYTHONDONTWRITEBYTECODE = "1"
  .\\backend\\.venv\\Scripts\\python.exe usiubot_datasets\\extraction_scripts\\build_all.py
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


# Stage 2 records carry the date the PDFs were first extracted. A re-run reproduces the same content, so the
# date is pinned; pass --extraction-date YYYY-MM-DD after changing the PDFs or the extraction rules.
EXTRACTION_DATE = "2026-11-01"


def run(script, *args):
    print(f"\n=== {script} ===", flush=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(HERE / script), *args], env=env)
    if r.returncode:
        print(f"{script} exited with code {r.returncode}")
    return r.returncode


def main():
    date = EXTRACTION_DATE
    if "--extraction-date" in sys.argv:
        date = sys.argv[sys.argv.index("--extraction-date") + 1]
    steps = [("extract_documents.py", "--extraction-date", date)]
    if "--reimport" in sys.argv:
        steps.append(("import_collection_reports.py",))
    steps += [("build_web_dataset.py",), ("validate_dataset.py",)]
    for s in steps:
        if run(*s):
            sys.exit(1)
    print("\nAll steps finished. Nothing was approved or imported into any database.")


if __name__ == "__main__":
    main()
