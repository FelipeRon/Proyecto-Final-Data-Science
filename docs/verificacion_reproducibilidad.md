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

## Tercera verificación: alertas, challenger y aprobación

Sobre el snapshot de MLflow actualizado (alias `challenger` en la versión 3 y tag `fase=reentrenamiento` en su run), restaurado en un MLflow local:

- `src.experimentos verify` devolvió `reproduced: True` con AP 0,9098503380639453; `champion` = 1 y `challenger` = 3.
- `monitoreo.alertas` sobre `docs/monitoreo.csv` generó alertas en el lote 6 (PSI, AP y tasa de inspección) y en el lote 8 (AP), y pidió reentrenar solo por el lote 6 (deriva con impacto). Quitando la caída de AP del lote 6, no pidió reentrenar.
- `src.reentrenar` con `PSET4_BACKEND=local` archivó el ciclo previo en `docs/historial_reentrenamiento/v3.json`, registró la versión 4 como `challenger` con `fase=reentrenamiento` y el motivo, y obtuvo las mismas cifras del ciclo documentado (−USD 12.000 y −USD 4.000 en los lotes 7 y 8; no califica).
- `src.promover --decision rechazar` dejó `champion` en 1 y etiquetó la versión; `--decision promover` fue bloqueado por la regla de promoción.

Esta ronda no usó Kestra ni Snowflake: el ciclo se ejecutó con los mismos módulos que llaman los flujos. Las salidas de la versión 4 quedaron solo en ese registro de prueba.

## Cuarta verificación: ciclo de Kestra contra Snowflake

El 25 de noviembre de 2026 se repitió el ciclo completo sobre `058db03` desde un clon nuevo, en el equipo de desarrollo con Windows y Docker Desktop, con la cuenta de Snowflake del proyecto. Se usó un Compose aislado (`-p pf-verif-058`, puertos 28080, 28004, 25003 y 28504) con imágenes construidas desde el clon y un MLflow propio restaurado desde `docs/mlflow_snapshot.zip`. El registro real no se modificó.

- **Replay y monitoreo.** La ejecución de Kestra `6KqcWW5Oj7kS1Z5kGK6rJf` de `produccion_lotes` leyó `PSET2.OBT.OBT_READINGS` (Query ID `01c8a661-0001-e07f-0001-77be00269e86`, SHA-256 `dbdb2601…9e1e`, igual al de `docs/split.json`) y registró 2.000 predicciones, ocho lotes y una alerta de PSI. Las métricas de los ocho lotes coinciden con `docs/monitoreo.csv`; solo cambian las latencias y el Query ID.
- **Alertas.** El subflujo `monitoreo` (`yux1c9BOTl5vdnZRGaaQs`) registró un WARN con cuatro alertas: PSI 2,633, caída de AP 0,668 y tasa de inspección 62,4 % en el lote 6, y caída de AP 0,707 en el lote 8. Lanzó `reentrenamiento` por «deriva de datos con impacto en el lote 6» y guardó la firma en el KV. Una segunda ejecución de `monitoreo` (`mZ3j8280J1ILlYqFLljc2`) repitió el WARN y no volvió a lanzar el reentrenamiento («el evento ya se procesó»).
- **Reentrenamiento y aprobación.** La ejecución `ml49BBtPSHIoshCf2nodc` registró la versión 4 con alias `challenger` y quedó en pausa con el resumen para aprobación. Se reanudó con `rechazar`: `champion` siguió en 1, la versión 4 quedó etiquetada con la decisión y `verificar_api` leyó la versión 1 en `/modelo`.
- **Bloqueo de la promoción.** En `1HbXsDSW3QCj0NondybdIm` se reanudó con `promover` un candidato que no califica. `aplicar_decision` falló con «El candidato no cumple el criterio de promoción» y `champion` no cambió.
- **Movimiento del alias.** Para recorrer la rama de promoción, en `2ToudARn0Yz27bzgYX2MMi` se marcó a mano `califica=true` en el `docs/reentrenamiento.json` del clon durante la pausa, solo en el registro aislado. Al reanudar con `promover`, `champion` pasó a la versión 6 y `verificar_api` y `GET /modelo` devolvieron esa versión. Después se devolvió `champion` a la versión 1 y `/modelo` lo reflejó.

