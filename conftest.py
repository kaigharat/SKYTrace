"""Root test configuration and legacy module mapping."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Map skytrace to backend.ml so legacy test suites and scripts can import skytrace seamlessly
import backend
import backend.ml as ml_pkg
import backend.ml.data
import backend.ml.evaluation
import backend.ml.features
import backend.ml.models
import backend.ml.training
import backend.ml.utils

sys.modules["skytrace"] = ml_pkg
sys.modules["skytrace.data"] = backend.ml.data
sys.modules["skytrace.evaluation"] = backend.ml.evaluation
sys.modules["skytrace.features"] = backend.ml.features
sys.modules["skytrace.models"] = backend.ml.models
sys.modules["skytrace.training"] = backend.ml.training
sys.modules["skytrace.utils"] = backend.ml.utils
