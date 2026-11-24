import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException

from api.esquemas import Reading
from src.datos import BASE, PROJECT
from src.pipeline import BusinessRule

app = FastAPI(title="AI4I - inspección de mantenimiento")
NAME = PROJECT + "-modelo"
ALIAS = "champion"
LOG = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def load_version(version):
    return mlflow.sklearn.load_model(f"models:/{NAME}/{version}")


def active_model():
    if os.getenv("FORCE_FALLBACK") != "1":
        try:
            version = mlflow.MlflowClient().get_model_version_by_alias(NAME, ALIAS)
            return load_version(version.version), {
                "nombre": NAME, "version": version.version, "alias": ALIAS,
                "run_id": version.run_id, "respaldo": False,
            }
        except Exception:
            LOG.exception("No se pudo cargar el alias; se activa la regla")
    return BusinessRule(), {
        "nombre": "regla_mantenimiento", "version": "regla-v1", "alias": None,
        "run_id": None, "respaldo": True,
    }


@app.get("/salud")
def health():
    _, metadata = active_model()
    return {"estado": "degradado" if metadata["respaldo"] else "ok",
            "modelo_cargado": not metadata["respaldo"]}


@app.get("/modelo")
def model():
    return active_model()[1]


@app.get("/monitoreo")
def monitoring():
    if os.getenv("PSET4_BACKEND","local") != "snowflake":
        raise HTTPException(503, "Monitoreo Snowflake no configurado")
    from monitoreo.snowflake_store import read_rows
    try:
        data = read_rows("monitoreo","alertas")
    except Exception as exc:
        LOG.exception("No se pudo consultar Snowflake")
        raise HTTPException(503, "Monitoreo no disponible") from exc
    latest = data["monitoreo"][-1] if data["monitoreo"] else None
    return {"ultimo_lote":latest, "alertas":data["alertas"]}


def record(event):
    if os.getenv("PSET4_BACKEND","local") == "snowflake":
        from monitoreo.snowflake_store import save
        try:
            save({"predicciones":[{**event,"origen":"api_pset4"}]})
        except Exception as exc:
            LOG.exception("No se pudo auditar la predicción en Snowflake")
            raise OSError("Registro de Snowflake falló") from exc
        return
    path = Path(os.getenv("PREDICTION_LOG", "artifacts/predicciones.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(event, allow_nan=False) + "\n").encode()
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        if os.write(fd, line) != len(line):
            raise OSError("Registro incompleto")
    finally:
        os.close(fd)


@app.post("/predecir")
def predict(reading: Reading):
    started = time.perf_counter()
    estimator, metadata = active_model()
    inputs = reading.model_dump()
    frame = pd.DataFrame([inputs], columns=BASE)
    probability = float(estimator.predict_proba(frame)[0, 1])
    decision = "inspeccionar" if probability >= getattr(estimator, "threshold", .5) else "continuar"
    response = {"id_prediccion": str(uuid4()), "probabilidad": None if metadata["respaldo"] else probability,
                "decision": decision, "version_modelo": metadata["version"],
                "run_id": metadata["run_id"], "respaldo": metadata["respaldo"]}
    try:
        record({**response, "timestamp": datetime.now(timezone.utc).isoformat(),
                "entradas": inputs, "latencia_ms": (time.perf_counter() - started) * 1000})
    except OSError as exc:
        raise HTTPException(503, "No se pudo registrar la predicción") from exc
    return response