### Fallo encontrado y corregido

Con Snowflake, el primer reentrenamiento obtuvo una mejora media de −USD 12.000 por 1.000 lecturas (−24.000 y 0 en los lotes 7 y 8), frente a −USD 8.000 (−12.000 y −4.000) del ciclo documentado y del backend local. La primera verificación ya había visto la misma diferencia. La causa es el orden de las filas: `read_rows` devuelve `OBT.PREDICCIONES` ordenada por `ID_PREDICCION`, que es un UUID, mientras que el CSV local conserva el orden del replay. Ese orden cambia los pliegues de la validación cruzada y, con ellos, el umbral y el candidato.

La rama `fix/orden-reentrenamiento-snowflake` reordena las predicciones leídas de Snowflake con el mismo orden del replay (`monitoreo.replay.orden_replay`) y añade una prueba. Con el arreglo, el reentrenamiento orquestado `1HbXsDSW3QCj0NondybdIm` reprodujo exactamente el ciclo documentado: −12.000 y −4.000 en los lotes 7 y 8, media −8.000 y dispersión de CV 1.605,95. Pasaron las 31 pruebas.

También se comprobó que los flujos cargan `.env` con `set -a; . .env` bajo `set -e`. Un valor con espacios sin comillas, como una ruta de Docker Desktop dentro de «Proyecto Data Science», rompe esa carga. `.env.example` ahora indica que esos valores van entre comillas dobles; Compose las retira al leer el archivo.

### Construcción de RAW a OBT en una base nueva

Para no tocar `PSET2`, se creó desde ACCOUNTADMIN la base vacía `PSET2_VERIF` con los esquemas RAW, BRONZE, SILVER, GOLD y OBT y los mismos permisos de `docs/snowflake_setup.sql` para `PSET2_ROLE`. El `.env` del clon apuntó `SNOWFLAKE_DATABASE` a esa base solo durante esta prueba. La imagen de ingesta se construyó desde el clon (`Dockerfile.ingesta`) y, como `kestra/ingesta.yml` fija `ai4i-runner:1`, se importó una copia del flujo que solo cambia esa imagen para no reutilizar una compilada antes.

- La ejecución de Kestra `99H6JjyhD01y2Obgen4gX` de `pset2.ai4i_pipeline` terminó en SUCCESS. Descargó el snapshot de UCI en el primer intento y cargó 10.000 filas en `RAW.AI4I` con SHA-256 `dc6630cd…a8e`, igual al CSV local de PSET-02.
- `dbt build` pasó 20 de 20 (modelos y pruebas, incluidas `conservation`, `physical_contract` y `quarantine_empty`).
- Spark 3.5.3 construyó `OBT.OBT_READINGS` y validó el join: 10.000 filas de hecho, 10.000 en la OBT y 10.000 identificadores únicos.
- Conteos en `PSET2_VERIF`: RAW 10.000, Bronze 10.000, Silver 10.000 con cuarentena vacía, `FCT_READING` 10.000, `DIM_PRODUCT_TYPE` 3 y OBT 10.000.
- El hash canónico de la OBT reconstruida (`src.datos.canonical_hash`) es `dbdb2601fec1714c56141c3b24833f6fb671342cadb68d516238a58cbb9f9e1e`, el mismo de `PSET2.OBT.OBT_READINGS` y de `docs/split.json` (Query ID `01c8a66d-0001-e0ae-0001-77be0026f172`). Es decir, la cadena desde la fuente reproduce exactamente los datos con que se entrenó el modelo.

`PSET2_VERIF` puede eliminarse con `DROP DATABASE PSET2_VERIF;` desde ACCOUNTADMIN.
