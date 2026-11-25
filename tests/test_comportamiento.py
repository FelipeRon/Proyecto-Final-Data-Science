"""Comportamiento de negocio que el champion debe cumplir en el dominio de mantenimiento.

El champion es un ensamble de árboles, así que no garantiza monotonía lectura a lectura.
Las pruebas verifican el efecto agregado sobre la muestra fija del repositorio, que es lo
que afecta a la lista de inspección de un turno, y casos extremos claros.
"""
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main
from src.datos import BASE

ROOT = Path(__file__).parent / "fixtures"
READING = dict(product_type="L", air_temperature_k=300., process_temperature_k=310.,
               rotational_speed_rpm=1500., torque_nm=40., tool_wear_min=100.)


@pytest.fixture(scope="module")
def champion():
    return mlflow.sklearn.load_model(str(ROOT / "champion"))


@pytest.fixture(scope="module")
def sample():
    return pd.read_csv(ROOT / "holdout.csv", float_precision="round_trip")[BASE]


def inspection_rate(model, frame):
    return float((model.predict_proba(frame)[:, 1] >= model.threshold).mean())


@pytest.mark.parametrize("column,delta", [("tool_wear_min", 100.), ("torque_nm", 20.)])
def test_mas_desgaste_o_torque_no_reduce_el_riesgo(champion, sample, column, delta):
    # Más desgaste de herramienta o más torque no pueden bajar el riesgo de falla del turno.
    shifted = sample.assign(**{column: sample[column] + delta})
    before = champion.predict_proba(sample)[:, 1]
    after = champion.predict_proba(shifted)[:, 1]
    assert after.mean() > before.mean()
    assert inspection_rate(champion, shifted) > inspection_rate(champion, sample)


def test_sobrecarga_evidente_se_inspecciona_y_lectura_normal_continua(champion):
    normal = pd.DataFrame([READING], columns=BASE)
    overload = pd.DataFrame([{**READING, "torque_nm": 70., "tool_wear_min": 240.}], columns=BASE)
    assert champion.predict_proba(normal)[0, 1] < champion.threshold
    assert champion.predict_proba(overload)[0, 1] >= champion.threshold


def test_modelo_que_no_carga_activa_respaldo(monkeypatch, tmp_path):
    # Sin FORCE_FALLBACK: el registro falla y el servicio debe responder con la regla del PSet 3.
    monkeypatch.delenv("FORCE_FALLBACK", raising=False)
    monkeypatch.setenv("PSET4_BACKEND", "local")
    monkeypatch.setenv("PREDICTION_LOG", str(tmp_path / "predicciones.jsonl"))

    class Unavailable:
        def get_model_version_by_alias(self, *args):
            raise ConnectionError("registro MLflow no disponible")

    monkeypatch.setattr(main.mlflow, "MlflowClient", Unavailable)
    client = TestClient(main.app)
    assert client.get("/salud").json() == {"estado": "degradado", "modelo_cargado": False}
    body = client.post("/predecir", json={**READING, "torque_nm": 65.}).json()
    assert body["respaldo"] is True and body["version_modelo"] == "regla-v1"
    assert body["decision"] == "inspeccionar"
