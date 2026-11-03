#!/usr/bin/env bash
# Rebuild the GitHub version from its fixed public CSV sources.
set -euo pipefail
cd "$(dirname "$0")"

# Prefer the caller's active virtual environment; override with EDA_PYTHON.
if [[ -n "${EDA_PYTHON:-}" ]]; then
  PY="$EDA_PYTHON"
elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PY="$VIRTUAL_ENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "Python 3 is required. Install Python and run: python -m pip install -r requirements.txt" >&2
  exit 1
fi

export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLCONFIGDIR="$PWD/.mplcache"
mkdir -p "$MPLCONFIGDIR"

echo "Using Python: $PY"
"$PY" src/download_data.py
"$PY" src/analysis.py
"$PY" src/explorer.py
"$PY" src/build_interactive.py
"$PY" src/build_notebook.py
# PDF generation can depend on an available CJK font.
"$PY" src/build_report.py
"$PY" src/validate_results.py

if command -v node >/dev/null 2>&1; then
  node src/check_interactive.cjs
else
  echo "Node.js not found: skipping optional JavaScript interaction check."
fi
echo "Rebuild finished. Check output/validation.json and the generated PDF."
