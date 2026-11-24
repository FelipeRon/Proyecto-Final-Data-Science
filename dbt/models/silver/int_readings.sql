select *, process_temperature_k - air_temperature_k as temperature_delta_k,
       torque_nm * rotational_speed_rpm * 2 * 3.141592653589793 / 60 as power_w,
       case when tool_wear_min >= 200 or torque_nm >= 60 then 1 else 0 end as baseline_alert,
       case when machine_failure <> case when twf+ hdf+pwf+osf+rnf > 0 then 1 else 0 end
            then true else false end as target_mode_disagreement
from {{ ref('int_quality') }} where accepted
