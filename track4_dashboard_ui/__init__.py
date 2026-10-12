"""Track 4: Stability & Dashboard package."""

from pathlib import Path
import sys

_nested_pkg = Path(__file__).resolve().parent / "track4_dashboard_ui"
if _nested_pkg.exists() and str(_nested_pkg) not in sys.path:
    sys.path.insert(0, str(_nested_pkg))

try:
    from .track4_dashboard_ui import backend, failover_engine
except ImportError:
    pass
