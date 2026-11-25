# Verificación desde un clon limpio

La comprobación partió del commit `961be00961fe4fd06aeeabbd5d4979f8c764cd32` clonado desde GitHub. Se usó Docker Desktop sobre el mismo equipo físico, con imágenes compiladas sin caché, volúmenes nuevos, nombre Compose separado y puertos alternativos. Se configuró la cuenta de Snowflake existente y se reutilizó su llave local. Para aislar MLflow se dirigió el runner a `http://mlflow:5000`.

- **Registro.** La restauración del ZIP produjo un MLflow separado. `src.experimentos verify` reprodujo las métricas del champion, incluida Average Precision de 0,9098503380639453.
- **Snowflake.** El replay usó `PSET2.OBT.OBT_READINGS` directamente y registró 2.000 predicciones, ocho lotes y una alerta. Query ID `01c8a1a3-0001-dff7-0001-77be00260146`. El runner del replay no montó `data/`.
- **API y tablero.** La API sirvió el champion versión 1 con el run `d07d9f7f061848138579716948af2c6f`. La predicción documentada persistió en Snowflake. Omitir torque produjo HTTP 422. El tablero renderizó sus métricas desde Snowflake.
- **Pruebas.** Pasaron las 16 pruebas en el contenedor recién construido. El workflow CI del commit original también pasó.
- **Rollback y reentrenamiento.** La API aislada reflejó el cambio 1 → 2 → 1. El entrenamiento de Snowflake registró el candidato versión 4 solo en el MLflow del clon. Conservó la decisión de no promover, con una diferencia media de costo de -USD 12.000 por 1.000 lecturas en los lotes de evaluación, frente a -USD 8.000 en el registro histórico.
- **Alcance.** Se verificó la aplicación desde una OBT ya provisionada. La construcción completa de RAW a OBT con una cuenta de Snowflake nueva y los permisos de aprovisionamiento no se ejecutó. Se comprobó que la imagen contiene Spark 3.5.3 y que dbt autentica contra Snowflake.

El workflow CD del commit original falló en el paso que construye y publica la imagen en GHCR. La imagen que usó esta verificación se construyó localmente desde el código fuente. El CD del commit siguiente, `ae65fb5`, pasó: ejecutó las pruebas, construyó la imagen y la publicó en GHCR como `ghcr.io/feliperon/proyecto-final-data-science:ae65fb5e7e98d95fd24fd0f25696ae6114db2c5a`.

- [CI del commit original](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45466217941)
- [CD del commit original](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45466217890) (fallido)
- [CI del commit `ae65fb5`](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45469538596)
- [CD del commit `ae65fb5`](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45469538637) (imagen publicada en GHCR)

## Orquestación e imagen de ingesta

Kestra completó la ejecución 304Q4OjnETbSYsGW1XOLhC en el entorno aislado con las tareas replay y monitoreo en SUCCESS. Los cuatro flujos quedaron validados e importados. Se configuraron las URLs de los servicios y el directorio de trabajo del contenedor.

Después de añadir Git y procps a la imagen de ingesta, spark-submit informó Spark 3.5.3 y dbt debug completó todas las comprobaciones de conexión a Snowflake.

## Segunda verificación: commit `fd3565a`, sin credenciales

El 25 de noviembre de 2026 se repitió la comprobación sobre `fd3565acacd7b9c0eaf660ce3ab81387c56dc7f0` desde un clon nuevo, en un contenedor Linux con Docker Engine y sin acceso a Snowflake. Por eso esta ronda verifica todo lo que no depende de la cuenta y deja fuera lo que sí depende de ella.

- **Pruebas.** Pasaron las 23 pruebas en la imagen recién construida, con el comando de la sección 3 del README. El conteo creció desde la primera verificación por las pruebas del contrato PSET-03 y del disparo por PSI.
- **Registro.** `src.portable restore` restauró `docs/mlflow_snapshot.zip`, cuyo SHA-256 coincide con `docs/mlflow_snapshot.sha256`. Con MLflow del Compose, `src.experimentos verify` devolvió `reproduced: True` y Average Precision de 0,9098503380639453.
- **API y tablero.** `/salud`, `/modelo` (champion versión 1, run `d07d9f7f061848138579716948af2c6f`) y `/docs` respondieron 200, y el tablero cargó en el 8504. Con `PSET4_BACKEND=local`, la predicción documentada devolvió 200. Un tipo inválido, un campo faltante y un campo de etiqueta devolvieron 422. `FORCE_FALLBACK=1` sirvió la regla `regla-v1`. El alias `champion` se movió de 1 a 2 y de vuelta a 1, y `/modelo` reflejó cada cambio. Con el backend `snowflake` y sin cuenta, `/predecir` y `/monitoreo` devolvieron 503, que es la respuesta prevista.
- **Replay.** Con `PSET4_BACKEND=local` y el snapshot restaurado, el replay produjo 2.000 predicciones, ocho lotes y una alerta. Probabilidades, decisiones, PSI y métricas coinciden con `docs/predicciones.csv`, `docs/monitoreo.csv` y `docs/replay.json`. Solo difieren las latencias y faltan las columnas `origen` y `query_id`, que aporta Snowflake. Este modo sobrescribe esos tres archivos, así que conviene restaurarlos con `git checkout docs` al terminar.
- **Notebooks.** Los notebooks 01 a 06 se ejecutan completos con nbclient en la imagen del proyecto, conectada al MLflow restaurado. El 07 requiere Snowflake. En esta ronda se añadieron `docs/ablacion.json` y `docs/plan_tuning.json`, que los notebooks 03 y 04 leen y que solo existían en la carpeta de trabajo original. Se reconstruyeron sin reentrenar: la ablación sale del run `5d2ef8332c4c450bb5bfbd54457e953a` del snapshot, y el plan sale de las tres mejores familias de `docs/candidatos.json`, que son las mismas de `docs/tuning.json`. Las salidas de ambos notebooks coinciden con las guardadas.
- **Kestra.** Kestra v1.3.44 arrancó con PostgreSQL. Los cinco flujos pasaron la validación de la API y se importaron. El flujo `monitoreo` lanzó el contenedor runner con el proyecto montado. No alcanzó la API porque en Linux `host.docker.internal` no existe por defecto y la API publica solo en 127.0.0.1. Para orquestar en Linux, `KESTRA_PREDICTION_URI` y `KESTRA_MLFLOW_URI` deben apuntar a una dirección alcanzable desde los contenedores de tareas.
- **CI/CD.** El [CI](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45636156411) y el [CD](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45636156431) de `fd3565a` pasaron. El CD publicó la imagen en GHCR.

Sin credenciales no se ejecutaron el replay contra `PSET2.OBT.OBT_READINGS`, la escritura en las tablas operativas, el notebook 07, la ingesta RAW→OBT ni el reentrenamiento. Tampoco se construyó la imagen de Spark. Solo las dependencias directas están fijadas en `requirements.txt`, y las transitivas se resuelven al construir. En esta ronda, por ejemplo, Pydantic se resolvió a 2.14 y emitió avisos de deprecación sin afectar las pruebas.
