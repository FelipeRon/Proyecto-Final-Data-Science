# Calificación estimada del PSet 4 (sin video)

Estimación propia del puntaje según la rúbrica de `CD-PSet-4.pdf`, revisando el repositorio en la rama `claude/project-thread-ldgtzl` (25-nov-2026). Se asume que **no se entrega el video de demostración**. El video no tiene un peso propio en la rúbrica, pero es la evidencia que el enunciado pide para la infraestructura local (Compose, ingesta, 422, rollback, alerta, aprobación del reentrenamiento e interruptor). Sin él, cada criterio que dependía de esa demostración se apoya solo en texto, y se descontó en el criterio correspondiente.

## Resultado

| Criterio | Peso | Cumplimiento | Puntos |
|---|---:|---:|---:|
| Patrón de despliegue y servicio de predicción | 15 | 87 % | 13,0 |
| Pruebas automáticas y CI/CD | 10 | 70 % | 7,0 |
| Reentrenamiento, promoción y rollback | 10 | 55 % | 5,5 |
| Simulación de producción y métricas de monitoreo | 10 | 75 % | 7,5 |
| Deriva de datos, deriva conceptual y alertas | 10 | 70 % | 7,0 |
| Ética operativa, criterios de retirada y respaldo | 10 | 80 % | 8,0 |
| Resultado de negocio y presentación ejecutiva | 15 | 90 % | 13,5 |
| Integración end-to-end, correcciones, reproducibilidad y documento técnico | 20 | 70 % | 14,0 |
| **Total** | **100** | | **≈ 75,5 / 100** |

Rango razonable: **72 a 80**, según lo estricto que sea el corrector con la falta del video y con los flujos de Kestra incompletos.

## Detalle por criterio

### 1. Patrón de despliegue y servicio de predicción (13,0 / 15)

Cumple:
- `docs/despliegue.md` y el memo justifican batch (lote cada 15 min, publicación en 5 min) y explican qué tendría que cambiar para usar online.
- `api/main.py` expone `GET /salud`, `GET /modelo` y `POST /predecir`; carga `models:/ai4i-mantenimiento-modelo@champion` sin reconstruir la imagen.
- `api/esquemas.py` valida con Pydantic estricto (tipos, rangos, categorías L/M/H, `extra="forbid"`) y devuelve 422 con el campo que falló.
- Aplica el umbral del PSet 3 y devuelve probabilidad, decisión (`inspeccionar`/`continuar`), versión, run_id e id.
- Cada predicción se registra en `OBT.PREDICCIONES` de Snowflake con id, timestamp, entradas, salida, versión y latencia.

Descuentos:
- El volumen de predicciones por día y el costo de actuar con una predicción desactualizada no se cuantifican (el memo dice que los lotes de 250 "no equivalen a un volumen diario real").
- Sin video no hay demostración de una predicción válida y una inválida sobre la infraestructura levantada.

### 2. Pruebas automáticas y CI/CD (7,0 / 10)

Cumple:
- Contrato (`tests/test_contrato.py`): 200 con el esquema esperado; 422 para campo faltante, tipo incorrecto y categoría desconocida.
- Modelo (`tests/test_modelo.py`): el fixture `tests/fixtures/champion` reproduce AP y costo registrados con tolerancia justificada.
- `ci.yml` corre en cada push y pull request, construye la imagen y ejecuta pytest; `cd.yml` corre las pruebas, construye y publica en GHCR con el hash del commit (verde en `ae65fb5`).

Descuentos:
- **Faltan las 2 pruebas de comportamiento de negocio sobre el modelo** (p. ej. "más desgaste no reduce la probabilidad de falla"). Las pruebas actuales de umbral validan la regla de respaldo, no el modelo. Tampoco existe `tests/test_comportamiento.py`, que pide la estructura.
- La prueba de respaldo usa `FORCE_FALLBACK=1`; no prueba el caso "el modelo no carga" (p. ej. registro inaccesible).
- `docker-compose.yml` usa la imagen local `ai4i-pset4:local`, no la imagen de GHCR que publica el CD.
- El memo todavía dice que la publicación en GHCR y la captura de GitHub Actions "quedan pendientes": falta la captura en verde que pide la sección 5 del documento.

