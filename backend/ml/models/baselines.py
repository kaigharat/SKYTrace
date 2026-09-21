"""SkyTrace baseline models.

Phase-1 baselines only:
    - RandomForestBaseline (static code features -> RF classifier)

Future phases will add:
    - CodeBERT baseline (in models/code_encoder.py)
    - CodeBERT + GNN
    - LSTM
    - Multi-modal fusion
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier


@dataclass
class RandomForestBaseline:
    """RandomForestClassifier wrapper.

    Uses class_weight='balanced' by default because the DiverseVul
    vulnerability class is ~5.7% of the dataset.
    """

    params: Dict[str, Any] = field(default_factory=lambda: {
        "n_estimators": 300,
        "max_depth": None,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
        "class_weight": "balanced",
        "n_jobs": -1,
        "random_state": 42,
    })
    model: Optional[RandomForestClassifier] = None
    fit_time_sec: float = 0.0
    n_features: int = 0

    def build(self) -> "RandomForestBaseline":
        self.model = RandomForestClassifier(**self.params)
        return self

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestBaseline":
        if self.model is None:
            self.build()
        self.n_features = X.shape[1]
        t0 = time.time()
        self.model.fit(X, y)
        self.fit_time_sec = time.time() - t0
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def feature_importances(self) -> Dict[str, float]:
        if self.model is None:
            return {}
        return {"feature_{:02d}".format(i): float(v) for i, v in enumerate(self.model.feature_importances_)}

    def get_params(self) -> Dict[str, Any]:
        return {
            "type": "RandomForestClassifier",
            "params": self.params,
            "n_features": self.n_features,
            "n_estimators_actual": self.model.n_estimators if self.model else None,
        }
