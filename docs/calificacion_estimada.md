# Calificación estimada del PSet 4 (sin video)

Estimación propia del puntaje según la rúbrica de `CD-PSet-4.pdf`. Se asume que **no se entrega el video de demostración**. El video no tiene un peso propio, pero es la evidencia que el enunciado pide para la infraestructura local; sin él, cada criterio que dependía de esa demostración se apoya en texto y se descontó ahí.

Tercera evaluación (25-nov-2026), sobre la rama `claude/project-thread-ldgtzl` después de corregir las brechas. Evaluaciones anteriores: 75,5 (commit `aa687e8`) y 78,5 (commit `aea76a4`).

## Resultado

| Criterio | Peso | Antes | Ahora |
|---|---:|---:|---:|
| Patrón de despliegue y servicio de predicción | 15 | 13,0 | 13,5 |
| Pruebas automáticas y CI/CD | 10 | 7,0 | 9,0 |
| Reentrenamiento, promoción y rollback | 10 | 7,0 | 8,0 |
| Simulación de producción y métricas de monitoreo | 10 | 7,5 | 7,5 |
| Deriva de datos, deriva conceptual y alertas | 10 | 7,5 | 8,5 |
| Ética operativa, criterios de retirada y respaldo | 10 | 8,0 | 9,0 |
| Resultado de negocio y presentación ejecutiva | 15 | 13,5 | 13,5 |
| Integración end-to-end, correcciones, reproducibilidad y documento técnico | 20 | 15,0 | 16,5 |
| **Total** | **100** | **78,5** | **≈ 85,5** |

Rango razonable: **82 a 88**. Lo que más pesa en contra es que el ciclo de Kestra contra Snowflake no tiene evidencia de ejecución y que falta el video.

## Qué se corrigió

- **Pruebas de comportamiento** (`tests/test_comportamiento.py`): +100 min de desgaste o +20 Nm de torque suben la probabilidad media y la tasa de inspección del champion; una sobrecarga evidente se inspecciona; si el registro no carga, la API responde con la regla y `respaldo=true`. Total: 30 pruebas.
- **Disparo del reentrenamiento** (`monitoreo/alertas.py`, `kestra/monitoreo.yml`): ya no basta el PSI. Reentrena con deriva con impacto (PSI > 0,25 y AP bajo el piso de CV en el mismo lote) o con caída de AP en 2 lotes seguidos. En el replay dispara el lote 6; el lote 8 (caída aislada) solo alerta. `disparo_deriva.yml` y `monitoreo/disparo.py` quedan integrados en `monitoreo.yml`.
- **Alertas**: plantilla completa (métrica, umbral, ventana, severidad, quién, acción) para PSI, AP, tasa de inspección y costo; `monitoreo.yml` escribe cada alerta como WARN en el log de Kestra.
- **Registro**: alias `challenger` y tag `fase=reentrenamiento`. El snapshot de MLflow se actualizó (challenger → v3, tag `fase` en el run `17a1183d…`); `corridas.csv` incluye el reentrenamiento y `reentrenamientos.csv` sale de `mlflow.search_runs` filtrando `fase`.
- **Ciclo repetible**: `src/reentrenar.py` archiva el ciclo previo en `docs/historial_reentrenamiento/` en vez de negarse a correr. Se repitió el ciclo con el código nuevo sobre el registro restaurado: misma mejora de −USD 8.000, rechazo registrado y promoción bloqueada por la regla.
- **Tablero**: marca con líneas los lotes con alertas y el reentrenamiento, y muestra volumen, latencia, probabilidades, AP, PSI y costo.
- **CD y Compose**: `cd.yml` publica `:<sha>` y `:latest`; la API de `docker-compose.yml` usa `ghcr.io/feliperon/proyecto-final-data-science` (configurable con `API_IMAGE`).
- **Diagramas**: `docs/arquitectura.png` y `docs/modelo_dimensional.png` (`scripts/diagramas.py`).
- **Memo técnico** regenerado con `scripts/memo.py`: 12 páginas, volumen y costo de predicción desactualizada, tabla de GitHub Actions, regla de promoción, plantilla de alertas, tabla de diagnóstico, evidencia del ciclo, métricas por subgrupo, revisión de la supervisión humana y anexos (`cambios.md` y memos de PSET-1 a PSET-3).

## Descuentos que quedan

- **Video** y su enlace en el memo (el memo lo marca como pendiente).
- **Kestra de punta a punta**: el ciclo alerta → challenger → pausa → decisión se ejecutó con los módulos de Python, no en Kestra contra Snowflake. Una captura de esa ejecución sumaría 1 a 2 puntos.
- `kestra/produccion_lotes.yml` corre el replay completo en una tarea, no un ciclo por lote, y `monitoreo.yml` lee las métricas que escribe el replay en vez de calcularlas.
- Tasas 4xx/5xx no se miden en el replay (se explica en el memo).
- La "captura" de GitHub Actions es una tabla con enlaces a las ejecuciones; una captura de pantalla real es más convincente.
- La presentación ejecutiva no cambió: su recomendación (piloto) no dice explícitamente "escalar, ajustar o retirar".
- El código está en la raíz del repositorio y no dentro de `proyecto_final/`; la prueba RAW → OBT en una cuenta nueva no se ejecutó.
