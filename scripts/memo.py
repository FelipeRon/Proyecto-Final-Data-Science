"""Genera docs/PSet4_memo_Ron_Andrade.pdf (documento técnico + anexos).

Las cifras se leen de los archivos de evidencia de docs/ para que el memo no se
desalinee del repositorio. Requiere reportlab y pypdf. Ejecutar desde la raíz:
python scripts/memo.py
"""
import json
from pathlib import Path

import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "PSet4_memo_Ron_Andrade.pdf"
AUTHOR = "Felipe Ron Andrade / Ciencia de Datos"
REPO = "https://github.com/FelipeRon/Proyecto-Final-Data-Science"
VIDEO_URL = "https://drive.google.com/file/d/18C2aJ86TmV3iDoHwG5BmqobG-oICIeeF/view?usp=sharing"
VIDEO = f'Video de demostración: <link href="{VIDEO_URL}" color="#245C79"><u>{VIDEO_URL}</u></link>.'

# Formato heredado del memo del PSet 3 (scripts/build_report.py de PSET-3): estilos base de
# reportlab en negro, tablas con encabezado azul claro y pie de página simple.
TEAL = colors.HexColor("#245C79")
INK = colors.black
MUTED = colors.HexColor("#555555")
RULE = colors.HexColor("#D9D9D9")
HEAD = colors.HexColor("#DAE5ED")
ZEBRA = colors.HexColor("#F2F5F7")
RUST = colors.HexColor("#9a3412")
DOC_TITLE = "Detección de falla actual con AI4I en operación"
SUBTITLE = "PSet 4 | Felipe Ron Andrade | 26 de noviembre de 2026"
MARGINS = dict(leftMargin=52, rightMargin=52, topMargin=38, bottomMargin=40)

_base = getSampleStyleSheet()
for _name in ["Title", "Heading1", "Heading2"]:
    _base[_name].textColor = colors.black
_base["Title"].fontSize, _base["Title"].leading = 20, 24
_base["Heading1"].fontSize, _base["Heading1"].leading = 15, 18
_base["Heading2"].fontSize, _base["Heading2"].leading = 11, 14

S = {
    "doctitle": _base["Title"],
    "title": _base["Heading1"],
    "h": _base["Heading2"],
    "lede": ParagraphStyle("lede", fontName="Helvetica", fontSize=9.3, leading=12.5, spaceAfter=7),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.3, leading=12.5, alignment=TA_LEFT,
                           spaceAfter=7),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=7.5, leading=10),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica", fontSize=7.5, leading=10),
    "note": ParagraphStyle("note", fontName="Helvetica", fontSize=7.5, leading=10, spaceAfter=5),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=7.5, leading=10,
                           backColor=colors.HexColor("#F2F5F7"), borderPadding=5, spaceBefore=3,
                           spaceAfter=7),
}

state = {"total": 0, "sec": 0}


def usd(value):
    return f"{value:,.0f}".replace(",", ".")


def dec(value, digits=3):
    return f"{value:.{digits}f}".replace(".", ",")


def pct(value, digits=1):
    return f"{100 * value:.{digits}f}".replace(".", ",") + " %"


def page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 43, 23, f"Felipe Ron Andrade | PSet 4 | {doc.page}")
    canvas.restoreState()


def p(text, style="body"):
    if style == "title":
        if text.startswith("Anexo"):
            return Paragraph(text.replace(" · ", " "), S["title"])
        state["sec"] += 1
        if state["sec"] == 1:  # como en el PSet 3: título del documento y la sección 1 bajo él
            return Paragraph(f"1 {text}", S["h"])
        text = f"{state['sec']} {text}"
    return Paragraph(text, S[style])


def section(title, lede, blocks):
    flow = [p(title, "title"), p(lede, "lede")]
    for heading, body in blocks:
        part = [p(heading, "h")] + ([p(body)] if isinstance(body, str) else body)
        flow.append(KeepTogether(part))
    flow.append(PageBreak())
    return flow


def table(rows, widths, header=True, zebra=True):
    data = [[p(str(c), "cellh" if header and i == 0 else "cell") for c in row]
            for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), .4, RULE),
             ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), HEAD))
    if zebra:
        for r in range(2 if header else 1, len(rows), 2):
            style.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
    t.setStyle(TableStyle(style))
    return t


def picture(path, width):
    img = Image(str(path))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = width, width * ratio
    return img


