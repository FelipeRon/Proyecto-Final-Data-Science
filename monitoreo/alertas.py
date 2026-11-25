"""Catálogo de alertas y regla de disparo del reentrenamiento.

Las reglas leen las filas de OBT.MONITOREO que escribe ``monitoreo.replay``. Kestra
ejecuta ``python -m monitoreo.alertas`` después de cada replay: imprime una línea
``ALERTA`` por evento y publica el resumen como salida del flujo, que decide si
registra un WARN y si lanza el reentrenamiento.

Regla de disparo (sección 7.1): la deriva de datos sola no reentrena.
- Deriva con impacto: un lote etiquetado con PSI > 0,25 y caída de AP.
- Deriva conceptual o degradación sostenida: caída de AP en 2 lotes etiquetados seguidos.
"""
import json
import os
import urllib.request

UMBRAL_PSI = .25
UMBRAL_TASA = .12
LOTES_CONSECUTIVOS = 2

# Plantilla de la sección 6.3. El piso de AP es la media de CV menos dos desviaciones
# del champion (0,8788 - 2 x 0,0260), el mismo que calcula el replay en ``caida_ap``.
REGLAS = [
    dict(id="psi", metrica="PSI por feature", umbral="> 0,25", ventana="1 lote",
         severidad="alta", responsable="Datos y Mantenimiento",
         accion="Revisar sensor y fuente. Reentrenar solo si además cae el desempeño."),
    dict(id="caida_ap", metrica="AP del lote etiquetado", umbral="< 0,827 (media CV - 2 DE)",
         ventana="1 lote etiquetado", severidad="media", responsable="Datos",
         accion="Revisar etiquetas y composición. Con PSI alto o en 2 lotes seguidos, reentrenar."),
    dict(id="tasa_inspeccion", metrica="Tasa de inspección", umbral="> 12 %", ventana="1 lote",
         severidad="alta", responsable="Mantenimiento",
         accion="Validar capacidad del turno. En 2 lotes seguidos, activar FORCE_FALLBACK."),
    dict(id="costo", metrica="Costo por 1.000 del modelo", umbral="> costo de la regla",
         ventana="2 lotes etiquetados seguidos", severidad="alta",
         responsable="Mantenimiento y Finanzas", accion="Activar FORCE_FALLBACK y revisar el modelo."),
]
POR_ID = {regla["id"]: regla for regla in REGLAS}


def _bool(value):
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "t", "yes")
    return bool(value)


def _ordenar(lotes):
    return sorted(lotes or [], key=lambda lote: int(lote["periodo"]))


def evaluar(lotes):
    """Devuelve un evento por regla incumplida en cada lote, en orden de período."""
    eventos, costo_alto = [], 0
    for lote in _ordenar(lotes):
        periodo = int(lote["periodo"])
        if lote.get("psi_max") is not None and float(lote["psi_max"]) > UMBRAL_PSI:
            eventos.append({"periodo": periodo, "regla": "psi", "valor": float(lote["psi_max"])})
        if _bool(lote.get("caida_ap")):
            eventos.append({"periodo": periodo, "regla": "caida_ap", "valor": float(lote["ap"])})
        if lote.get("alert_rate") is not None and float(lote["alert_rate"]) > UMBRAL_TASA:
            eventos.append({"periodo": periodo, "regla": "tasa_inspeccion",
                            "valor": float(lote["alert_rate"])})
        caro = (lote.get("cost_per_1000") is not None and lote.get("costo_regla") is not None
                and float(lote["cost_per_1000"]) > float(lote["costo_regla"]))
        costo_alto = costo_alto + 1 if caro else 0
        if costo_alto >= LOTES_CONSECUTIVOS:
            eventos.append({"periodo": periodo, "regla": "costo", "valor": float(lote["cost_per_1000"])})
    for evento in eventos:
        regla = POR_ID[evento["regla"]]
        evento.update(severidad=regla["severidad"], responsable=regla["responsable"],
                      accion=regla["accion"])
    return eventos


def debe_reentrenar(lotes, n=LOTES_CONSECUTIVOS):
    """Último evento que justifica reentrenar, o ``None`` si solo hay deriva sin impacto."""
    motivo, seguidos = None, 0
    for lote in _ordenar(lotes):
        caida = _bool(lote.get("caida_ap"))
        deriva = lote.get("psi_max") is not None and float(lote["psi_max"]) > UMBRAL_PSI
        seguidos = seguidos + 1 if caida else 0
        periodo = int(lote["periodo"])
        if deriva and caida:
            tipo = "deriva de datos con impacto"
        elif seguidos >= n:
            tipo = f"caída de AP en {n} lotes seguidos"
        else:
            continue
        motivo = {"periodo": periodo, "tipo": tipo, "psi_max": float(lote.get("psi_max") or 0),
                  "ap": float(lote["ap"]), "query_id": lote.get("query_id")}
    return motivo


def resumen(estado):
    lotes = estado.get("lotes") or ([estado["ultimo_lote"]] if estado.get("ultimo_lote") else [])
    eventos = evaluar(lotes)
    motivo = debe_reentrenar(lotes)
    firma = f'{motivo["query_id"]}/{motivo["periodo"]}/{motivo["tipo"]}' if motivo else None
    return {"lotes": len(lotes), "alertas": len(eventos), "eventos": eventos,
            "reentrenar": motivo is not None, "motivo": motivo, "firma": firma,
            "psi_max": max((float(l["psi_max"]) for l in lotes if l.get("psi_max") is not None),
                           default=None)}


def leer_api():
    api = os.environ["PSET4_API_URI"].rstrip("/")
    with urllib.request.urlopen(f"{api}/monitoreo", timeout=30) as response:
        return json.load(response)


def run():
    resultado = resumen(leer_api())
    for evento in resultado["eventos"]:
        print(f'ALERTA lote {evento["periodo"]} {evento["regla"]}={evento["valor"]:.4f} '
              f'severidad={evento["severidad"]} -> {evento["responsable"]}: {evento["accion"]}')
    print(json.dumps(resultado, ensure_ascii=False))
    salida = {k: resultado[k] for k in ("lotes", "alertas", "reentrenar", "firma", "psi_max")}
    salida["motivo"] = resultado["motivo"]["tipo"] if resultado["motivo"] else None
    salida["periodo"] = resultado["motivo"]["periodo"] if resultado["motivo"] else None
    salida["detalle"] = "; ".join(f'lote {e["periodo"]} {e["regla"]}' for e in resultado["eventos"])
    print("::" + json.dumps({"outputs": salida}) + "::")


if __name__ == "__main__":
    run()
