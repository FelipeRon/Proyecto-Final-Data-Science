# Verificación desde un clon limpio

La comprobación partió del commit `961be00961fe4fd06aeeabbd5d4979f8c764cd32` clonado desde GitHub. Se usó Docker Desktop sobre el mismo equipo físico, con imágenes compiladas sin caché, volúmenes nuevos, nombre Compose separado y puertos alternativos. Se configuró la cuenta de Snowflake existente y se reutilizó su llave local. Para aislar MLflow se dirigió el runner a `http://mlflow:5000`.

- **Registro.** La restauración del ZIP produjo un MLflow separado. `src.experimentos verify` reprodujo las métricas del champion, incluida Average Precision de 0,9098503380639453.
- **Snowflake.** El replay usó `PSET2.OBT.OBT_READINGS` directamente y registró 2.000 predicciones, ocho lotes y una alerta. Query ID `01c8a1a3-0001-dff7-0001-77be00260146`. El runner del replay no montó `data/`.
- **API y tablero.** La API sirvió el champion versión 1 con el run `d07d9f7f061848138579716948af2c6f`. La predicción documentada persistió en Snowflake. Omitir torque produjo HTTP 422. El tablero renderizó sus métricas desde Snowflake.
- **Pruebas.** Pasaron las 16 pruebas en el contenedor recién construido. El workflow CI del commit original también pasó.
- **Rollback y reentrenamiento.** La API aislada reflejó el cambio 1 → 2 → 1. El entrenamiento de Snowflake registró el candidato versión 4 solo en el MLflow del clon. Conservó la decisión de no promover, con una diferencia media de costo de -USD 12.000 por 1.000 lecturas en los lotes de evaluación, frente a -USD 8.000 en el registro histórico.
- **Alcance.** Se verificó la aplicación desde una OBT ya provisionada. La construcción completa de RAW a OBT con una cuenta de Snowflake nueva y los permisos de aprovisionamiento no se ejecutó. Se comprobó que la imagen contiene Spark 3.5.3 y que dbt autentica contra Snowflake.

El workflow CD del commit original falló en el paso que construye y publica la imagen en GHCR. La imagen que usó esta verificación se construyó localmente desde el código fuente.

- [CI del commit original](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45466217941)
- [CD del commit original](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45466217890)

## Orquestación e imagen de ingesta

Kestra completó la ejecución 304Q4OjnETbSYsGW1XOLhC en el entorno aislado con las tareas replay y monitoreo en SUCCESS. Los cuatro flujos quedaron validados e importados. Se configuraron las URLs de los servicios y el directorio de trabajo del contenedor.

Después de añadir Git y procps a la imagen de ingesta, spark-submit informó Spark 3.5.3 y dbt debug completó todas las comprobaciones de conexión a Snowflake.