### 3. Reentrenamiento, promoción y rollback (5,5 / 10)

Cumple:
- Regla de promoción con métrica de negocio (costo por 1.000) y dispersión de la CV, evaluada en lotes 7 y 8 que ninguno de los modelos vio.
- Ventana justificada (train original + lotes etiquetados 1 a 6), misma preparación de `src/pipeline.py` sin repetir tuning.
- Ciclo documentado: candidato v3, run `17a1183d…`, costo +USD 8.000 por 1.000, no se promueve y se registra el motivo.
- Rollback 1 → 2 → 1 verificado en `docs/verificacion_reproducibilidad.md`.

Descuentos:
- `kestra/reentrenamiento.yml` **no tiene disparador** (ni por alerta ni por calendario) y la pausa es un `Pause` de 24 h sin rama de aprobar/rechazar ni tarea que mueva el alias `champion`. *Actualización:* `kestra/disparo_deriva.yml` y `kestra/reentrenamiento.yml` ya agregan el disparo por PSI, la aprobación con promover/rechazar y la tarea que mueve `champion` (`src/promover.py`); falta ejecutarlo contra Snowflake y el MLflow restaurado.
- El alias del candidato es `candidato_pset4`, no `challenger`; el tag es `phase`, no `fase=reentrenamiento`, y el motivo del disparo no se registra como tag en MLflow.
- El disparador real es por calendario aunque el enunciado prioriza la alerta de la sección 6.3.
- Sin video ni capturas del rollback y de la pausa de aprobación; la evidencia es solo textual.

### 4. Simulación de producción y métricas de monitoreo (7,5 / 10)

Cumple:
- 8 lotes de 250 lecturas desde la OBT de Snowflake, con la etiqueta disponible un lote después.
- Lote 6 con deriva inducida documentada (+18 Nm de torque).
- Se explica que AI4I no es cronológico y se incluye la sensibilidad por orden UDI.
- Métricas de modelo (percentiles de probabilidad, tasa de inspección, AP, costo) y de datos (faltantes, fuera de rango, categoría nueva).

Descuentos:
- `kestra/produccion_lotes.yml` ejecuta el replay completo en una sola tarea, no un ciclo por lote (leer, predecir, guardar y unir con el target cuando llega).
- Faltan las métricas de sistema de tasa de errores 4xx/5xx (el memo lo reconoce).

### 5. Deriva de datos, deriva conceptual y alertas (7,0 / 10)

Cumple:
- PSI por feature con umbral 0,25 justificado empíricamente; KS para numéricas y chi-cuadrado para `product_type` como respaldo.
- Deriva conceptual: AP del lote contra media de CV menos dos desviaciones.
- El lote 6 dispara la alerta (PSI 2,63) y los 7 de control no (máximo 0,072).
- Tablero Streamlit con métricas de sistema, modelo y deriva por lote.

Descuentos:
- `kestra/monitoreo.yml` solo consulta `GET /monitoreo` e imprime el JSON. No calcula métricas, no escribe `MONITOREO` ni emite una alerta explícita en el log.
- La tabla de diagnóstico (entradas/desempeño/acción) y la plantilla de alertas (métrica, umbral, ventana, severidad, quién, acción) aparecen en prosa, no como tablas. Hay una sola alerta definida (PSI).
- El tablero no marca los reentrenamientos y muestra las alertas solo como tabla aparte. Falta `monitoreo/alertas.py`, que pide la estructura.

### 6. Ética operativa, criterios de retirada y respaldo (8,0 / 10)

Cumple:
- Subgrupo por tipo de producto (`docs/subgrupos.csv`) con fallas, falsas alertas y omitidas.
- Costo de cada error y quién lo asume (inspección frente a paro y emergencia).
- 3 criterios de retirada con métrica, umbral y respuesta (`docs/criterio_retirada.md`).
- Interruptor `FORCE_FALLBACK` implementado y probado en pytest.

