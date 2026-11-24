select reading_id, product_id, product_type, air_temperature_k, process_temperature_k,
       rotational_speed_rpm, torque_nm, tool_wear_min, temperature_delta_k, power_w,
       machine_failure, baseline_alert, target_mode_disagreement, file_sha256, source_row
from {{ ref('int_readings') }}
