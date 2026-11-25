"""Aplica la decisión manual sobre el candidato registrado por src.reentrenar.

Promover mueve el alias champion a la versión candidata y guarda la versión
anterior para el rollback. Rechazar deja el alias sin cambios. En ambos casos
la decisión queda en etiquetas de la versión en MLflow y en docs/aprobacion.json.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import mlflow

from src.datos import PROJECT, dump

NAME = PROJECT + "-modelo"
CHAMPION = "champion"
CANDIDATE = "challenger"


def decidir(decision, version, responsable, comentario, client=None,
            registro="docs/reentrenamiento.json", salida="docs/aprobacion.json"):
    if decision not in ("promover", "rechazar"):
        raise ValueError("La decisión debe ser promover o rechazar")
    if not responsable.strip():
        raise ValueError("La aprobación requiere un responsable")
    client = client or mlflow.MlflowClient()
    ciclo = json.loads(Path(registro).read_text(encoding="utf-8"))
    version = str(version)
    if str(ciclo["version"]) != version:
        raise SystemExit(f"La versión {version} no corresponde al ciclo registrado ({ciclo['version']})")
    candidato = client.get_model_version_by_alias(NAME, CANDIDATE)
    if str(candidato.version) != version:
        raise SystemExit(f"El alias {CANDIDATE} apunta a la versión {candidato.version}, no a {version}")
    anterior = str(client.get_model_version_by_alias(NAME, CHAMPION).version)
    if decision == "promover" and not ciclo["califica"]:
        raise SystemExit("El candidato no cumple el criterio de promoción; registre la decisión como rechazar")
    if decision == "promover":
        client.set_registered_model_alias(NAME, CHAMPION, version)
    momento = datetime.now(timezone.utc).isoformat()
    for clave, valor in {"aprobacion": decision, "aprobacion_responsable": responsable,
                         "aprobacion_comentario": comentario, "aprobacion_fecha": momento}.items():
        client.set_model_version_tag(NAME, version, clave, valor)
    resultado = {"decision": decision, "version_candidata": version, "champion_anterior": anterior,
                 "champion_actual": version if decision == "promover" else anterior,
                 "responsable": responsable, "comentario": comentario, "fecha": momento,
                 "califica": ciclo["califica"], "disparador": ciclo.get("disparador")}
    dump(salida, resultado)
    print(json.dumps(resultado, ensure_ascii=False))
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", required=True, choices=["promover", "rechazar"])
    parser.add_argument("--version", required=True)
    parser.add_argument("--responsable", required=True)
    parser.add_argument("--comentario", default="")
    args = parser.parse_args()
    decidir(args.decision, args.version, args.responsable, args.comentario)


if __name__ == "__main__":
    main()
