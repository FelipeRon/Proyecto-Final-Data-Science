select
{% if target.type == 'snowflake' %}try_cast(payload:"UDI"::varchar as integer){% else %}try_cast(json_extract_string(payload, '$."UDI"') as integer){% endif %} as reading_id,
{% if target.type == 'snowflake' %}try_cast(payload:"Product ID"::varchar as varchar){% else %}try_cast(json_extract_string(payload, '$."Product ID"') as varchar){% endif %} as product_id,
{% if target.type == 'snowflake' %}try_cast(payload:"Type"::varchar as varchar){% else %}try_cast(json_extract_string(payload, '$."Type"') as varchar){% endif %} as product_type,
{% if target.type == 'snowflake' %}try_cast(payload:"Air temperature [K]"::varchar as double){% else %}try_cast(json_extract_string(payload, '$."Air temperature [K]"') as double){% endif %} as air_temperature_k,
{% if target.type == 'snowflake' %}try_cast(payload:"Process temperature [K]"::varchar as double){% else %}try_cast(json_extract_string(payload, '$."Process temperature [K]"') as double){% endif %} as process_temperature_k,
{% if target.type == 'snowflake' %}try_cast(payload:"Rotational speed [rpm]"::varchar as double){% else %}try_cast(json_extract_string(payload, '$."Rotational speed [rpm]"') as double){% endif %} as rotational_speed_rpm,
{% if target.type == 'snowflake' %}try_cast(payload:"Torque [Nm]"::varchar as double){% else %}try_cast(json_extract_string(payload, '$."Torque [Nm]"') as double){% endif %} as torque_nm,
{% if target.type == 'snowflake' %}try_cast(payload:"Tool wear [min]"::varchar as double){% else %}try_cast(json_extract_string(payload, '$."Tool wear [min]"') as double){% endif %} as tool_wear_min,
{% if target.type == 'snowflake' %}try_cast(payload:"Machine failure"::varchar as integer){% else %}try_cast(json_extract_string(payload, '$."Machine failure"') as integer){% endif %} as machine_failure,
{% if target.type == 'snowflake' %}try_cast(payload:"TWF"::varchar as integer){% else %}try_cast(json_extract_string(payload, '$."TWF"') as integer){% endif %} as twf,
{% if target.type == 'snowflake' %}try_cast(payload:"HDF"::varchar as integer){% else %}try_cast(json_extract_string(payload, '$."HDF"') as integer){% endif %} as hdf,
{% if target.type == 'snowflake' %}try_cast(payload:"PWF"::varchar as integer){% else %}try_cast(json_extract_string(payload, '$."PWF"') as integer){% endif %} as pwf,
{% if target.type == 'snowflake' %}try_cast(payload:"OSF"::varchar as integer){% else %}try_cast(json_extract_string(payload, '$."OSF"') as integer){% endif %} as osf,
{% if target.type == 'snowflake' %}try_cast(payload:"RNF"::varchar as integer){% else %}try_cast(json_extract_string(payload, '$."RNF"') as integer){% endif %} as rnf,
file_sha256, source_row, source_url, loaded_at
from {{ source('ai4i','AI4I') }}
where file_sha256 = (select file_sha256 from {{ source('ai4i','AI4I') }} group by file_sha256 order by max(loaded_at) desc, file_sha256 limit 1)
