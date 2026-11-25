# Patrón de despliegue y operación

Se adopta batch para el piloto. Supuesto a validar con mantenimiento: se reúne un lote cada 15 minutos y se publica la lista de inspección dentro de 5 minutos desde su cierre. La peor espera de una lectura sería de 20 minutos. Este objetivo corresponde a priorizar inspecciones de turno y requiere una vía independiente para alarmas de seguridad inmediata. Online reduciría la espera por lectura y permitiría intervenir antes, a cambio de disponibilidad continua y más coordinación para evitar avisos duplicados. Esos avisos inmediatos se pierden con batch. Los ocho períodos del replay son simulados.

## Registro y rollback

La API resuelve ai4i-mantenimiento-modelo@champion en MLflow. GET /modelo muestra alias, versión y run_id. El modelo de referencia es la versión 1, run d07d9f7f061848138579716948af2c6f de PSET-03.

Para promover, el responsable verifica el resultado del candidato en una ventana comparable, registra la versión actual y mueve el alias champion a la versión aprobada en MLflow. GET /modelo debe devolver la versión y el run_id nuevos. Para revertir, mueve el mismo alias a la versión previamente registrada y comprueba GET /modelo y una predicción válida. Usa un registro de demostración para ensayar el cambio. FORCE_FALLBACK activa la regla experta durante un incidente.

## Disparo por métrica y aprobación

`kestra/monitoreo.yml` corre después de cada replay. `monitoreo/alertas.py` aplica la plantilla de alertas (tabla siguiente), las escribe como WARN en el log de Kestra y decide el reentrenamiento: deriva con impacto (PSI > 0,25 con AP bajo el piso de CV en el mismo lote) o caída de AP en dos lotes etiquetados seguidos. La deriva de datos sin caída de desempeño solo genera la alerta de revisión. La firma del evento (query_id, lote y motivo) queda en el KV de Kestra para no reentrenar dos veces por la misma alerta.

| Métrica | Umbral | Ventana | Severidad | Quién la recibe | Acción |
|---|---|---|---|---|---|
| PSI por feature | > 0,25 | 1 lote | Alta | Datos y Mantenimiento | Revisar sensor y fuente. Reentrenar solo si además cae el desempeño. |
| AP del lote etiquetado | < 0,827 (media CV − 2 DE) | 1 lote | Media | Datos | Revisar etiquetas y composición. Con PSI alto o en 2 lotes seguidos, reentrenar. |
| Tasa de inspección | > 12 % | 1 lote | Alta | Mantenimiento | Validar capacidad del turno. En 2 lotes seguidos, activar FORCE_FALLBACK. |
| Costo por 1.000 del modelo | > costo de la regla | 2 lotes seguidos | Alta | Mantenimiento y Finanzas | Activar FORCE_FALLBACK y revisar el modelo. |

| Entradas | Desempeño | Diagnóstico | Acción |
|---|---|---|---|
| Cambian | Se mantiene | Deriva de datos sin impacto | Alerta PSI, revisión del sensor; no se reentrena. |
| Cambian | Cae | Deriva de datos con impacto (lote 6) | Revisar la fuente; reentrenar y comparar el challenger con aprobación manual. |
| Estables | Cae | Deriva conceptual (lote 8, una sola vez) | Revisar etiquetas; reentrenar si la caída se repite en el lote siguiente. |

En el replay, los lotes 1 a 5 y 7 no generan alertas. El lote 6 genera PSI, caída de AP y tasa de inspección de 62,4 % y dispara el reentrenamiento. El lote 8 genera una caída aislada de AP (0,707) sin deriva de entradas; con una sola ocurrencia no reentrena y se documenta como alerta de revisión.

`reentrenamiento` entrena el candidato, lo registra con el alias `challenger` y el tag `fase=reentrenamiento`, escribe en el log un resumen con la mejora de costo y el criterio de promoción, y se pausa. El responsable reanuda la ejecución desde la interfaz de Kestra con `decision` (promover o rechazar), `responsable` y `comentario`. Sin respuesta en 72 horas la ejecución se cancela y el champion no cambia. `src/promover.py` aplica la decisión: solo mueve el alias champion si el candidato cumple el criterio de `src/reentrenar.py`, deja la decisión en etiquetas de la versión en MLflow y guarda en `docs/aprobacion.json` la versión anterior para el rollback. La última tarea consulta GET /modelo para confirmar la versión servida.

## Métricas y alertas

El replay registra latencia p50/p95 por lote para identificar una degradación del scoring. La API registra latencia por predicción para auditar el servicio. La latencia de scoring excluye la escritura del evento de auditoría. Cuando se dispone de etiquetas, AP mide la capacidad de priorizar fallas en clases desbalanceadas y el costo por 1.000 aproxima la carga económica. Antes de las etiquetas, vigilar PSI y tasa de inspección permite detectar cambios de entradas y capacidad.

En el replay de referencia, el PSI máximo de los lotes de control estuvo por debajo de 0,25 y el lote con +18 Nm superó ese umbral. El corte 0,25 separó el escenario inducido de estos controles, sin calibración en planta. Una AP bajo la media de CV menos dos desviaciones con PSI bajo activa investigación por degradación compatible con deriva conceptual. Con PSI alto, primero se investiga la entrada y su efecto antes de atribuir la caída a un cambio de concepto.

GET /monitoreo consulta las alertas y el último lote en Snowflake. El tablero lee las mismas tablas. El notebook de monitoreo analiza las cifras generadas por el replay.
