# Criterio de retirada

El responsable de mantenimiento y el equipo de datos revisan al cierre de cada lote etiquetado las columnas cost_per_1000, costo_regla, alert_rate, caida_ap y psi_max de OBT.MONITOREO. Las ventanas son períodos del piloto operativo.

- Revisar el sensor y validar capacidad en el mismo turno si PSI supera 0,25 en cualquier variable o si la tasa de inspección supera 12 % en un lote.
- Activar FORCE_FALLBACK=1 durante el siguiente lote si la tasa supera 12 % en dos lotes consecutivos, o si el costo del champion excede el de la regla durante dos lotes etiquetados consecutivos. Ante pérdida de trazabilidad o falla de registro, suspender decisiones del modelo y aplicar la regla operativa bajo supervisión.
- Para volver al champion, verificar sensor y trazabilidad y exigir dos lotes etiquetados con tasa ≤12 % y costo del modelo ≤ costo de la regla. Mantenimiento valida y registra el retorno.

El objetivo es evitar saturación de inspecciones y fallas omitidas sin una vía de respuesta. El control por subgrupo L, M y H debe corroborarse en planta, donde existen consecuencias reales y tamaños de muestra desiguales. Estos límites son operativos para el piloto y pueden ajustarse con evidencia etiquetada y capacidad observada.
