{#
  GOLD — municípios (código IBGE de 7 dígitos, o mesmo que o INEP usa).
  Nome e UF do ano mais recente em que o município aparece no Censo Escolar. Municípios que ainda não
  têm escola nos anos carregados, mas já aparecem no IDEB (ex.: criados depois do último Censo), entram
  pela planilha do IDEB. A malha completa do IBGE entra quando a população for carregada.
#}
with fontes as (
    select co_municipio, no_municipio, co_uf, ano_censo as ano, 1 as prioridade
    from {{ ref('stg_censo_escolar__escola') }}
    where co_municipio is not null
    union all
    select distinct co_municipio, no_municipio, co_municipio / 100000 as co_uf, 0 as ano, 2 as prioridade
    from {{ ref('stg_ideb__municipio') }}
    where co_municipio is not null
),
ranqueado as (
    select *, row_number() over (partition by co_municipio order by prioridade, ano desc) as rn
    from fontes
)
select r.co_municipio, r.no_municipio, r.co_uf, u.sg_uf, u.co_regiao,
       r.prioridade = 2 as so_no_ideb
from ranqueado r
left join {{ ref('dim_uf') }} u using (co_uf)
where r.rn = 1