def cost_chart(mon, marks):
    d = Drawing(170 * mm, 62 * mm)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 12 * mm, 10 * mm, 152 * mm, 46 * mm
    series = [list(zip(mon.periodo, mon.cost_per_1000 / 1000)), list(zip(mon.periodo, mon.costo_regla / 1000)),
              list(zip(mon.periodo, mon.costo_sin_inspeccion / 1000))]
    lp.data = series
    for i, color in enumerate([TEAL, RUST, colors.HexColor("#9aa5b1")]):
        lp.lines[i].strokeColor = color
        lp.lines[i].strokeWidth = 1.6
        lp.lines[i].symbol = makeMarker("FilledCircle", size=3, fillColor=color, strokeColor=color)
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = 1, 8
    lp.xValueAxis.valueSteps = list(range(1, 9))
    lp.yValueAxis.valueMin, lp.yValueAxis.valueMax, lp.yValueAxis.valueStep = 0, 450, 100
    for axis in (lp.xValueAxis, lp.yValueAxis):
        axis.labels.fontName, axis.labels.fontSize = "Helvetica", 7
        axis.labels.fillColor = MUTED
        axis.strokeColor = RULE
    lp.yValueAxis.visibleGrid = True
    lp.yValueAxis.gridStrokeColor = RULE
    d.add(lp)
    for periodo, label in marks:
        x = lp.x + (periodo - 1) / 7 * lp.width
        d.add(Line(x, lp.y, x, lp.y + lp.height, strokeColor=RUST, strokeDashArray=[2, 2], strokeWidth=.7))
        d.add(String(x + 2, lp.y + lp.height - 6, label, fontName="Helvetica", fontSize=6.5, fillColor=RUST))
    legend = [("Modelo", TEAL), ("Regla experta", RUST), ("Sin inspección", colors.HexColor("#9aa5b1"))]
    for i, (name, color) in enumerate(legend):
        d.add(String(lp.x + i * 28 * mm, 2 * mm, name, fontName="Helvetica", fontSize=7, fillColor=color))
    d.add(String(lp.x + lp.width, 2 * mm, "Miles de USD por 1.000 lecturas", fontName="Helvetica",
                 fontSize=7, fillColor=MUTED, textAnchor="end"))
    return d


