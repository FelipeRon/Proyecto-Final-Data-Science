"""Entrena un candidato al cierre del sexto lote etiquetado."""
import json
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


def run():
    output = Path("docs/reentrenamiento.json")
    if output.exists():
        raise SystemExit("El ciclo ya está registrado. Use un workspace nuevo para repetir.")
    train, holdout, provenance = split()
    simulation = pd.read_csv("docs/predicciones.csv")
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
        mlflow.set_tag("phase", "reentrenamiento")
        mlflow.log_params({"snapshot": provenance["dataset_sha256"], "ultimo_lote": 6,
                           "version_base": version, "filas_entrenamiento": len(history)})
        mlflow.log_metrics({"mejora_coste_1000": paired.mean(), "dispersion_cv_costo": cv_std})
        model = mlflow.sklearn.log_model(challenger, "pipeline",
                    signature=infer_signature(x, challenger.predict(x)), input_example=x.head(3),
                    code_paths=["src"])
        registered = mlflow.register_model(model.model_uri, name)
        client = mlflow.MlflowClient()
        client.set_registered_model_alias(name, "candidato_pset4", registered.version)
        result = {"run_id": mlrun.info.run_id, "version": registered.version,
                  "disparador": "calendario al madurar 6 lotes", "filas_entrenamiento": len(history),
                  "champion_version": version, "mejora_media_costo": float(paired.mean()),
                  "dispersion_cv_costo": cv_std, "califica": eligible, "promovido": False,
                  "evaluacion": windows}
    dump(output, result)
    pd.DataFrame([{k: v for k, v in result.items() if k != "evaluacion"}]).to_csv(
        "docs/reentrenamientos.csv", index=False)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    run()
