import json
import os
import time
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

import mlflow
import numpy as np
import pandas as pd

from monitoreo.deriva import compare
from src.datos import BASE, TARGET, split, dump
from src.metricas import evaluate
from src.pipeline import BusinessRule


def orden_replay(holdout):
    """Orden en que el replay recorre el holdout. Lo comparten el replay y el reentrenamiento."""
    return holdout.sort_values("reading_id").sample(frac=1, random_state=42)


def ordenar_simulacion(simulation, holdout):
    """Devuelve las predicciones en el orden del replay, sin depender de cómo se leyeron."""
    orden = orden_replay(holdout)["reading_id"].to_numpy()
    return simulation.set_index("reading_id").loc[orden].reset_index()


def run():
    backend = os.getenv('PSET4_BACKEND','local')
    if backend not in ('snowflake','local'):
        raise ValueError('PSET4_BACKEND debe ser snowflake o local')
    if backend == 'snowflake':
        from monitoreo.snowflake_store import read_partition
        spec = json.loads(Path('docs/split.json').read_text(encoding='utf-8'))
        train, holdout, metadata = read_partition(spec)
    else:
        train, holdout, metadata = split()
    selection = json.loads(Path("docs/seleccion.json").read_text(encoding="utf-8"))
    winner = selection["models"][0]
    model = mlflow.sklearn.load_model(f'models:/{selection["model_name"]}/{winner["version"]}')
    partitions = np.array_split(orden_replay(holdout).index.to_numpy(), 8)
    rows, alerts, predictions = [], [], []
    for number, indices in enumerate(partitions, 1):
        batch = holdout.loc[indices].copy()
        if number == 6:
            batch["torque_nm"] += 18
        features = batch[BASE]
        latency = []
        probabilities = []
        for index in features.index:
            started = time.perf_counter()
            probabilities.append(float(model.predict_proba(features.loc[[index]])[0, 1]))
            latency.append((time.perf_counter() - started) * 1000)
        decisions = np.asarray(probabilities) >= model.threshold
        for pos, (index, reading) in enumerate(features.iterrows()):
            reading_id = int(batch.loc[index, "reading_id"])
            predictions.append(dict(id_prediccion=str(uuid5(NAMESPACE_URL, f'{metadata["dataset_sha256"]}/{number}/{reading_id}')),
                periodo=number, etiqueta_disponible_en=number + 1, reading_id=reading_id, version_modelo=winner["version"],
                run_id=winner["final_run_id"], dataset_sha256=metadata["dataset_sha256"], probabilidad=probabilities[pos],
                decision="inspeccionar" if decisions[pos] else "continuar", latencia_ms=latency[pos], **reading.to_dict()))
        # El cálculo se atribuye al siguiente período simulado, cuando se libera la etiqueta.
        truth = batch[TARGET]
        observed = evaluate(truth, probabilities, model.threshold)
        reference = evaluate(truth, BusinessRule().predict(features), .5)
        drift = {name: compare(train[name], features[name], name == "product_type") for name in BASE}
        quality = {name: {"faltantes": float(features[name].isna().mean()),
                          "fuera_rango_o_nuevo": float((~features[name].isin(train[name].unique())).mean()) if name == "product_type"
                          else float(((features[name] < train[name].min()) | (features[name] > train[name].max())).mean())}
                   for name in BASE}
        triggered = [name for name, values in drift.items() if values["psi"] is not None and values["psi"] > .25]
        for name in triggered:
            alerts.append(dict(periodo=number, variable=name, psi=drift[name]["psi"],
                               severidad="alta", responsable="Datos y Mantenimiento"))
        rows.append(dict(periodo=number, etiqueta_disponible_en=number+1, n=len(batch),
                         p50_ms=float(np.median(latency)), p95_ms=float(np.percentile(latency, 95)),
                         prob_p10=float(np.percentile(probabilities, 10)), prob_p50=float(np.median(probabilities)),
                         prob_p90=float(np.percentile(probabilities, 90)), costo_regla=reference["cost_per_1000"],
                         costo_sin_inspeccion=float(truth.mean()*8000000), **observed,
                         psi_max=max(d["psi"] for d in drift.values()), deriva=bool(triggered),
                         caida_ap=observed["ap"] < winner["cv_ap_mean"]-2*winner["cv_ap_std"],
                         detalle=json.dumps({"deriva": drift, "calidad": quality})))
    if backend == 'snowflake':
        from monitoreo.snowflake_store import save
        for item in predictions + rows + alerts:
            item['origen'] = 'replay_pset4'
            item['query_id'] = metadata['query_id']
        save({'predicciones':predictions,'monitoreo':rows,'alertas':alerts},replace_alerts=True)
    print(json.dumps({'backend':backend,'source':metadata,'predictions':len(predictions),
                      'periods':len(rows),'alerts':len(alerts)}))
    pd.DataFrame(rows).to_csv("docs/monitoreo.csv", index=False)
    pd.DataFrame(alerts, columns=["periodo","variable","psi","severidad","responsable"]).to_csv("docs/alertas.csv", index=False)
    pd.DataFrame(predictions).to_csv("docs/predicciones.csv", index=False)
    dump("docs/replay.json", {"lotes": rows, "alertas": alerts, "origen": metadata, "modelo": winner["version"]})


if __name__ == "__main__":
    run()
