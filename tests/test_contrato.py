import json

import pytest
from fastapi.testclient import TestClient

from api.main import app

READING = dict(product_type="L", air_temperature_k=300., process_temperature_k=310.,
               rotational_speed_rpm=1500., torque_nm=40., tool_wear_min=100.)


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("FORCE_FALLBACK", "1")
    path = tmp_path / "predicciones.jsonl"
    monkeypatch.setenv("PREDICTION_LOG", str(path))
    return TestClient(app), path


def test_contract(setup):
    client, path = setup
    response = client.post("/predecir", json=READING)
    assert response.status_code == 200
    body = response.json()
    assert body["respaldo"] and body["decision"] == "continuar"
    event = json.loads(path.read_text())
    assert event["id_prediccion"] == body["id_prediccion"]
    assert event["entradas"] == READING and event["latencia_ms"] >= 0


@pytest.mark.parametrize("reading,field", [
    ({k: v for k, v in READING.items() if k != "torque_nm"}, "torque_nm"),
    ({**READING, "torque_nm": "40"}, "torque_nm"),
    ({**READING, "product_type": "X"}, "product_type"),
])
def test_invalid_field(setup, reading, field):
    client, path = setup
    response = client.post("/predecir", json=reading)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == field
    assert not path.exists()


@pytest.mark.parametrize("change", [{"tool_wear_min": 200.}, {"torque_nm": 60.}])
def test_operational_fallback(setup, change):
    client, _ = setup
    assert client.post("/predecir", json={**READING, **change}).json()["decision"] == "inspeccionar"

def test_prediction_uses_preprocessing_and_threshold(monkeypatch, tmp_path):
    from api import main
    from src.pipeline import DecisionModel, make_pipeline
    from sklearn.linear_model import LogisticRegression
    import pandas as pd

    frame = pd.DataFrame([READING, {**READING, 'torque_nm':70.}])
    model = DecisionModel(make_pipeline(LogisticRegression()), threshold=.65).fit(frame,[0,1])
    meta = {"version":"test-1","run_id":"fixture","respaldo":False}
    monkeypatch.setattr(main, "active_model", lambda: (model,meta))
    monkeypatch.setenv("PSET4_BACKEND","local")
    monkeypatch.setenv("PREDICTION_LOG", str(tmp_path/"predictions.jsonl"))
    response = TestClient(app).post("/predecir",json=READING)
    assert response.status_code == 200
    score = model.predict_proba(frame.iloc[[0]])[0,1]
    assert response.json()["probabilidad"] == pytest.approx(score)
    assert response.json()["decision"] == ("inspeccionar" if score>=model.threshold else "continuar")
