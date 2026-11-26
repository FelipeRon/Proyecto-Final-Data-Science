# PSet 04 · Guía de reproducción

Pasos para reproducir el proyecto final (detección de falla actual con AI4I 2020) desde un clon limpio. El detalle técnico y los resultados están en el [memo](docs/PSet4_memo_Ron_Andrade.pdf).

Los comandos son de PowerShell con Docker Desktop y se ejecutan desde la raíz del repositorio.

## 0. Requisitos

- Docker Desktop con Docker Compose v2.
- Git.
- Una cuenta de Snowflake con un rol que lea `PSET2.OBT.OBT_READINGS` y pueda crear y escribir tablas en el esquema `OBT`, con autenticación por llave privada. Sin cuenta se puede seguir la guía con el backend local (paso 9).

## 1. Clonar el repositorio

```powershell
git clone https://github.com/FelipeRon/Proyecto-Final-Data-Science.git
cd Proyecto-Final-Data-Science
```

## 2. Configurar las variables

```powershell
Copy-Item .env.example .env
```

En `.env`:

1. Completa `SNOWFLAKE_ACCOUNT` y, si cambian, usuario, rol, warehouse y base.
2. Guarda la llave privada en `secrets/snowflake_key.p8` o apunta `SNOWFLAKE_SECRETS_DIR` a su carpeta.
3. Completa `KESTRA_DB_PASSWORD`, `KESTRA_USER` y `KESTRA_PASSWORD`.
4. Pon en `HOST_PROJECT_DIR` y `KESTRA_SECRETS_DIR` las rutas absolutas del repositorio y de los secretos tal como las ve el motor Linux de Docker Desktop, por ejemplo `"/run/desktop/mnt/host/c/Users/yo/Proyecto Data Science/Proyecto-Final-Data-Science"`.
5. Pon entre comillas dobles todo valor con espacios, porque los flujos de Kestra cargan el archivo con `set -a; . .env`.

Si la cuenta es nueva, crea primero la base, los esquemas y los permisos con [`docs/snowflake_setup.sql`](docs/snowflake_setup.sql).

## 3. Levantar la infraestructura

Ejecuta este bloque una sola vez por carpeta de trabajo. Restaura el registro de MLflow antes del primer arranque.

```powershell
New-Item -ItemType Directory -Force data | Out-Null
docker compose config --quiet
docker compose build runner
docker compose run --rm --no-deps -v "${PWD}/data:/app/data" runner python -m src.portable restore
docker compose pull api
docker compose up -d --no-build mlflow kestra api tablero
```

Servicios disponibles:

| Servicio | Dirección |
|---|---|
| Kestra | <http://127.0.0.1:8080> |
| MLflow | <http://127.0.0.1:5003> |
| API (OpenAPI) | <http://127.0.0.1:8004/docs> |
| Tablero Streamlit | <http://127.0.0.1:8504> |

`API_IMAGE` en `.env` permite fijar la imagen de un commit (`ghcr.io/feliperon/proyecto-final-data-science:<sha>`) o usar la construida en local (`ai4i-pset4:local`). Si en el equipo hay otra copia activa, usa otros puertos y otro nombre de proyecto (`docker compose -p <nombre>`).

## 4. Verificar el modelo restaurado

```powershell
docker compose run --rm runner python -m src.experimentos verify
```

Debe devolver `reproduced: True` con Average Precision 0,9098503380639453. En MLflow, el modelo `ai4i-mantenimiento-modelo` tiene `champion` en la versión 1.

## 5. Probar la API

```powershell
Invoke-RestMethod http://127.0.0.1:8004/salud
Invoke-RestMethod http://127.0.0.1:8004/modelo

$body = @{
  product_type='L'; air_temperature_k=300; process_temperature_k=310
  rotational_speed_rpm=1500; torque_nm=40; tool_wear_min=100
} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8004/predecir -Method Post -ContentType application/json -Body $body
```

`/modelo` debe mostrar `champion` versión 1. Cambia un campo a un valor inválido (por ejemplo `product_type='X'`) para comprobar la respuesta 422.

## 6. Ejecutar las pruebas

```powershell
docker run --rm --mount "type=bind,source=$((Get-Location).Path)/tests,target=/app/tests,readonly" ai4i-pset4:local python -m pytest -q
```

