{#
  Armadilha 06: contagens exportadas como "0.0" quebram o cast direto para inteiro.
  Passa por NUMERIC antes de INTEGER e trata string vazia como nulo.
#}
{% macro para_inteiro(coluna) -%}
    nullif(trim({{ coluna }}), '')::numeric::integer
{%- endmacro %}

{#
  Armadilha 01: o INEP usa 88888, 99999 e 77777 como códigos-sentinela em colunas QT_*.
  Somar sem tratar infla qualquer total. Sentinela vira nulo.
#}
{% macro quantidade_inep(coluna) -%}
    case
        when {{ para_inteiro(coluna) }} in (77777, 88888, 99999) then null
        else {{ para_inteiro(coluna) }}
    end
{%- endmacro %}

{#
  Indicadores IN_* do INEP: 1 = sim, 0 = não, vazio = não informado. Qualquer outro valor vira nulo.
#}
{% macro para_booleano(coluna) -%}
    case trim({{ coluna }}) when '1' then true when '0' then false end
{%- endmacro %}
