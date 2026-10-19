{#
  SILVER — SEDAP+ (INEP, dado protegido com privacidade diferencial).
  Grão: ano × UF × dependência × métrica. Valores já vêm com ruído; ver armadilha 09.
#}
select
    {{ para_inteiro('ano') }}            as ano_censo,
    {{ para_inteiro('co_uf') }}          as co_uf,
    {{ para_inteiro('tp_dependencia') }} as tp_dependencia,
    lower(trim(metrica))                 as metrica,
    round(nullif(trim(valor), '')::numeric)::integer as valor,
    excluiu_aee::boolean                 as excluiu_aee,
    extraido_em::timestamptz             as extraido_em,
    arquivo                              as _arquivo_origem
from {{ source('bronze', 'sedap_ee_tipo') }}