Deben pasar las 31 pruebas. No requieren credenciales.

## 7. Ingesta desde la fuente (RAW → OBT)

```powershell
docker compose build spark
docker compose run --rm spark dbt debug --project-dir /app/dbt --profiles-dir /app/dbt
```

1. Entra a [Kestra](http://127.0.0.1:8080) e importa `kestra/ingesta.yml`.
2. Ejecuta el flujo `pset2.ai4i_pipeline`. El cron viene deshabilitado para que la ejecución sea explícita.
3. Al terminar, `PSET2.OBT.OBT_READINGS` tiene 10.000 filas y `dbt build` reporta 20 de 20.

## 8. Replay, monitoreo y reentrenamiento

### Con Kestra

1. Importa, en este orden, `kestra/monitoreo.yml`, `kestra/produccion_lotes.yml`, y `kestra/reentrenamiento.yml`.
2. Ejecuta `produccion_lotes`. Puntúa 8 lotes de 250 lecturas (con deriva inducida en el lote 6) y escribe en `OBT.PREDICCIONES`, `OBT.MONITOREO` y `OBT.ALERTAS`.
3. `monitoreo` corre al terminar, registra las alertas como WARN y lanza `reentrenamiento` por la deriva del lote 6.
4. `reentrenamiento` registra el candidato con alias `challenger` y queda en pausa. Para decidir, abre la ejecución en Kestra, pulsa **Resume** y completa `decision` (`promover` o `rechazar`), `responsable` y `comentario`.
5. Consulta el resultado con `Invoke-RestMethod http://127.0.0.1:8004/monitoreo` y en el [tablero](http://127.0.0.1:8504).

Los contenedores de tareas usan `KESTRA_MLFLOW_URI` y `KESTRA_PREDICTION_URI` para llegar a los puertos del host, y `KESTRA_RUNNER_IMAGE` para la imagen. En Linux, apúntalas a una dirección alcanzable desde los contenedores, porque `host.docker.internal` no existe por defecto.

### Sin Kestra

```powershell
docker compose run --rm --no-deps runner
Invoke-RestMethod http://127.0.0.1:8004/monitoreo
docker compose run --rm runner python -m src.reentrenar
docker compose run --rm runner python -m src.promover --decision rechazar --version <versión del challenger> --responsable <nombre>
```

## 9. Sin cuenta de Snowflake (backend local)

Pon `PSET4_BACKEND=local` en `.env` y recrea los servicios con `docker compose up -d --no-build api tablero`. El replay y el reentrenamiento leen entonces el snapshot restaurado y los CSV de `docs/`. Este modo sobrescribe `docs/predicciones.csv`, `docs/monitoreo.csv` y `docs/replay.json`; restáuralos al terminar con:

```powershell
git checkout docs
```

La ingesta (paso 7) y el notebook 07 requieren Snowflake.

## 10. Regla de respaldo y rollback

**Regla de respaldo:**

1. Agrega `FORCE_FALLBACK=1` a `.env`.
2. Ejecuta `docker compose up -d api`.
3. `Invoke-RestMethod http://127.0.0.1:8004/modelo` debe mostrar `regla-v1` y cada predicción `respaldo=true`.
4. Vuelve a `FORCE_FALLBACK=0` y recrea el servicio.

**Rollback:**

1. En [MLflow](http://127.0.0.1:5003), reasigna el alias `champion` a la versión anterior (la que guarda `docs/aprobacion.json` tras una promoción).
2. Comprueba con `GET /modelo` que la API sirve esa versión.
3. Devuelve el alias a la versión 1 al terminar.

## 11. Notebooks y documentos

- Los notebooks `notebooks/01` a `06` se ejecutan con el MLflow restaurado; el `07` requiere Snowflake.
- El memo y los diagramas se regeneran en un entorno de Python 3.12 con las dependencias del proyecto (`scripts/` no va en la imagen):

```powershell
pip install -r requirements.txt pypdf
python scripts/diagramas.py
python scripts/memo.py
```

## 12. Apagar

```powershell
docker compose down
```

Agrega `-v` para borrar también los volúmenes (metadatos de Kestra).
