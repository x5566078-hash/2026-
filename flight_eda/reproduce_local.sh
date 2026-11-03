#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
EDA_SCI_PY="/opt/anaconda3/bin/python"
EDA_PDF_PY="/Users/lichenghao/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12"
if [[ ! -x "$EDA_SCI_PY" ]]; then EDA_SCI_PY="$(command -v python3)"; fi
if [[ ! -x "$EDA_PDF_PY" ]]; then EDA_PDF_PY="$EDA_SCI_PY"; fi
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLCONFIGDIR="$PWD/.mplcache"
"$EDA_SCI_PY" src/download_data.py
"$EDA_SCI_PY" src/analysis.py
"$EDA_SCI_PY" src/explorer.py
"$EDA_SCI_PY" src/build_interactive.py
"$EDA_SCI_PY" src/build_notebook.py
"$EDA_PDF_PY" src/build_report.py
"$EDA_SCI_PY" src/validate_results.py
if command -v node >/dev/null; then node src/check_interactive.cjs; fi
