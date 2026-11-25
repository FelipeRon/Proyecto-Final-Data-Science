import json
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from monitoreo.alertas import REGLAS, evaluar

st.set_page_config(page_title="AI4I - Monitoreo", layout="wide")
st.title("Monitoreo de la simulación")
try:
    if os.getenv("PSET4_BACKEND","local")=="snowflake":
        from monitoreo.snowflake_store import read_rows
        source=read_rows("monitoreo","alertas")
        data=pd.DataFrame(source["monitoreo"])
    else:
        data=pd.read_csv("docs/monitoreo.csv")
except (FileNotFoundError,KeyError):
    st.info("Ejecuta primero el replay.")
    st.stop()

data["periodo"]=data["periodo"].astype(int)
events=pd.DataFrame(evaluar(data.drop(columns=["detalle"],errors="ignore").to_dict("records")))
marks=[]
if not events.empty:
    for periodo, group in events.groupby("periodo"):
        marks.append({"periodo":periodo,"evento":"Alerta: "+", ".join(group.regla)})
cycle=Path("docs/reentrenamiento.json")
if cycle.exists():
    info=json.loads(cycle.read_text(encoding="utf-8"))
    # El candidato se entrena al cierre del lote 6, cuando su etiqueta ya llegó.
    marks.append({"periodo":6,"evento":f'Reentrenamiento v{info["version"]} '
                  f'({"promovido" if info.get("promovido") else "rechazado"})'})
marks=pd.DataFrame(marks,columns=["periodo","evento"])


def chart(columns, title, fmt=",.2f"):
    long=data.melt("periodo",columns,var_name="serie",value_name="valor")
    lines=alt.Chart(long).mark_line(point=True).encode(
        x=alt.X("periodo:O",title="Lote"),y=alt.Y("valor:Q",title=None,axis=alt.Axis(format=fmt)),
        color=alt.Color("serie:N",title=None),tooltip=["periodo","serie",alt.Tooltip("valor:Q",format=fmt)])
    rules=alt.Chart(marks).mark_rule(strokeDash=[4,4],color="#c0392b").encode(
        x="periodo:O",tooltip=["periodo","evento"])
    st.altair_chart((lines+rules).properties(title=title,height=260),use_container_width=True)


st.caption("Las líneas rojas punteadas marcan lotes con alertas y el reentrenamiento.")
left,right=st.columns(2)
with left:
    chart(["cost_per_1000","costo_regla","costo_sin_inspeccion"],"Negocio: costo por 1.000 lecturas",",.0f")
    chart(["ap","psi_max"],"Modelo y deriva: AP y PSI máximo")
with right:
    chart(["p50_ms","p95_ms"],"Sistema: latencia de scoring (ms)")
    chart(["prob_p10","prob_p50","prob_p90","alert_rate"],"Modelo: probabilidades y tasa de inspección")
st.subheader("Volumen por lote")
st.bar_chart(data.set_index("periodo")["n"])
st.subheader("Eventos marcados")
st.dataframe(marks,hide_index=True)
st.subheader("Alertas")
st.dataframe(events if not events.empty else pd.DataFrame(columns=["periodo","regla","valor"]),hide_index=True)
with st.expander("Catálogo de alertas"):
    st.dataframe(pd.DataFrame(REGLAS),hide_index=True)
