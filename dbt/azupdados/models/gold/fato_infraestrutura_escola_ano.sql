{#
  GOLD — infraestrutura da escola. Grão: escola × ano.
  Indicadores IN_* como booleano (nulo = não informado) e quantidades de salas e equipamentos.
  `qt_salas_utilizadas` é contagem FÍSICA de salas, não por turno: razão alunos por sala precisa
  considerar os turnos de funcionamento.
#}
{%- set c = colunas_censo() -%}
select
    {{ dbt_utils.generate_surrogate_key(['s.co_entidade', 's.ano_censo']) }} as fato_infraestrutura_escola_ano_sk,
    e.escola_sk,
    s.ano_censo,
    s.co_uf,
    s.co_municipio,
    s.tp_dependencia,
    s.tp_localizacao,
    s.tp_situacao_funcionamento,
    {%- for col in c['infra_indicadores'] + c['infra_quantidades'] %}
    s.{{ col }}{{ "," if not loop.last }}
    {%- endfor %}
from {{ ref('stg_censo_escolar__escola') }} s
join {{ ref('dim_escola') }} e using (co_entidade)
