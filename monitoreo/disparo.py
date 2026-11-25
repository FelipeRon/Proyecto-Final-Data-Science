"""Decide si la deriva publicada justifica lanzar un reentrenamiento.

Kestra ejecuta este módulo después del monitoreo. Lee GET /monitoreo, toma el
mayor PSI entre el último lote y las alertas registradas y lo compara con el
umbral. El resultado se emite como salida de Kestra con la sintaxis
``::{"outputs": ...}::``.
"""
import json
import os
import urllib.request

UMBRAL_PSI = .25


def evaluar(estado, umbral=UMBRAL_PSI):
    """Devuelve el PSI más alto observado y si supera el umbral."""
    medidas = []
    ultimo = estado.get("ultimo_lote") or {}
    if ultimo.get("psi_max") is not None:
        medidas.append({"psi": float(ultimo["psi_max"]), "periodo": ultimo.get("periodo"),
                        "variable": None, "query_id": ultimo.get("query_id")})
    for alerta in estado.get("alertas") or []:
        if alerta.get("psi") is not None:
            medidas.append({"psi": float(alerta["psi"]), "periodo": alerta.get("periodo"),
                            "variable": alerta.get("variable"), "query_id": alerta.get("query_id")})
    if not medidas:
        return {"psi_max": None, "umbral": float(umbral), "supera_umbral": False,
                "periodo": None, "variable": None, "firma": None}
    peor = max(medidas, key=lambda medida: medida["psi"])
    # La firma identifica el evento de deriva para no reentrenar dos veces por la misma alerta.
    firma = f'{peor["query_id"]}/{peor["periodo"]}/{peor["variable"]}'
    return {"psi_max": peor["psi"], "umbral": float(umbral), "supera_umbral": peor["psi"] > umbral,
            "periodo": peor["periodo"], "variable": peor["variable"], "firma": firma}


def run():
    api = os.environ["PSET4_API_URI"].rstrip("/")
    umbral = float(os.getenv("UMBRAL_PSI", UMBRAL_PSI))
    with urllib.request.urlopen(f"{api}/monitoreo", timeout=30) as response:
        estado = json.load(response)
    resultado = evaluar(estado, umbral)
    print(json.dumps(resultado, ensure_ascii=False))
    print("::" + json.dumps({"outputs": resultado}) + "::")


if __name__ == "__main__":
    run()
