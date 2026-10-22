{#
  GOLD — profissionais escolares que não são docentes (gestão, apoio, saúde, tradutor de Libras...).
  Grão: escola × ano. Tradutor/intérprete de Libras e revisor de braille só existem nos anos mais recentes.
#}
{%- set c = colunas_censo() -%}
select
    {{ dbt_utils.generate_surrogate_key(['s.co_entidade', 's.ano_censo']) }} as fato_profissionais_escola_ano_sk,
    e.escola_sk,
    s.ano_censo,
    s.co_uf,
    s.co_municipio,
    s.tp_dependencia,
    {%- for col in c['profissionais'] %}
    s.{{ col }}{{ "," if not loop.last }}
    {%- endfor %}
from {{ ref('stg_censo_escolar__escola') }} s
join {{ ref('dim_escola') }} e using (co_entidade)
