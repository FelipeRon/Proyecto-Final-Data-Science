"""Genera docs/arquitectura.png y docs/modelo_dimensional.png con matplotlib."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

DOCS = Path(__file__).resolve().parents[1] / "docs"
INK, MUTED, LINE = "#1f2933", "#52606d", "#9aa5b1"
FILL = {"datos": "#e3f2fd", "modelo": "#e8f5e9", "servicio": "#fff3e0", "operacion": "#fce4ec"}


def box(ax, x, y, w, h, title, body, kind):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=FILL[kind], ec=LINE, lw=1))
    ax.text(x + w / 2, y + h - 0.18, title, ha="center", va="top", fontsize=9.5,
            weight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.48, body, ha="center", va="top", fontsize=7.6,
            color=MUTED, linespacing=1.35)


def arrow(ax, a, b, label=None, rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, color=MUTED,
                                 lw=1.1, connectionstyle=f"arc3,rad={rad}"))
    if label:
        vertical = abs(a[0] - b[0]) < 1e-6
        x = (a[0] + b[0]) / 2 + (0.08 if vertical else 0)
        y = (a[1] + b[1]) / 2 + (0 if vertical else 0.12) - (0.85 if rad else 0)
        ax.text(x, y, label, ha="left" if vertical else "center", va="center",
                fontsize=7, color=MUTED, style="italic")


def arquitectura():
    fig, ax = plt.subplots(figsize=(13, 6.2), dpi=160)
    ax.set_xlim(0, 13); ax.set_ylim(-0.7, 6.2); ax.axis("off")
    w, h = 2.25, 1.35
    top = [(0.2, "Fuente", "UCI AI4I 2020\nCSV local de respaldo", "datos"),
           (2.75, "Kestra: ingesta", "ingesta.yml\nreintentos y backfill", "datos"),
           (5.3, "Snowflake + dbt", "RAW → Bronze → Silver\n→ Gold (estrella)", "datos"),
           (7.85, "Spark", "join validado\n→ OBT_READINGS", "datos"),
           (10.4, "Experimentación", "notebooks 01-05, src/\nMLflow: runs y registro", "modelo")]
    for x, t, b, k in top:
        box(ax, x, 4.5, w, h, t, b, k)
    for i in range(len(top) - 1):
        arrow(ax, (top[i][0] + w, 5.17), (top[i + 1][0], 5.17))
    mid = [(10.4, "MLflow Registry", "alias champion / challenger\nrollback moviendo el alias", "modelo"),
           (7.85, "API FastAPI", "/salud /modelo /predecir\nPydantic, umbral, respaldo", "servicio"),
           (5.3, "produccion_lotes.yml", "8 lotes desde la OBT\nlote 6 con +18 Nm", "servicio"),
           (2.75, "Snowflake operativo", "PREDICCIONES\nMONITOREO · ALERTAS", "servicio"),
           (0.2, "Tablero Streamlit", "sistema, modelo, deriva\nalertas y reentrenos", "operacion")]
    for x, t, b, k in mid:
        box(ax, x, 2.45, w, h, t, b, k)
    arrow(ax, (11.52, 4.5), (11.52, 3.8), "registra")
    for i in range(len(mid) - 1):
        arrow(ax, (mid[i][0], 3.12), (mid[i + 1][0] + w, 3.12))
    low = [(2.75, "monitoreo.yml", "PSI, KS, chi², AP vs CV; WARN\nreentrena si hay caída", "operacion"),
           (5.3, "reentrenamiento.yml", "challenger, fase=reentrenamiento\npausa de aprobación", "operacion"),
           (7.85, "GitHub Actions", "ci.yml: build + pytest\ncd.yml: imagen a GHCR", "servicio"),
           (10.4, "Decisión humana", "promover: mueve champion\nrechazar: registra motivo", "operacion")]
    for x, t, b, k in low:
        box(ax, x, 0.35, w, h, t, b, k)
    arrow(ax, (3.87, 2.45), (3.87, 1.7), "tras cada replay")
    arrow(ax, (2.75 + w, 1.02), (5.3, 1.02))
    arrow(ax, (6.42, 0.35), (11.52, 0.35), "aprobar o rechazar", rad=0.18)
    arrow(ax, (11.52, 1.7), (11.52, 2.45), "alias")
    arrow(ax, (8.97, 1.7), (8.97, 2.45), "imagen")
    ax.text(0.2, 6.05, "Arquitectura end-to-end · AI4I mantenimiento predictivo", fontsize=12,
            weight="bold", color=INK)
    fig.savefig(DOCS / "arquitectura.png", bbox_inches="tight", facecolor="white")


def modelo_dimensional():
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=160)
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.2); ax.axis("off")

    def table(x, y, w, name, grain, cols, kind):
        h = 0.55 + 0.27 * len(cols)
        ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                    fc="white", ec=LINE, lw=1))
        ax.add_patch(FancyBboxPatch((x, y - 0.5), w, 0.5, boxstyle="round,pad=0.02,rounding_size=0.06",
                                    fc=FILL[kind], ec=LINE, lw=1))
        ax.text(x + 0.12, y - 0.2, name, fontsize=10, weight="bold", color=INK, va="center")
        ax.text(x + 0.12, y - 0.4, grain, fontsize=7, color=MUTED, va="center", style="italic")
        for i, c in enumerate(cols):
            ax.text(x + 0.15, y - 0.72 - 0.27 * i, c, fontsize=7.8, color=INK, va="center",
                    family="monospace")
        return h

    table(0.3, 4.6, 3.6, "GOLD.FCT_READING", "grano: una fila por lectura del snapshot",
          ["PK reading_id", "   product_id", "FK product_type", "   air/process_temperature_k",
           "   rotational_speed_rpm, torque_nm", "   tool_wear_min", "   temperature_delta_k, power_w",
           "   machine_failure (target)", "   baseline_alert", "   file_sha256, source_row"], "datos")
    table(5.0, 4.6, 2.6, "GOLD.DIM_PRODUCT_TYPE", "una fila por tipo L/M/H",
          ["PK product_type", "   quality_tier"], "modelo")
    table(5.0, 2.7, 4.6, "OBT.OBT_READINGS", "grano: una fila por lectura (Spark: hecho ⋈ dimensión)",
          ["reading_id, 6 features, quality_tier", "machine_failure", "validado: conteo = hechos,",
           "reading_id único, sin huérfanos"], "servicio")
    arrow(ax, (3.9, 4.25), (5.0, 4.25), "N:1 product_type")
    arrow(ax, (3.9, 2.0), (5.0, 2.0), "join izquierdo")
    arrow(ax, (6.3, 3.5), (6.3, 2.7))
    ax.text(0.3, 5.05, "Modelo dimensional (Gold) y OBT", fontsize=12, weight="bold", color=INK)
    fig.savefig(DOCS / "modelo_dimensional.png", bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    arquitectura()
    modelo_dimensional()
