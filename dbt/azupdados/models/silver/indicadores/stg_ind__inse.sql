{#
  SILVER — INSE (Indicador de Nível Socioeconômico) por escola, uma linha por escola × edição.
  As edições mudam de layout (cod_escola/co_escola/id_escola; inse_valor_absoluto/media_inse) e de
  METODOLOGIA: 2013 (2011–2013) classifica em sete níveis nominais ("Muito Baixo" a "Muito Alto" → 1–7);
  2015, em "Grupo 1–6"; ambas em escala ~0–100. De 2019 em diante, escala do SAEB e "Nível I–VIII". O INEP avisa que as duas não são comparáveis: `eh_metodologia_saeb` separa.
#}
{%- set rels = dbt_utils.get_relations_by_pattern('bronze', 'ind_inse_%') -%}
{%- if rels | length == 0 %}
select null::int as ano_saeb, null::bigint as co_entidade, null::int as qt_alunos_inse, null::numeric as inse_valor,
       null::text as inse_classificacao, null::int as inse_nivel, null::boolean as eh_metodologia_saeb,
       {% for n in range(1, 9) %}null::numeric as pc_nivel_{{ n }}, {% endfor %}0 as qt_valores_invalidos
where false
{%- endif %}
{%- for rel in rels %}
{%- set cols = adapter.get_columns_in_relation(rel) | map(attribute='name') | list -%}
{%- set chave = (['id_escola', 'co_escola', 'cod_escola'] | select('in', cols) | list)[0] -%}
{%- set valor = (['media_inse', 'inse_valor_absoluto', 'inse___valor_absoluto'] | select('in', cols) | list)[0] -%}
{%- set classe = (['inse_classificacao', 'inse___classifica__o'] | select('in', cols) | list)[0] -%}
{%- set ano = rel.identifier[-4:] | int %}
select {{ ano }} as ano_saeb,
       nullif(trim({{ chave }}), '')::bigint as co_entidade,
       {{ para_inteiro('qtd_alunos_inse') }} as qt_alunos_inse,
       {{ ind_numero(valor) }} as inse_valor,
       nullif(trim({{ classe }}), '') as inse_classificacao,
       case {{ normalizar_nome(classe) }}
           -- 2013 (edição 2011–2013): sete níveis nominais, do "Muito Baixo" ao "Muito Alto"
           when 'muito baixo' then 1 when 'baixo' then 2 when 'medio baixo' then 3 when 'medio' then 4
           when 'medio alto' then 5 when 'alto' then 6 when 'muito alto' then 7
           else
       case upper(trim(regexp_replace({{ classe }}, '^\s*(n.vel|grupo)\s*', '', 'i')))
           when 'I' then 1 when 'II' then 2 when 'III' then 3 when 'IV' then 4 when 'V' then 5
           when 'VI' then 6 when 'VII' then 7 when 'VIII' then 8
           else case when trim({{ classe }}) ~ '[0-9]+\s*$' then (regexp_match({{ classe }}, '([0-9]+)\s*$'))[1]::int end
       end end as inse_nivel,
       {{ 'true' if ano >= 2019 else 'false' }} as eh_metodologia_saeb,
       {% for n in range(1, 9) %}{% if ('pc_nivel_' ~ n) in cols %}{{ ind_numero('pc_nivel_' ~ n) }}{% else %}null::numeric{% endif %} as pc_nivel_{{ n }},
       {% endfor %}(not {{ ind_valor_ausente(valor) }} and {{ ind_numero(valor) }} is null)::int as qt_valores_invalidos
from {{ rel }}
{% if not loop.last %}union all{% endif %}
{%- endfor %}
