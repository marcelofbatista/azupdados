{#
  Transforma colunas QT_MAT_BAS_<categoria> (formato largo do INEP) em linhas (formato longo),
  uma por categoria, ligadas à dimensão do recorte pela chave informada em `mapa`.
#}
{% macro desempilhar_recorte(mapa, chave_dim) -%}
{%- for coluna, chave in mapa.items() %}
select
    {{ dbt_utils.generate_surrogate_key(['s.co_entidade', 's.ano_censo', "'" ~ chave ~ "'"]) }} as sk,
    e.escola_sk,
    s.ano_censo,
    s.co_uf,
    s.co_municipio,
    s.tp_dependencia,
    {{ chave }} as {{ chave_dim }},
    s.{{ coluna }} as qt_matriculas
from {{ ref('stg_censo_escolar__escola') }} s
join {{ ref('dim_escola') }} e using (co_entidade)
where s.{{ coluna }} is not null
{% if not loop.last %}union all{% endif %}
{%- endfor %}
{%- endmacro %}
