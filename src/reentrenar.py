"""Entrena un candidato al cierre del sexto lote etiquetado."""
import json
import os
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from src.datos import BASE, TARGET, split, dump
from src.metricas import choose_threshold, evaluate
from src.pipeline import DecisionModel


CHALLENGER = "challenger"
FILTRO = "tags.fase = 'reentrenamiento'"


def export_retraining_runs(path="docs/reentrenamientos.csv"):
    """Exporta con mlflow.search_runs las corridas con fase=reentrenamiento."""
    rows = mlflow.search_runs(search_all_experiments=True, filter_string=FILTRO, max_results=1000)
    rows.drop(columns=["artifact_uri"], errors="ignore").to_csv(path, index=False)
    return rows


def run():
    output = Path("docs/reentrenamiento.json")
    if output.exists():
        # Conserva la evidencia del ciclo anterior antes de registrar uno nuevo.
        previo = json.loads(output.read_text(encoding="utf-8"))
        archivo = Path("docs/historial_reentrenamiento") / f'v{previo["version"]}.json'
        archivo.parent.mkdir(exist_ok=True)
        if not archivo.exists():
            archivo.write_text(output.read_text(encoding="utf-8"), encoding="utf-8")
    if os.getenv("PSET4_BACKEND","local") == "snowflake":
        from monitoreo.snowflake_store import read_partition, read_rows
        spec = json.loads(Path("docs/split.json").read_text(encoding="utf-8"))
        train, holdout, provenance = read_partition(spec)
        simulation = pd.DataFrame(row for row in read_rows("predicciones")["predicciones"]
                                  if row.get("origen") == "replay_pset4")
        if len(simulation) != len(holdout) or not simulation.dataset_sha256.eq(provenance["dataset_sha256"]).all():
            raise ValueError("El replay de Snowflake no corresponde a la partición del modelo")
        # Snowflake devuelve las filas ordenadas por ID_PREDICCION (UUID). El orden de las
        # filas cambia los pliegues de la CV, así que se restituye el orden del replay.
        from monitoreo.replay import ordenar_simulacion
        simulation = ordenar_simulacion(simulation, holdout)
    else:
        train, holdout, provenance = split()
        simulation = pd.read_csv("docs/predicciones.csv")
    motivo = os.getenv("PSET4_DISPARADOR", "calendario al madurar 6 lotes")
    selection = json.loads(Path("docs/seleccion.json").read_text(encoding="utf-8"))
    name = selection["model_name"]
    version = selection["models"][0]["version"]
    champion = mlflow.sklearn.load_model(f"models:/{name}/{version}")
    labeled = simulation.merge(holdout[["reading_id", TARGET]], on="reading_id", validate="one_to_one")
    mature = labeled.loc[labeled.etiqueta_disponible_en <= 7, BASE + [TARGET]]
    history = pd.concat([train[BASE + [TARGET]], mature], ignore_index=True)
    x, y = history[BASE], history[TARGET]
    cv = StratifiedKFold(3, shuffle=True, random_state=42)
    pipeline = clone(champion.pipeline)
    oof = cross_val_predict(pipeline, x, y, cv=cv, method="predict_proba")[:, 1]
    threshold = choose_threshold(y, oof)
    challenger = DecisionModel(pipeline, threshold).fit(x, y)
    windows = []
    for period in (7, 8):
        part = labeled[labeled.periodo == period]
        old = evaluate(part[TARGET], champion.predict_proba(part[BASE])[:, 1], champion.threshold)
        new = evaluate(part[TARGET], challenger.predict_proba(part[BASE])[:, 1], threshold)
        windows.append({"periodo": period, "champion": old, "candidato": new,
                        "mejora_costo": old["cost_per_1000"] - new["cost_per_1000"]})
    paired = np.array([row["mejora_costo"] for row in windows])
    cv_cost = [evaluate(y.iloc[test], oof[test], threshold)["cost_per_1000"] for _, test in cv.split(x, y)]
    cv_std = float(np.std(cv_cost, ddof=1))
    eligible = bool(paired.mean() > cv_std and all(row["candidato"]["alert_rate"] <= .12 for row in windows))
    mlflow.set_experiment("ai4i-mantenimiento-pset4")
    with mlflow.start_run(run_name="reentrenamiento_lote_6") as mlrun:
        mlflow.set_tags({"fase": "reentrenamiento", "phase": "reentrenamiento", "disparador": motivo})
        mlflow.log_params({"snapshot": provenance["dataset_sha256"], "ultimo_lote": 6,
                           "version_base": version, "filas_entrenamiento": len(history)})
        mlflow.log_metrics({"mejora_coste_1000": paired.mean(), "dispersion_cv_costo": cv_std})
        model = mlflow.sklearn.log_model(challenger, "pipeline",
                    signature=infer_signature(x, challenger.predict(x)), input_example=x.head(3),
                    code_paths=["src"])
        registered = mlflow.register_model(model.model_uri, name)
        client = mlflow.MlflowClient()
        client.set_registered_model_alias(name, CHALLENGER, registered.version)
        result = {"run_id": mlrun.info.run_id, "version": registered.version,
                  "disparador": motivo, "filas_entrenamiento": len(history),
                  "champion_version": version, "mejora_media_costo": float(paired.mean()),
                  "dispersion_cv_costo": cv_std, "califica": eligible, "promovido": False,
                  "evaluacion": windows}
    dump(output, result)
    export_retraining_runs()
    print(json.dumps(result, ensure_ascii=False))
    resumen = {k: result[k] for k in ("run_id", "version", "champion_version", "califica",
                                       "mejora_media_costo", "dispersion_cv_costo")}
    print("::" + json.dumps({"outputs": resumen}) + "::")


if __name__ == "__main__":
    run()
