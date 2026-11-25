# Patrón de despliegue y operación

Se adopta batch para el piloto. Supuesto a validar con mantenimiento: se reúne un lote cada 15 minutos y se publica la lista de inspección dentro de 5 minutos desde su cierre. La peor espera de una lectura sería de 20 minutos. Este objetivo corresponde a priorizar inspecciones de turno y requiere una vía independiente para alarmas de seguridad inmediata. Online reduciría la espera por lectura y permitiría intervenir antes, a cambio de disponibilidad continua y más coordinación para evitar avisos duplicados. Esos avisos inmediatos se pierden con batch. Los ocho períodos del replay son simulados.

## Registro y rollback

La API resuelve ai4i-mantenimiento-modelo@champion en MLflow. GET /modelo muestra alias, versión y run_id. El modelo de referencia es la versión 1, run d07d9f7f061848138579716948af2c6f de PSET-03.

Para promover, el responsable verifica el resultado del candidato en una ventana comparable, registra la versión actual y mueve el alias champion a la versión aprobada en MLflow. GET /modelo debe devolver la versión y el run_id nuevos. Para revertir, mueve el mismo alias a la versión previamente registrada y comprueba GET /modelo y una predicción válida. Usa un registro de demostración para ensayar el cambio. FORCE_FALLBACK activa la regla experta durante un incidente.

## Disparo por métrica y aprobación

`kestra/disparo_deriva.yml` se ejecuta cada vez que el flujo `monitoreo` termina en SUCCESS. Lee GET /monitoreo, toma el mayor PSI entre el último lote y las alertas registradas y, si supera `umbral_psi` (0,25 por defecto), lanza `kestra/reentrenamiento.yml`. La firma del evento (query_id, lote y variable) queda en el KV de Kestra para no reentrenar dos veces por la misma alerta.

`reentrenamiento` entrena el candidato, escribe en el log un resumen con la mejora de costo y el criterio de promoción, y se pausa. El responsable reanuda la ejecución desde la interfaz de Kestra con `decision` (promover o rechazar), `responsable` y `comentario`. Sin respuesta en 72 horas la ejecución se cancela y el champion no cambia. `src/promover.py` aplica la decisión: solo mueve el alias champion si el candidato cumple el criterio de `src/reentrenar.py`, deja la decisión en etiquetas de la versión en MLflow y guarda en `docs/aprobacion.json` la versión anterior para el rollback. La última tarea consulta GET /modelo para confirmar la versión servida.

## Métricas y alertas

El replay registra latencia p50/p95 por lote para identificar una degradación del scoring. La API registra latencia por predicción para auditar el servicio. La latencia de scoring excluye la escritura del evento de auditoría. Cuando se dispone de etiquetas, AP mide la capacidad de priorizar fallas en clases desbalanceadas y el costo por 1.000 aproxima la carga económica. Antes de las etiquetas, vigilar PSI y tasa de inspección permite detectar cambios de entradas y capacidad.

En el replay de referencia, el PSI máximo de los lotes de control estuvo por debajo de 0,25 y el lote con +18 Nm superó ese umbral. El corte 0,25 separó el escenario inducido de estos controles, sin calibración en planta. Una AP bajo la media de CV menos dos desviaciones con PSI bajo activa investigación por degradación compatible con deriva conceptual. Con PSI alto, primero se investiga la entrada y su efecto antes de atribuir la caída a un cambio de concepto.

GET /monitoreo consulta las alertas y el último lote en Snowflake. El tablero lee las mismas tablas. El notebook de monitoreo analiza las cifras generadas por el replay.
