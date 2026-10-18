{#
  Armadilha 02: o layout do Censo Escolar muda entre anos.
  Devolve a lista de colunas que existem em pelo menos uma tabela bronze do padrão,
  para que a silver selecione cada coluna somente se ela existir, sem quebrar o build.
#}
{% macro colunas_existentes(relacoes) -%}
    {%- set nomes = [] -%}
    {%- if execute -%}
        {%- for rel in relacoes -%}
            {%- for col in adapter.get_columns_in_relation(rel) -%}
                {%- if col.name | lower not in nomes -%}
                    {%- do nomes.append(col.name | lower) -%}
                {%- endif -%}
            {%- endfor -%}
        {%- endfor -%}
    {%- endif -%}
    {{ return(nomes) }}
{%- endmacro %}

{#
  O nulo precisa ter tipo: um `null` sem tipo vira TEXT na view e quebra contas e COALESCE
  na gold quando a coluna não existe em nenhum ano carregado.
#}
{% macro coluna_ou_nulo(nome, existentes, expressao=none, tipo='text') -%}
    {%- if nome in existentes -%}
        {{ expressao if expressao is not none else nome }}
    {%- else -%}
        null::{{ tipo }}
    {%- endif %} as {{ nome }}
{%- endmacro %}
