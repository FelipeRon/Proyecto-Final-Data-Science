# Cambios respecto a los PSets anteriores

| Observación o decisión | Ajuste | Evidencia |
|---|---|---|
| PSet 1 pidió corregir el horizonte y definir la regla experta. | La unidad es una lectura y el objetivo es la falla actual. La regla inspecciona con desgaste ≥200 min o torque ≥60 Nm. | src/datos.py, src/pipeline.py |
| PSet 1 pidió cuantificar los errores y explicitar los costos. | Se comparan inspección, emergencia y costo residual con un escenario económico común. | src/metricas.py, monitoreo/replay.py |
| PSet 1 pidió considerar el carácter sintético y la ausencia de series por máquina. | La operación se simula con ocho lotes y demora explícita de etiquetas. El análisis por orden UDI se conserva como sensibilidad. | docs/sensibilidad_orden_udi.csv |
| PSet 1 pidió una solicitud concreta al patrocinador. | Solicitar telemetría, etiquetas y costos reales de inspección y emergencia para un piloto. | Presentación ejecutiva |
| PSet 2 validó recuperación ante fallos y trazabilidad del snapshot. | Se reutiliza la ingesta con reintentos y respaldo, dbt y la validación del join Spark. | kestra/ingesta.yml, dbt/, spark/ |
| PSet 3 fijó la selección antes de abrir el holdout. | Se utiliza la versión del registro entrenada con Snowflake. El holdout se reutiliza para replay, por lo que la simulación no constituye una validación externa. | docs/dataset.json, docs/seleccion.json |

## Correcciones incorporadas desde PSET-03

| Cambio | Efecto en PSET-04 | Evidencia |
|---|---|---|
| Reconsulta de OBT Snowflake y EDA ampliada | La OBT coincide por hash con el snapshot usado por el modelo servido. | docs/pset3_revision/snowflake_reconsulta.json, eda_falla_por_tipo.csv |
| Contrato de inferencia documentado | Las seis entradas del fixture de evaluación pasan la validación de la API. La etiqueta y los campos de auditoría se rechazan. | docs/pset3_revision/contrato_inferencia.json, tests/test_contrato_pset3.py |
| Comparaciones de TabPFN y ChatGPT | Se incorporan como evidencia de experimentación suplementaria. El replay y la API conservan el champion original. | docs/pset3_revision/tabpfn.json, llm.json |
| Notebooks con salidas y evidencia MLflow | Los notebooks de PSET-03 y su memo actualizado documentan la revisión y la trazabilidad de los modelos. | notebooks/ y memo PSET-03 en Proyecto-Final/historial/ |
