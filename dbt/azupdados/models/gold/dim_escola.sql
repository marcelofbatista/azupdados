{#
  GOLD — dimensão escola (SCD tipo 1: atributos do ano mais recente em que a escola aparece).
  O histórico de atributos que mudam (dependência, localização) fica na fato, por ano.
#}
with ranqueado as (
    select
        *,
        row_number() over (partition by co_entidade order by ano_censo desc) as rn,
        min(ano_censo) over (partition by co_entidade)                      as primeiro_ano,
        max(ano_censo) over (partition by co_entidade)                      as ultimo_ano
    from {{ ref('stg_censo_escolar__escola') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['co_entidade']) }} as escola_sk,
    co_entidade,
    no_entidade,
    co_uf,
    sg_uf,
    co_municipio,
    no_municipio,
    tp_dependencia,
    tp_localizacao,
    primeiro_ano,
    ultimo_ano
from ranqueado
where rn = 1
