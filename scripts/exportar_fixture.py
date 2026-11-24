"""Exporta el champion y el conjunto fijo para CI sin acceso a MLflow."""
import json
from pathlib import Path

import mlflow.sklearn
import pandas as pd
from mlflow.models import infer_signature

from src.datos import BASE, TARGET, split

root = Path("tests/fixtures")
root.mkdir(exist_ok=True)
selection = json.loads(Path("docs/seleccion.json").read_text(encoding="utf-8"))
reference = selection["models"][0]
_, holdout, _ = split()
model = mlflow.sklearn.load_model(f'models:/{selection["model_name"]}/{reference["version"]}')
mlflow.sklearn.save_model(model, str(root/"champion"), signature=infer_signature(
    holdout[BASE], model.predict(holdout[BASE])), input_example=holdout[BASE].head(3), code_paths=["src"])
holdout[BASE + [TARGET]].to_csv(root/"holdout.csv", index=False)
(root/"metricas.json").write_text(json.dumps(reference["test"], indent=2), encoding="utf-8")
pred = pd.read_csv("docs/predicciones.csv").merge(holdout[["reading_id", TARGET]], on="reading_id",
                                                  validate="one_to_one")
pred["fn"] = (pred[TARGET] == 1) & (pred.decision == "continuar")
pred["fp"] = (pred[TARGET] == 0) & (pred.decision == "inspeccionar")
pred.groupby("product_type").agg(lecturas=(TARGET,"size"), fallas=(TARGET,"sum"),
    falsas_alertas=("fp","sum"), fallas_omitidas=("fn","sum")).to_csv("docs/subgrupos.csv")
