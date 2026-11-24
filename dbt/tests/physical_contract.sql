select * from {{ ref('fct_reading') }} where temperature_delta_k <= 0 or power_w <= 0 or tool_wear_min < 0
