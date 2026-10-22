{#
  GOLD — docentes e turmas por escola. Grão: escola × ano.
  Docente é contado uma vez por etapa em que atua: a soma das etapas passa do total `qt_doc_bas`.
#}
{%- set c = colunas_censo() -%}
select
    {{ dbt_utils.generate_surrogate_key(['s.co_entidade', 's.ano_censo']) }} as fato_docentes_turmas_escola_ano_sk,
    e.escola_sk,
    s.ano_censo,
    s.co_uf,
    s.co_municipio,
    s.tp_dependencia,
    {%- for col in c['docentes_turmas'] %}
    s.{{ col }}{{ "," if not loop.last }}
    {%- endfor %}
from {{ ref('stg_censo_escolar__escola') }} s
join {{ ref('dim_escola') }} e using (co_entidade)
