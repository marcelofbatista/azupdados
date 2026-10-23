{#
  SILVER — de-para das colunas dos indicadores INEP por escola: como cada coluna de cada arquivo foi lida.
  A etapa e a medida vêm do RÓTULO; `etapa_pelo_nome` é o que o nome técnico diria. Onde os dois discordam
  (`nome_diverge_do_rotulo`), o nome técnico está errado no arquivo do INEP (armadilha 12).
#}
-- depends_on: {{ source('bronze', 'ind_colunas') }}
{%- set mapa = ind_mapa(['REND', 'TDI', 'ATU', 'HAD', 'AFD', 'IED', 'IRD', 'ICG']) %}
{%- if mapa | length == 0 %}
select null::text as sigla, null::int as ano_censo, null::int as posicao, null::text as nome_tecnico,
       null::text as rotulo, null::text as tabela, null::boolean as eh_identificacao, null::text as medida,
       null::text as etapa, null::text as etapa_pelo_nome
where false
{%- else %}
select sigla, ano_censo, posicao, nome_tecnico, nullif(rotulo, '') as rotulo, tabela, eh_identificacao,
       medida, etapa, etapa_pelo_nome
from (values
{%- for c in mapa %}
    ('{{ c.sigla }}', {{ c.ano }}, {{ c.posicao }}, '{{ c.nome }}', $r${{ c.rotulo }}$r$, '{{ c.tabela }}', {{ c.eh_id }},
     {{ "'" ~ c.slot ~ "'" if c.slot else 'null' }}, {{ "'" ~ c.etapa ~ "'" if c.etapa else 'null' }},
     {{ "'" ~ c.etapa_pelo_nome ~ "'" if c.etapa_pelo_nome else 'null' }}){{ ',' if not loop.last }}
{%- endfor %}
) as m(sigla, ano_censo, posicao, nome_tecnico, rotulo, tabela, eh_identificacao, medida, etapa, etapa_pelo_nome)
{%- endif %}