def build_story():
    mon = pd.read_csv(DOCS / "monitoreo.csv")
    alerts = pd.read_csv(DOCS / "alertas.csv")
    sub = pd.read_csv(DOCS / "subgrupos.csv")
    cycle = json.loads((DOCS / "reentrenamiento.json").read_text(encoding="utf-8"))
    sel = json.loads((DOCS / "seleccion.json").read_text(encoding="utf-8"))["models"][0]
    champion_run = "d07d9f7f061848138579716948af2c6f"
    threshold = sel["threshold"]
    floor = sel["cv_ap_mean"] - 2 * sel["cv_ap_std"]
    controls = mon[mon.periodo != 6]
    model_mean, rule_mean, none_mean = mon.cost_per_1000.mean(), mon.costo_regla.mean(), mon.costo_sin_inspeccion.mean()
    saving = rule_mean - model_mean
    lote6 = mon[mon.periodo == 6].iloc[0]
    lote8 = mon[mon.periodo == 8].iloc[0]
    W = A4[0] - 104
    story = [p(DOC_TITLE, "doctitle"), p(SUBTITLE)]

    story += section("La decisión de mantenimiento",
        "Detección de falla actual por lectura de AI4I. El servicio recomienda una inspección y el equipo "
        "de mantenimiento decide cómo actuar.", [
        ("Video de demostración",
         f'Recorrido de la infraestructura local en funcionamiento (Compose, Kestra, MLflow, API, tablero, replay, '
         f'alertas, aprobación, rollback y respaldo): <link href="{VIDEO_URL}" color="#245C79"><u>{VIDEO_URL}</u></link>'),
        ("Unidad, objetivo y horizonte",
         "Una observación es una lectura con sensores y tipo de producto. El target binario es machine_failure "
         "y la predicción corresponde al estado de la lectura actual: el horizonte es el turno en curso. AI4I es "
         "sintético y no tiene marcas temporales de operación ni recorridos por máquina."),
        ("Política de decisión",
         f"La versión 1 inspecciona si la probabilidad alcanza el umbral {dec(threshold, 5)}, elegido en PSET-3 con "
         "predicciones fuera de fold y un tope de 12 % de alertas. Debajo del umbral recomienda continuar. El "
         "supervisor confirma con evidencia de planta y puede anular la recomendación. La línea base y regla de "
         "respaldo inspecciona con desgaste ≥200 min o torque ≥60 Nm."),
        ("Métricas técnica y de negocio",
         "Average Precision (AP) orienta la selección por el desbalance (3,4 % de fallas). El costo por 1.000 "
         "lecturas combina USD 500 por inspección, USD 8.000 por falla omitida y USD 1.500 de costo residual por "
         "falla inspeccionada. Son supuestos a revisar con mantenimiento y finanzas."),
        ("Patrón de despliegue: batch",
         "La decisión es una lista de inspección por turno, así que no exige respuesta por lectura. El piloto "
         "agrupa lecturas cada 15 minutos y publica la lista dentro de 5 minutos del cierre, con una espera máxima "
         "de 20 minutos. Supuesto del piloto: 50 equipos con una lectura por minuto generan unas 72.000 "
         "predicciones diarias (96 lotes de 750), que un lote resuelve en segundos. El costo de actuar con una predicción de 20 "
         "minutos es bajo para fallas por desgaste o sobrecarga, que evolucionan en horas, pero alto para una "
         "falla súbita: por eso las alarmas de seguridad siguen por una vía independiente."),
        ("Qué haría adecuado el patrón online",
         "Si la decisión pasara a detener una máquina en el momento (por ejemplo, cortar la carga ante torque "
         "anómalo), el horizonte sería de segundos y la API, que ya existe, tendría que operar en línea con un "
         "objetivo de latencia validado y una política para lecturas antiguas. Los ocho lotes del replay son una "
         "carga de prueba, no un volumen real."),
    ])

    story += [p("Arquitectura de extremo a extremo", "title"),
              p("La versión del registro y el hash del snapshot conectan cada decisión operativa con los datos que "
                "la originaron.", "lede"),
              picture(DOCS / "arquitectura.png", W), Spacer(1, 6)]
    story += [KeepTogether([p(h, "h"), p(b)]) for h, b in [
        ("Flujo", "Kestra ingiere el CSV de UCI a Snowflake RAW, dbt construye Bronze, Silver y Gold, y Spark une "
         "hecho y dimensión en PSET2.OBT.OBT_READINGS. Los notebooks de PSET-3 entrenan desde el snapshot de la "
         "OBT y registran el modelo en MLflow. La API resuelve el alias champion. produccion_lotes.yml puntúa ocho "
         "lotes y escribe PREDICCIONES y MONITOREO; monitoreo.yml calcula las alertas y, si hay deriva con impacto, "
         "lanza reentrenamiento.yml, que se detiene hasta la decisión humana."),
        ("Despliegue continuo", "ci.yml construye la imagen y ejecuta pytest en cada push y pull request. cd.yml, en "
         "cada merge a main, repite las pruebas y publica la imagen en GHCR con el hash del commit y latest; "
         "docker-compose.yml sirve la API desde esa imagen. El modelo no se despliega con el código: lo cambia el "
         "alias, con aprobación."),
    ]]
    story.append(PageBreak())

    story += [p("Datos y calidad", "title"),
              p("La OBT conserva una lectura por identificador y mantiene la procedencia del snapshot.", "lede")]
    story += [KeepTogether([p(h, "h"), p(b)]) for h, b in [
        ("Ingesta, retries y backfill", "La descarga oficial usa reintentos acotados (3 intentos con espera "
         "exponencial en Kestra) y admite un CSV local como respaldo. La carga RAW guarda el SHA-256 del archivo y "
         "reemplaza transaccionalmente las filas del mismo hash al repetir, así que un reintento no duplica. Un CSV "
         "histórico puede pasarse como entrada para backfill."),
        ("Calidad", "Silver tipa, valida rangos físicos y aparta los registros no conformes en int_quarantine; las "
         "pruebas dbt exigen conservación de conteos, contrato físico y cuarentena vacía. En el snapshot no hubo "
         "registros en cuarentena, por lo que no se descartaron lecturas."),
        ("Capas, estrella y OBT", "Gold materializa fct_reading (grano: una lectura del snapshot activo) y "
         "dim_product_type (una fila por tipo L, M, H). Spark une hecho y dimensión y valida que el conteo se "
         "conserve, que reading_id sea único y que no haya huérfanos. La ejecución de PSET-02 registró 10.000 filas "
         "RAW, 20 pasos dbt correctos y 10.000 filas únicas en la OBT; el snapshot tiene 339 fallas."),
        ("Reconstrucción desde la fuente", "El 25-nov-2026 la ejecución de Kestra 99H6JjyhD01y2Obgen4gX construyó "
         "todo en una base vacía (PSET2_VERIF): descargó UCI al primer intento, cargó 10.000 filas en RAW, dbt pasó "
         "20 de 20 y Spark validó el join. El hash canónico de la OBT reconstruida coincide con el del snapshot de "
         "entrenamiento, así que la cadena desde la fuente reproduce exactamente los datos del modelo."),
        ("Batch frente a streaming", "La ingesta histórica es batch porque la fuente es un archivo estático. En "
         "planta, la telemetría llegaría continua y el patrón batch de 15 minutos seguiría siendo suficiente."),
    ]]
    story += [Spacer(1, 4), picture(DOCS / "modelo_dimensional.png", W * .78), PageBreak()]

    story += section("Cómo se seleccionó el modelo",
        "La selección se congeló con validación cruzada antes de abrir el holdout.", [
        ("EDA que cambió el experimento", "Con 3,39 % de fallas en train se eligió AP y validación estratificada; "
         "accuracy no decide. La correlación de Spearman con la falla fue 0,17 para torque, −0,16 para velocidad, "
         "0,10 para desgaste y −0,10 para la diferencia térmica, lo que llevó a derivar diferencia térmica y potencia "
         "en el pipeline. Las colas de velocidad y torque son físicamente posibles y se conservaron."),
        ("Features y fuga", "Seis entradas: cinco numéricas y el tipo de producto. Se excluyen identificadores, "
         "target, subtipos de falla (TWF, HDF, PWF, OSF, RNF) y campos de auditoría. La prueba de fuga verifica que "
         "agregar etiquetas o identificadores no cambie las features, y el contrato de la API rechaza esos campos."),
        ("Validación", "Split estratificado 80/20 y tres folds fijos con semilla 42. Dos líneas base y cinco "
         "familias. 30 configuraciones aleatorias por cada una de las tres familias priorizadas."),
        ("Resultados", "Dummy y regla obtuvieron AP de CV 0,034 y 0,135. HistGradientBoosting obtuvo AP de CV "
         f"{dec(sel['cv_ap_mean'])} ± {dec(sel['cv_ap_std'])} y AP de prueba 0,910; Random Forest, segundo finalista, "
         f"0,893. TabPFN y ChatGPT se evaluaron como protocolos suplementarios. Champion: versión 1, run_id "
         f"{champion_run}."),
    ])

    story += section("Servicio y pruebas",
        "La API carga el modelo por alias y registra cada predicción en Snowflake antes de responder.", [
        ("Contrato FastAPI", "GET /salud informa si el modelo cargó. GET /modelo devuelve nombre, versión, alias y "
         "run_id. POST /predecir valida con Pydantic estricto (tipo L, M o H; temperaturas, velocidad y torque "
         "positivos; desgaste no negativo; sin campos extra) y devuelve 422 con el campo inválido. Cada predicción "
         "queda en OBT.PREDICCIONES con id, timestamp, entradas, salida, versión, run_id y latencia."),
        ("Ejemplo", [p('{"product_type":"L","air_temperature_k":300,"process_temperature_k":310,'
                       '"rotational_speed_rpm":1500,"torque_nm":40,"tool_wear_min":100}<br/>'
                       '→ {"probabilidad":0.000284,"decision":"continuar","version_modelo":"1",'
                       '"run_id":"d07d9f7f…","respaldo":false,"id_prediccion":"…"}', "code"),
                     p("Con product_type X, la API responde 422 indicando product_type.")]),
        ("Qué cubren las pruebas (30, en verde en CI)", [table([
            ["Tipo", "Archivo", "Qué verifica"],
            ["Contrato", "test_contrato.py, test_contrato_pset3.py", "200 con el esquema; 422 por campo faltante, tipo incorrecto, categoría desconocida y campos de etiqueta"],
            ["Modelo", "test_modelo.py", "El fixture exportado con save_model reproduce AP y costo registrados (tolerancia 1e-12 por redondeo)"],
            ["Negocio", "test_comportamiento.py", "+100 min de desgaste o +20 Nm de torque suben riesgo y tasa de inspección; sobrecarga evidente se inspecciona"],
            ["Respaldo", "test_comportamiento.py, test_contrato.py", "Registro caído o FORCE_FALLBACK=1: responde la regla e indica respaldo"],
            ["Operación", "test_disparo.py, test_pipeline.py", "Reglas de alerta y reentrenamiento, promoción y rechazo, features físicas"],
        ], [22 * mm, 52 * mm, W - 74 * mm])]),
        ("Fuera de CI", "Snowflake, Kestra y el MLflow en vivo no están disponibles en GitHub Actions: CI usa el "
         "modelo exportado en tests/fixtures/ y el registro local de predicciones. La integración con Snowflake se "
         "verificó a mano (docs/verificacion_reproducibilidad.md)."),
    ])

    story += [p("CI/CD y versionado", "title"),
              p("El código se despliega solo; el modelo cambia únicamente con aprobación.", "lede")]
    story += [KeepTogether([p("GitHub Actions", "h"), table([
        ["Workflow", "Commit", "Resultado", "Ejecución"],
        ["CI (build + pytest)", "aea76a4", "success", f'<link href="{REPO}/actions/runs/45639441461">runs/45639441461</link>'],
        ["CD (pruebas + GHCR)", "aea76a4", "success", f'<link href="{REPO}/actions/runs/45639441600">runs/45639441600</link>'],
        ["CD (pruebas + GHCR)", "ae65fb5", "success", f'<link href="{REPO}/actions/runs/45469538637">runs/45469538637</link>'],
    ], [42 * mm, 25 * mm, 22 * mm, W - 89 * mm]),
        p("Imagen publicada: ghcr.io/feliperon/proyecto-final-data-science:&lt;sha&gt; (y :latest). Estado leído de "
          "la API de GitHub Actions el 25-nov-2026.", "note")])]
    story += [KeepTogether([p(h, "h"), p(b)]) for h, b in [
        ("Regla de promoción", "El challenger reemplaza al champion si, en los mismos lotes etiquetados que ninguno "
         "vio (7 y 8), reduce el costo medio por 1.000 lecturas en más de una desviación estándar del costo de CV "
         "y mantiene la tasa de inspección ≤12 % en ambos lotes. Aun cumpliéndola, una persona aprueba."),
        ("Rollback", "La API consulta el alias en cada solicitud y solo guarda en caché el estimador por versión. "
         "En el clon de verificación, mover champion de 1 a 2 y de vuelta a 1 cambió GET /modelo en cada paso sin "
         "reconstruir la imagen."),
        ("Trazabilidad", "Cada fila de PREDICCIONES guarda versión, run_id, hash del snapshot y Query ID de "
         "Snowflake. El run de MLflow remite al snapshot de la OBT, que se construye desde fct_reading y "
         "dim_product_type."),
        ("Por qué el modelo no se promueve automáticamente", "Un candidato puede ganar en costo por un cambio de "
         "sensor o por pocas fallas en dos lotes de 250 lecturas, y su umbral cambia la carga de inspección. Ese "
         "cambio afecta la capacidad de un turno, así que lo decide mantenimiento, no el pipeline."),
    ]]
    story.append(PageBreak())

    alert_rows = [["Métrica", "Umbral", "Ventana", "Severidad", "Quién la recibe", "Acción"],
                  ["PSI por feature", "> 0,25", "1 lote", "Alta", "Datos y Mantenimiento", "Revisar sensor y fuente; reentrenar solo si cae el desempeño"],
                  ["AP del lote", f"< {dec(floor)} (CV − 2 DE)", "1 lote etiquetado", "Media", "Datos", "Revisar etiquetas; con PSI alto o 2 lotes seguidos, reentrenar"],
                  ["Tasa de inspección", "> 12 %", "1 lote", "Alta", "Mantenimiento", "Validar capacidad; 2 lotes seguidos → respaldo"],
                  ["Costo modelo", "> costo regla", "2 lotes seguidos", "Alta", "Mantenimiento y Finanzas", "Activar FORCE_FALLBACK"]]
    story += [p("Simulación, monitoreo y alertas", "title"),
              p("2.000 lecturas del holdout en ocho lotes de 250. La etiqueta de cada lote llega en el período "
                "siguiente.", "lede")]
    story += [KeepTogether([p(h, "h"), p(b)]) for h, b in [
        ("Lotes y deriva inducida", "AI4I no es cronológico: los lotes son una permutación reproducible (semilla 42) "
         "del holdout. Ordenar por UDI generó alertas en todos los lotes por concentración de temperaturas, así que se "
         "conserva solo como análisis de sensibilidad. En el lote 6 se sumaron exactamente 18 Nm al torque y se "
         "conservaron las etiquetas."),
        ("Métricas por lote", "Sistema: volumen, latencia p50 y p95 de scoring (el replay no pasa por HTTP, así que "
         "las tasas 4xx/5xx se miden en la API, no en el replay). Modelo: percentiles de probabilidad, tasa de "
         "inspección, AP y costo cuando llega la etiqueta. Datos: faltantes, valores fuera del rango de "
         "entrenamiento y categorías nuevas. Deriva: PSI por feature (decide), KS y chi-cuadrado (respaldo)."),
        ("Umbral de PSI", f"0,25 es el corte habitual de cambio fuerte. En el replay, los siete lotes de control "
         f"llegaron a un PSI máximo de {dec(controls.psi_max.max())} y el lote 6 a {dec(lote6.psi_max, 2)}, así que "
         "no hubo falsas alarmas de deriva."),
    ]]
    story += [KeepTogether([p("Plantilla de alertas (monitoreo/alertas.py)", "h"),
                            table(alert_rows, [24 * mm, 25 * mm, 20 * mm, 15 * mm, 30 * mm, W - 114 * mm])])]
    story.append(PageBreak())
    story += [p("Diagnóstico de deriva", "title"),
              p("La deriva de entradas sin caída de desempeño se revisa, pero no reentrena.", "lede"),
              table([["Entradas", "Desempeño", "Diagnóstico", "Acción", "En el replay"],
                     ["Cambian", "Se mantiene", "Deriva sin impacto", "Alerta PSI y revisión del sensor; no se reentrena", "No ocurrió"],
                     ["Cambian", "Cae", "Deriva con impacto", "Revisar la fuente, reentrenar y comparar con aprobación", f"Lote 6: PSI {dec(lote6.psi_max, 2)}, AP {dec(lote6.ap)}"],
                     ["Estables", "Cae", "Deriva conceptual", "Revisar etiquetas; reentrenar si se repite", f"Lote 8: AP {dec(lote8.ap)}, una vez"]],
                    [20 * mm, 22 * mm, 30 * mm, W - 112 * mm, 40 * mm]),
              p("Deriva conceptual: AP del lote frente a la media de CV menos dos desviaciones "
                f"({dec(floor)}). Una prueba controlada que conservó sensores y prevalencia pero alteró la relación "
                "entrada/etiqueta bajó AP de 0,940 a 0,022, y el notebook 07 la separa de la deriva de entradas.", "note")]
    story += [KeepTogether([p(h, "h"), p(b)]) for h, b in [
        ("Alertas disparadas", f"Lote 6: PSI de torque {dec(alerts.psi.max(), 2)}, AP bajo el piso y tasa de "
         f"inspección de {pct(lote6.alert_rate)}; disparó el reentrenamiento. Lote 8: caída aislada de AP sin "
         "deriva de entradas; quedó como alerta de revisión. Los lotes 1 a 5 y 7 no generaron alertas."),
        ("Kestra y tablero", "monitoreo.yml corre al terminar cada replay, escribe cada alerta como WARN en el log "
         "de Kestra y guarda la firma del evento para no reentrenar dos veces por la misma alerta. El tablero "
         "Streamlit muestra por lote las métricas de sistema, modelo, negocio y deriva, con líneas que marcan los "
         "lotes con alertas y el reentrenamiento."),
    ]]
    story.append(PageBreak())

    windows = cycle["evaluacion"]
    story += [p("Reentrenamiento", "title"),
              p("El ciclo sobre el lote con deriva produjo un challenger que no superó al champion.", "lede")]
    story += [KeepTogether([p(h, "h"), p(b)]) for h, b in [
        ("Disparador", "Por desempeño: deriva con impacto (PSI > 0,25 y AP bajo el piso en el mismo lote) o AP bajo "
         "el piso en dos lotes etiquetados seguidos. Por calendario: cada seis lotes etiquetados, aunque no haya "
         "alertas. La deriva sin caída no dispara. El ciclo documentado se ejecutó al madurar el lote 6, que "
         "coincide con la deriva con impacto."),
        ("Ventana", "Todo el histórico disponible: el train original más los lotes 1 a 6, cuyo target ya llegó. Con "
         "1.500 lecturas nuevas frente a 8.000 de train, una ventana móvil descartaría casi todas las fallas."),
        ("Tubería (reentrenamiento.yml)", "Reentrena con src/pipeline.py y los hiperparámetros del champion, sin "
         "tuning; registra la corrida con fase=reentrenamiento y el motivo, y la versión con el alias challenger. "
         "Evalúa ambos modelos en los lotes 7 y 8, aplica la regla de promoción y se pausa. El responsable reanuda "
         "con promover o rechazar; promover mueve champion, rechazar lo deja y registra el motivo en MLflow. Sin "
         "respuesta en 72 horas, la ejecución se cancela."),
    ]]
    story += [KeepTogether([p("Evidencia del ciclo", "h"), table([
        ["Lote", "Costo champion", "Costo challenger", "Diferencia", "Tasa challenger"],
        *[[w["periodo"], usd(w["champion"]["cost_per_1000"]), usd(w["candidato"]["cost_per_1000"]),
           usd(w["mejora_costo"]), pct(w["candidato"]["alert_rate"])] for w in windows],
    ], [20 * mm, 35 * mm, 35 * mm, 30 * mm, 30 * mm]),
        p(f"Challenger versión {cycle['version']}, run {cycle['run_id']}. Mejora media "
          f"{usd(cycle['mejora_media_costo'])} USD frente a un umbral de {usd(cycle['dispersion_cv_costo'])} USD "
          "(una desviación del costo de CV): no califica, se rechaza y champion sigue en la versión 1.", "note")])]
    story.append(PageBreak())

    sub = sub.assign(recall=lambda d: (d.fallas - d.fallas_omitidas) / d.fallas,
                     tasa=lambda d: (d.fallas - d.fallas_omitidas + d.falsas_alertas) / d.lecturas)
    story += [p("Ética, errores y retirada", "title"),
              p("La recomendación cambia la carga del equipo y la probabilidad de que una falla quede sin "
                "inspección.", "lede"),
              KeepTogether([p("Desempeño por tipo de producto", "h"), table(
                  [["Tipo", "Lecturas", "Fallas", "Recall", "Fallas omitidas", "Falsas alertas", "Tasa de inspección"]] +
                  [[r.product_type, usd(r.lecturas), r.fallas, pct(r.recall, 0), r.fallas_omitidas,
                    r.falsas_alertas, pct(r.tasa)] for r in sub.itertuples()],
                  [16 * mm, 22 * mm, 18 * mm, 18 * mm, 26 * mm, 26 * mm, W - 126 * mm]),
                  p("Incluye el lote alterado. H tiene solo 5 fallas: no permite concluir que el modelo sea mejor en "
                    "H.", "note")])]
    story += [KeepTogether([p(h, "h"), p(b)]) for h, b in [
        ("¿Es aceptable la diferencia?", "El recall de L y M (92 % y 88 %) y sus tasas de inspección (11,6 % y "
         "13,0 %) son parecidos; M recibe algo más de inspecciones por tener más fallas. Para el negocio la "
         "diferencia es aceptable. Para las personas afectadas, los operarios de L y M asumen el mismo riesgo "
         "residual de 3 fallas omitidas cada uno, así que el control por tipo se mantiene en el piloto."),
        ("Quién asume cada error", "Un falso positivo lo asume el técnico de mantenimiento: tiempo de inspección y "
         "tareas postergadas. Un falso negativo lo asume producción: paro no planificado, mantenimiento de "
         "emergencia y riesgo para el operario de la máquina."),
        ("Criterios de retirada", "1) Tasa de inspección > 12 % en dos lotes seguidos: FORCE_FALLBACK durante el "
         "siguiente lote. 2) Costo del modelo > costo de la regla en dos lotes etiquetados seguidos, aun después de "
         "reentrenar: respaldo y revisión del modelo. 3) Pérdida de trazabilidad o falla del registro de "
         "predicciones: se suspenden las decisiones del modelo. 4) PSI > 0,25 sin resolver al cierre del turno: "
         "supervisión humana de todas las alertas."),
        ("Interruptor de respaldo", "FORCE_FALLBACK=1 hace que la API use la regla (desgaste ≥200 o torque ≥60) e "
         "indique respaldo=true y version_modelo=regla-v1. Las pruebas lo verifican con el interruptor y con el "
         "registro caído, y se comprobó con la API en Docker."),
        ("Supervisión humana", "Se mantiene el juicio del PSET-1: el supervisor confirma cada alerta. Se ajusta en "
         "un punto: cuando la tasa de inspección supera 12 % (como en el lote 6, 62,4 %), el supervisor no confirma "
         "una a una, sino que activa la revisión del sensor y prioriza con la regla."),
    ]]
    story.append(PageBreak())

    rows = [["Lote", "Modelo", "Regla experta", "Sin inspección", "Evento"]]
    for r in mon.itertuples():
        event = {6: "Deriva con impacto y reentrenamiento (rechazado)", 8: "Caída aislada de AP"}.get(r.periodo, "")
        rows.append([r.periodo, usd(r.cost_per_1000), usd(r.costo_regla), usd(r.costo_sin_inspeccion), event])
    rows.append(["Media", usd(model_mean), usd(rule_mean), usd(none_mean), ""])
    story += [p("Resultado de negocio", "title"),
              p(f"El modelo redujo el costo simulado medio en USD {usd(saving)} por 1.000 lecturas frente a la "
                f"regla experta ({pct(saving / rule_mean)}).", "lede"),
              table(rows, [16 * mm, 28 * mm, 28 * mm, 28 * mm, W - 100 * mm]),
              p("Costo simulado en USD por 1.000 lecturas; cada lote pesa lo mismo.", "note"), Spacer(1, 6),
              cost_chart(mon, [(6, "Reentrenamiento")])]
    story += [KeepTogether([p("¿Valió la pena actuar según la predicción?", "h"), p(
        "Sí, en la simulación: el modelo superó a la regla en siete de ocho lotes y a no inspeccionar en todos "
        "salvo el lote 6. En ese lote el cambio de torque disparó las inspecciones y el modelo costó más que la "
        "regla; el reentrenamiento no mejoró el costo, así que el champion siguió puntuando. El ahorro depende de "
        "costos supuestos y de un dataset sintético: se recomienda ajustar y escalar a un piloto, no desplegar en "
        "producción.")])]
    story.append(PageBreak())

    story += section("Limitaciones y próximos pasos",
        "La evidencia respalda un piloto supervisado con datos reales y criterios de parada acordados.", [
        ("Alcance de la evidencia", "El holdout reutilizado permite comparar políticas en el mismo escenario, pero no "
         "es un flujo externo. El cambio de torque es artificial y los costos son supuestos. El replay no mide tasas "
         "HTTP 4xx/5xx porque puntúa en lote."),
        ("Lo que no se pudo resolver", "El replay usa el holdout permutado, no datos posteriores al corte, y "
         "produccion_lotes.yml procesa los ocho lotes en una sola tarea en vez de una ejecución por período. No "
         "hay tráfico HTTP real para medir errores en producción."),
        ("Qué haríamos primero", "Pedir telemetría y etiquetas con fecha, costos de inspección y paro, y capacidad "
         "por turno; correr el modelo en paralelo a la regla y comparar costo y fallas por tipo de producto antes "
         "de decidir si se escala."),
        ("Reproducción y video", f"README.md describe el orden completo. Evidencia: docs/predicciones.csv, "
         f"monitoreo.csv, alertas.csv, corridas.csv y reentrenamientos.csv. {VIDEO}"),
        ("Anexos", "A continuación: docs/cambios.md y los memos de PSET-1 (memo y pitch), PSET-2 y PSET-3."),
    ])
    return story


