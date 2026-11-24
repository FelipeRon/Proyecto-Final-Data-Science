# Verificación de la rúbrica extendida

Evaluación técnica orientativa basada en la rúbrica del 4 de noviembre de 2026.

| Criterio | Nivel estimado | Evidencia |
|---|---:|---|
| Patrón de despliegue | 4/4 | `despliegue.md` justifica batch cada 15 minutos, respuesta dentro de 5 minutos desde el cierre y la pérdida de inmediatez frente a online. Los números son supuestos del piloto. |
| Servicio y pruebas | 3/4 | Imagen construida y levantada con Compose. Predicción registrada en Snowflake y respuesta HTTP 422 al omitir torque. Pipeline compartido, dependencias principales fijadas y 16 pruebas en Docker. GitHub Actions del commit de entrega queda pendiente. |
| Registro y versionado | 4/4 | La API resolvió el alias champion, v1, run d07d9f7f061848138579716948af2c6f de PSET-03. `despliegue.md` documenta promoción y reversión. |
| Monitoreo y deriva | 4/4 | Replay directo de Snowflake y verificación del tablero. El notebook ejecutado separa desplazamiento de torque de un cambio inducido de la relación entrada/etiqueta. GET /monitoreo expone la alerta operativa. |
| Comunicación y retirada | 4/4 | Dos versiones de la diapositiva de resultados y `criterio_retirada.md`, con condiciones medibles de capacidad, costo y trazabilidad. |

## Evidencia de ejecución

El replay consultó la OBT sin montar `data/`. El Query ID de Snowflake, la identificación del modelo y la predicción HTTP auditada quedan en `verificacion_rubrica.json`. Se verificaron 2.000 predicciones de replay, ocho lotes, una alerta y un evento de API consultable en la base. Los CSV son exportaciones de evidencia. La API y el tablero consultan las tablas de Snowflake con `PSET4_BACKEND=snowflake`.

El mayor PSI de los controles fue 0,0720 y el del lote alterado 2,6330. El valor 0,25 discriminó ambos grupos en este ensayo. La prueba conceptual controlada conservó sensores y prevalencia y bajó AP de 0,9400 a 0,0223. Los períodos y costos son simulados.

## Pendientes de entrega

Para el nivel máximo de la rúbrica extendida queda ejecutar GitHub Actions en el commit que se entregue y conservar el enlace de la corrida en verde. La carpeta local no está configurada como repositorio Git de PSET-04.

Para la consigna original también quedan comprobar el disparador por métrica y la aprobación en Kestra, demostrar promoción y rollback en un registro aislado, verificar un Compose único con toda la infraestructura, publicar la imagen en GHCR y grabar/enlazar el video de hasta siete minutos. El replay, la API, el tablero y la simulación de deriva sí se verificaron desde Docker contra Snowflake.
