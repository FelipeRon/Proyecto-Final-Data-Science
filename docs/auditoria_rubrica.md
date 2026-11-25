# Verificación de la rúbrica extendida

Evaluación técnica orientativa basada en la rúbrica del 4 de noviembre de 2026.

| Criterio | Nivel estimado | Evidencia |
|---|---:|---|
| Patrón de despliegue | 4/4 | `despliegue.md` justifica batch cada 15 minutos, respuesta dentro de 5 minutos desde el cierre y la pérdida de inmediatez frente a online. Los números son supuestos del piloto. |
| Servicio y pruebas | 4/4 con CI verde | Imagen construida y levantada con Compose. Predicción registrada en Snowflake y respuesta HTTP 422 al omitir torque. Pipeline compartido, dependencias principales fijadas y 16 pruebas en Docker. El workflow CI debe estar en verde para el commit evaluado. |
| Registro y versionado | 4/4 | La API resolvió el alias champion, v1, run d07d9f7f061848138579716948af2c6f de PSET-03. `despliegue.md` documenta promoción y reversión. |
| Monitoreo y deriva | 4/4 | Replay directo de Snowflake y verificación del tablero. El notebook ejecutado separa desplazamiento de torque de un cambio inducido de la relación entrada/etiqueta. GET /monitoreo expone la alerta operativa. |
| Comunicación y retirada | 4/4 | Memo técnico, presentación ejecutiva y `criterio_retirada.md`, con condiciones medibles de capacidad, costo y trazabilidad. |

## Evidencia de ejecución

El replay consultó la OBT sin montar `data/`. El Query ID de Snowflake, la identificación del modelo y la predicción HTTP auditada quedan en `verificacion_rubrica.json`. Se verificaron 2.000 predicciones de replay, ocho lotes, una alerta y un evento de API consultable en la base. Los CSV son exportaciones de evidencia. La API y el tablero consultan las tablas de Snowflake con `PSET4_BACKEND=snowflake`.

El mayor PSI de los controles fue 0,0720 y el del lote alterado 2,6330. El valor 0,25 discriminó ambos grupos en este ensayo. La prueba conceptual controlada conservó sensores y prevalencia y bajó AP de 0,9400 a 0,0223. Los períodos y costos son simulados.

## Pendientes de entrega

El [CI](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45469538596) y el [CD](https://github.com/FelipeRon/Proyecto-Final-Data-Science/actions/runs/45469538637) del commit `ae65fb5` pasaron. El CD construyó la imagen y la publicó en GHCR como `ghcr.io/feliperon/proyecto-final-data-science:ae65fb5e7e98d95fd24fd0f25696ae6114db2c5a`. Para calificar un commit posterior, consulta sus propias ejecuciones.

La [verificación desde un clon limpio](verificacion_reproducibilidad.md) cubre el Compose integrado, Snowflake, Kestra, el rollback y el reentrenamiento aislado. Para la consigna original quedan la prueba integral de RAW a OBT en una cuenta nueva, el disparo por métrica, la aprobación en Kestra y el video.
