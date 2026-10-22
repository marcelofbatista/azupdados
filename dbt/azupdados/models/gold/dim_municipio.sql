{#
  GOLD — municípios (código IBGE de 7 dígitos, o mesmo que o INEP usa).
  Nome e UF do ano mais recente em que o município aparece no Censo Escolar. Municípios sem nenhuma
  escola em nenhum ano não aparecem; a malha completa do IBGE entra quando a população for carregada.
#}
with ranqueado as (
    select co_municipio, no_municipio, co_uf,
           row_number() over (partition by co_municipio order by ano_censo desc) as rn
    from {{ ref('stg_censo_escolar__escola') }}
    where co_municipio is not null
)
select r.co_municipio, r.no_municipio, r.co_uf, u.sg_uf, u.co_regiao
from ranqueado r
left join {{ ref('dim_uf') }} u using (co_uf)
where r.rn = 1
