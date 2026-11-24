-- Fail closed: the published source should satisfy the contract. Investigate rather than silently discard.
select * from {{ ref('int_quarantine') }}
