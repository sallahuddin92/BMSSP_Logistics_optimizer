"""Fixed local bootstrap for `python -I -B .../run.py`; no configurable code paths."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from task15_cohort_a_runner.__main__ import main
if __name__=='__main__':raise SystemExit(main())
