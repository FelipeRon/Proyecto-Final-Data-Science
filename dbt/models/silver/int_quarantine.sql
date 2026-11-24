select * from {{ ref('int_quality') }} where not accepted
