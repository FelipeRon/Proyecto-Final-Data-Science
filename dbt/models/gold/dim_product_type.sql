select distinct product_type, case product_type when 'L' then 'low' when 'M' then 'medium' when 'H' then 'high' end as quality_tier from {{ ref('int_readings') }}