def cambios_story():
    text = (DOCS / "cambios.md").read_text(encoding="utf-8").splitlines()
    story = [p("Anexo A · docs/cambios.md", "title")]
    rows = []
    for line in text:
        if line.startswith("## "):
            if rows:
                story.append(table(rows, None)); rows = []
            story.append(p(line[3:], "h"))
        elif line.startswith("|") and not set(line) <= set("|-: "):
            rows.append([c.strip() for c in line.strip("|").split("|")])
    if rows:
        story.append(table(rows, None))
    return story


def main():
    body = build_story() + cambios_story()
    tmp = DOCS / "_memo_cuerpo.pdf"
    for _ in range(1):
        doc = SimpleDocTemplate(str(tmp), pagesize=A4, **MARGINS, title="PSet4 memo técnico",
                                author="Felipe Ron Andrade")
        doc.build(list(body), onFirstPage=page, onLaterPages=page)
        state["total"] = len(PdfReader(tmp).pages)
    writer = PdfWriter()
    writer.append(str(tmp))
    for name in ["PSet1_memo_Ron (1).pdf", "PSet1_pitch_Ron (1).pdf", "PSet2_memo_Ron_Andrade.pdf",
                 "PSet3_memo_Ron_Andrade.pdf"]:
        writer.append(str(DOCS / "historial" / name))
    with OUT.open("wb") as handle:
        writer.write(handle)
    tmp.unlink()
    print(f"{OUT.name}: {state['total']} páginas propias + anexos")


if __name__ == "__main__":
    main()
