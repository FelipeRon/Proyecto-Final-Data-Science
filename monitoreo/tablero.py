import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI4I - Monitoreo", layout="wide")
st.title("Monitoreo de la simulación")
try:
    if os.getenv("PSET4_BACKEND","local")=="snowflake":
        from monitoreo.snowflake_store import read_rows
        source=read_rows("monitoreo","alertas")
        data=pd.DataFrame(source["monitoreo"]).set_index("periodo")
        alerts=pd.DataFrame(source["alertas"])
    else:
        data=pd.read_csv("docs/monitoreo.csv").set_index("periodo")
        alerts=pd.read_csv("docs/alertas.csv")
except (FileNotFoundError,KeyError):
    st.info("Ejecuta primero el replay.")
    st.stop()
st.subheader("Costo por 1.000 lecturas")
st.line_chart(data[["cost_per_1000", "costo_regla", "costo_sin_inspeccion"]])
st.subheader("Inferencia y distribución de probabilidades")
st.line_chart(data[["p50_ms", "p95_ms"]])
st.line_chart(data[["prob_p10", "prob_p50", "prob_p90", "alert_rate"]])
st.subheader("Desempeño y deriva")
st.line_chart(data[["ap", "psi_max"]])
st.dataframe(alerts)
