# PSet 04 · Operación del modelo AI4I

Proyecto final de Ciencia de Datos. Detección de falla en la lectura actual. Ejecuta los comandos desde la raíz del proyecto.

## 1. Datos y registro

Configura la cuenta con `docs/snowflake_setup.sql` y ejecuta el pipeline de ingesta desde la fuente hasta RAW, Bronze, Silver, Gold y OBT. El flow de referencia se incluye en `kestra/ingesta.yml`. Usa la configuración del runner PSET-02, el CSV local si UCI no responde y el rol con acceso a la base PSET2.

Para reproducir el modelo entregado, restaura primero el respaldo de MLflow con los pasos de «Infraestructura integrada». Para entrenar un modelo nuevo, sigue el procedimiento de PSET-03 y registra el alias `champion`. El replay usa la OBT en vivo y verifica que coincida por hash con la partición congelada en `docs/split.json`. Los archivos CSV exportados sirven como respaldo de la evidencia.

## 2. API y tablero

En un checkout nuevo, copia la configuración de ejemplo:

```powershell
Copy-Item .env.example .env
```
Completa `SNOWFLAKE_ACCOUNT` en `.env` y guarda la llave en `secrets/snowflake_key.p8` o ajusta `SNOWFLAKE_SECRETS_DIR`. El rol requiere lectura de `PSET2.OBT.OBT_READINGS` y creación/escritura de tablas operativas en el esquema OBT. Levanta primero la infraestructura siguiendo la sección «Infraestructura integrada» y verifica:

```powershell
Invoke-RestMethod http://127.0.0.1:8004/salud
Invoke-RestMethod http://127.0.0.1:8004/modelo
```