Descuentos:
- Por subgrupo no se reporta la métrica técnica (AP o recall) ni la tasa de decisión de forma explícita, y la aceptabilidad para las personas afectadas se trata de forma breve.
- La revisión del juicio humano del PSet 1 no concluye explícitamente si sigue siendo adecuado o si cambia.
- La demostración del interruptor sobre la API levantada era parte del video.

### 7. Resultado de negocio y presentación ejecutiva (13,5 / 15)

Cumple:
- Costo lote por lote frente a la regla experta y frente a no inspeccionar, en tabla y gráfico, con el lote del reentrenamiento marcado.
- Responde la pregunta: −38,7 % de costo simulado (USD 130.250 frente a 212.500 por 1.000 lecturas) y dice cuándo el modelo pierde (lote 6).
- Presentación de 11 diapositivas para el patrocinador: problema, cambio en la decisión, valor con cifra, riesgos y recomendación (piloto supervisado), con un solo diagrama simple.

Descuentos:
- La recomendación "piloto" no se encuadra explícitamente como escalar, ajustar o retirar.
- No hay anexos técnicos en la presentación (opcionales, pero el enunciado los menciona).

### 8. Integración end-to-end, correcciones, reproducibilidad y documento técnico (14,0 / 20)

Cumple:
- Un solo repositorio con ingesta, dbt, Spark, notebooks, `src/` y lo del PSet 4; notebooks ejecutados con salidas.
- `docker-compose.yml` con Kestra, Spark (bajo demanda), MLflow, API y tablero.
- README con variables de entorno, Snowflake, pruebas y orden de ejecución.
- `docs/cambios.md` con observaciones de los PSets 1 a 3; trazabilidad por versión, run_id, hash del snapshot y Query ID.
- Exportaciones `predicciones.csv`, `monitoreo.csv`, `alertas.csv`, `corridas.csv` y `reentrenamientos.csv`; memo de 10 páginas (≤ 12) con las 10 secciones.

Descuentos:
- **Sin enlace al video en el documento técnico** (requisito explícito).
- El código está en la raíz del repo y no en `proyecto_final/`. Faltan `docs/arquitectura.png`, `docs/modelo_dimensional.png`, `monitoreo/alertas.py` y `tests/test_comportamiento.py`.
- `corridas.csv` no incluye la corrida de reentrenamiento (`17a1183d…`), y `reentrenamientos.csv` no sale de `mlflow.search_runs` filtrando `fase='reentrenamiento'`.
- La prueba RAW → OBT en una cuenta nueva no se ejecutó; Compose no levanta todo con un solo comando (requiere restaurar MLflow antes).
- El memo tiene información desactualizada (GHCR "pendiente") y los anexos (memos anteriores y `cambios.md`) van como archivos sueltos, no dentro del documento.

## Qué subiría más la nota con poco esfuerzo

1. Agregar `tests/test_comportamiento.py` con 2 pruebas de monotonía sobre el fixture del champion (desgaste y torque) y una prueba de "el modelo no carga → respaldo". Aproximadamente +2 puntos.
2. Completar `kestra/reentrenamiento.yml`: disparador (Flow trigger desde `monitoreo` o Schedule), `Pause` con aprobar/rechazar y una tarea que mueva `champion`; renombrar alias a `challenger` y tag a `fase`. Aproximadamente +2 a +3 puntos.
3. Que `kestra/monitoreo.yml` emita un `Log` de nivel WARN/ERROR cuando haya alerta. Aproximadamente +1 punto.
4. Actualizar el memo: captura de Actions en verde, GHCR publicado y tablas de alertas y diagnóstico. Aproximadamente +1 a +2 puntos.
5. Exportar `docs/arquitectura.png` y `docs/modelo_dimensional.png`, y regenerar `corridas.csv` con la corrida de reentrenamiento. Aproximadamente +1 punto.
6. Grabar el video. Recupera la mayor parte de los descuentos por evidencia (+4 a +6 puntos).
