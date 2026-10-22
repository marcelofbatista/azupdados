{#
  GOLD — IDEB do Brasil, das regiões e das UFs. Grão: território × rede × etapa × edição.
  O arquivo do INEP identifica o território pelo nome; o código vem das dimensões de território.
#}
with base as (
    select s.*,
           case when {{ normalizar_nome('s.no_territorio') }} = 'brasil' then 'brasil'
                when r.co_regiao is not null then 'regiao'
                when u.co_uf is not null then 'uf' end as nivel,
           r.co_regiao as co_regiao_direto, u.co_uf, u.co_regiao as co_regiao_da_uf
    from {{ ref('stg_ideb__agregado') }} s
    left join {{ ref('dim_regiao') }} r on {{ normalizar_nome('r.no_regiao') }} = {{ normalizar_nome('s.no_territorio') }}
    left join {{ ref('dim_uf') }} u on {{ normalizar_nome('u.no_uf') }} = {{ normalizar_nome('s.no_territorio') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['no_territorio', 'rede', 'etapa', 'ano_ideb']) }} as fato_ideb_agregado_ano_sk,
    nivel,
    no_territorio,
    coalesce(co_regiao_direto, co_regiao_da_uf) as co_regiao,
    co_uf,
    rede,
    {{ etapa_ideb_sk('etapa') }} as etapa_sk,
    ano_ideb,
    {{ pivotar_ideb() }}
from base
group by 2, 3, 4, 5, 6, 7, 8, etapa