La API y OpenAPI están en [8004](http://127.0.0.1:8004/docs). El tablero está en [8504](http://127.0.0.1:8504). Compose conecta los contenedores a su propio servicio en `http://mlflow:5000`. La interfaz del registro está en el puerto local 5003. Ajusta `MLFLOW_TRACKING_URI` si el registro reside en otra dirección.

```powershell
$body = @{
  product_type='L'; air_temperature_k=300; process_temperature_k=310
  rotational_speed_rpm=1500; torque_nm=40; tool_wear_min=100
} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8004/predecir -Method Post -ContentType application/json -Body $body
```

Cambia un campo a un valor inválido para verificar que la API devuelve 422. Los resultados aceptados se guardan en `OBT.PREDICCIONES`. `GET /monitoreo` consulta `OBT.MONITOREO` y `OBT.ALERTAS`. Las pruebas unitarias usan registro local aislado.

## 3. Pruebas

```powershell
docker run --rm --mount "type=bind,source=$((Get-Location).Path)/tests,target=/app/tests,readonly" ai4i-pset4:local python -m pytest -q
```

## 4. Lotes, alertas y reentrenamiento

```powershell
docker compose run --rm runner python -m monitoreo.replay
```

Los lotes se puntúan con la versión de referencia fijada en `docs/seleccion.json`. El tablero consulta `OBT.MONITOREO` y `OBT.ALERTAS`. El lote 6 aumenta 18 Nm el torque. Cada fila identifica el Query ID de la OBT leída en Snowflake. Simula la disponibilidad de etiquetas un lote después.

Para reproducir el reentrenamiento usa una copia nueva sin `docs/reentrenamiento.json` ni su CSV, conserva el snapshot y configura el registro:

```powershell
docker compose run --rm runner python -m src.reentrenar
```

Para ensayar los flujos de Kestra en el servicio de PSET-02, habilita el montaje de volúmenes en su runner Docker y configura `ENV_PSET4_PROJECT_DIR` con la ruta del proyecto visible para el motor Linux. Importa `kestra/monitoreo.yml` antes de `kestra/produccion_lotes.yml`. Configura también `ENV_PSET4_SECRETS_DIR` en Kestra con la ruta de la carpeta de la llave, visible desde el motor Docker. El replay de Kestra publica en Snowflake y el flujo de monitoreo consulta la API. Para cargar resultados históricos desde CSV queda el comando independiente `python -m monitoreo.publicar`.

## 5. Respaldo y cambio de versión

Configura `FORCE_FALLBACK=1` en `.env` y ejecuta `docker compose up -d api`. El servicio aplicará la regla por torque o desgaste e indicará respaldo en la respuesta. Retira ese valor y vuelve a recrear el servicio cuando termine la revisión.

Para rollback en un registro de demostración, reasigna el alias `champion` a la versión anterior desde MLflow y consulta `GET /modelo`. Registra el run_id y conserva el alias original una vez terminada la prueba. La selección de un candidato requiere revisión del costo y de la capacidad de inspección.

## Continuidad con la revisión de PSET-03

Esta entrega conserva el snapshot Snowflake y el modelo de referencia identificados en `docs/dataset.json` y `docs/seleccion.json`. `docs/pset3_revision/` reúne la reconsulta, la EDA ampliada, el contrato de inferencia y las dos pruebas suplementarias de PSET-03. El ensayo supervisado de PSET-04 sigue usando el champion original. `tests/test_contrato_pset3.py` verifica las seis entradas del fixture y el rechazo de campos de etiqueta y auditoría.

## Evidencia de evaluación

Consulta [la auditoría de la rúbrica](docs/auditoria_rubrica.md), [el diseño de despliegue](docs/despliegue.md), [el criterio de retirada](docs/criterio_retirada.md) y [el notebook de monitoreo con sus salidas](notebooks/07_analisis_monitoreo.ipynb). El registro vivo se verifica con `Invoke-RestMethod http://127.0.0.1:8004/monitoreo`.

## Infraestructura integrada y entregables

`docker-compose.yml` reúne PostgreSQL, Kestra, MLflow, FastAPI y Streamlit. Spark se ejecuta como trabajo bajo demanda: `docker compose run --rm spark`.

En un checkout limpio, completa las variables privadas de `.env`, incluidos los accesos de Kestra. Mantén `MLFLOW_TRACKING_URI=http://mlflow:5000` para usar el registro de este Compose. Restaura el registro antes del primer arranque de MLflow. Ejecuta el bloque siguiente una sola vez por carpeta de trabajo.

```powershell
New-Item -ItemType Directory -Force data | Out-Null
docker compose config --quiet
docker compose build runner
docker compose run --rm --no-deps -v "${PWD}/data:/app/data" runner python -m src.portable restore
docker compose up -d --no-build mlflow kestra api tablero
```

En un equipo con otra copia activa, usa puertos y nombre de proyecto distintos. La variante de Windows con Docker Desktop requiere que el motor pueda compartir la carpeta del repositorio. `artifacts/` y `data/` son locales. La API sirve el modelo restaurado mediante el alias `champion`. El replay lee la OBT directamente de Snowflake, comprueba el split congelado y escribe las tablas operativas:

```powershell
docker compose run --rm --no-deps runner
Invoke-RestMethod http://127.0.0.1:8004/monitoreo
```

Para una ejecución desde la fuente, construye `docker compose build spark`, importa los YAML de `kestra/` y ejecuta la ingesta antes del replay. El cron de ingesta se entrega deshabilitado para que su ejecución sea explícita. Para comprobar la conexión sin escribir datos, ejecuta `docker compose run --rm spark dbt debug --project-dir /app/dbt --profiles-dir /app/dbt`. En Docker Desktop usa para `HOST_PROJECT_DIR` y `KESTRA_SECRETS_DIR` las rutas absolutas visibles para el motor Linux. Kestra está en [8080](http://127.0.0.1:8080) y MLflow en [5003](http://127.0.0.1:5003). En otro equipo esos puertos deben estar libres. Importa primero `kestra/monitoreo.yml` y después `kestra/produccion_lotes.yml` para ejecutar el replay orquestado. Importa también `kestra/reentrenamiento.yml` y `kestra/disparo_deriva.yml` para que un PSI por encima de 0,25 lance el reentrenamiento y quede en pausa hasta la aprobación manual. `src.reentrenar` se niega a correr si existe `docs/reentrenamiento.json`, así que el ciclo disparado requiere una carpeta de trabajo sin ese registro. Los runners de Kestra usan `KESTRA_MLFLOW_URI` y `KESTRA_PREDICTION_URI` para acceder a los puertos del host y `KESTRA_RUNNER_IMAGE` para el tag de la imagen de PSET-04.

- [Memo técnico](docs/PSet4_memo_Ron_Andrade.pdf)
- [Presentación ejecutiva](docs/PSet4_presentacion_Ron_Andrade.pdf)
- [Historial de los PSets](docs/historial/)
- [Auditoría de la rúbrica](docs/auditoria_rubrica.md)

La [verificación desde un clon limpio](docs/verificacion_reproducibilidad.md) documenta los requisitos, las pruebas y los límites observados.
