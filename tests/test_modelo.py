import json
from pathlib import Path

import mlflow.sklearn
import pandas as pd
import pytest

from src.datos import BASE, TARGET
from src.metricas import evaluate


def test_champion_reproduces_registered_ap_and_cost():
    root = Path(__file__).parent / "fixtures"
    reference = json.loads((root / "metricas.json").read_text())
    fixed = pd.read_csv(root / "holdout.csv", float_precision="round_trip")
    model = mlflow.sklearn.load_model(str(root / "champion"))
    result = evaluate(fixed[TARGET], model.predict_proba(fixed[BASE])[:, 1], model.threshold)
    # Tolerancia absoluta para el redondeo de coma flotante. El costo usa conteos.
    assert result["ap"] == pytest.approx(reference["ap"], rel=0, abs=1e-12)
    assert result["cost_per_1000"] == reference["cost_per_1000"]
