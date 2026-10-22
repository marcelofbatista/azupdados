{#
  IDEB: transforma as colunas VL_<METRICA>_<ANO>[_<SUFIXO>][__<n>] (formato largo do INEP) em linhas.
  `chaves` são as colunas de identificação do nível (escola, município, UF, Brasil); a etapa vem do
  nome da tabela bronze (ideb_<nivel>_<ai|af|em>).
#}
{% macro desempilhar_ideb(padrao, chaves) -%}
{%- set relacoes = dbt_utils.get_relations_by_pattern('bronze', padrao) -%}
{%- if relacoes | length == 0 %}
select {% for c in chaves %}null::text as {{ c }}, {% endfor %}null::text as etapa,
       null::text as coluna, null::text as valor where false
{%- endif %}
{%- for rel in relacoes %}
{%- set vls = [] -%}
{%- for col in adapter.get_columns_in_relation(rel) -%}
    {%- if col.name.startswith('vl_') %}{% do vls.append(col.name) %}{% endif -%}
{%- endfor %}
select {% for c in chaves %}t.{{ c }}, {% endfor %}'{{ rel.identifier[-2:] }}' as etapa, v.coluna, v.valor
from {{ rel }} t
cross join lateral (values
    {%- for c in vls %}
    ('{{ c }}', t.{{ c }}){{ "," if not loop.last }}
    {%- endfor %}
) as v(coluna, valor)
{% if not loop.last %}union all{% endif %}
{%- endfor %}
{%- endmacro %}

{#
  Interpreta o nome da coluna e o valor. Armadilha 11: quando o INEP repete o nome de uma coluna,
  a n-ésima ocorrência (sufixo __n) é a edição 2·(n−1) anos depois do rótulo — no arquivo de 2025,
  VL_INDICADOR_REND_2023 aparece duas vezes e a segunda é 2025. O teste de unicidade da silver
  pega o caso se a regra não valer para algum arquivo.
#}
{% macro interpretar_coluna_ideb() -%}
    (regexp_match(coluna, '^vl_([a-z_]+?)_([0-9]{4})(?:_([a-z0-9][a-z0-9_]*?))?(?:__([0-9]+))?$'))[1]  as metrica,
    (regexp_match(coluna, '^vl_([a-z_]+?)_([0-9]{4})(?:_([a-z0-9][a-z0-9_]*?))?(?:__([0-9]+))?$'))[2]::int
      + 2 * (coalesce((regexp_match(coluna, '__([0-9]+)$'))[1]::int, 1) - 1)          as ano_ideb,
    coalesce((regexp_match(coluna, '^vl_([a-z_]+?)_([0-9]{4})(?:_([a-z0-9][a-z0-9_]*?))?(?:__([0-9]+))?$'))[3], '') as sufixo,
    case when replace(trim(valor), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
         then replace(trim(valor), ',', '.')::numeric end                                as valor
{%- endmacro %}
