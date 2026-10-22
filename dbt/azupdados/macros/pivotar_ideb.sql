{# Colunas de medida do IDEB, a partir do formato longo da silver. #}
{% macro pivotar_ideb() -%}
    max(valor) filter (where metrica = 'aprovacao' and sufixo = 'si_4')  as taxa_aprovacao,
    max(valor) filter (where metrica = 'indicador_rend')                  as indicador_rendimento,
    max(valor) filter (where metrica = 'nota_matematica')                 as nota_matematica,
    max(valor) filter (where metrica = 'nota_portugues')                  as nota_portugues,
    max(valor) filter (where metrica = 'nota_media')                      as nota_media_padronizada,
    max(valor) filter (where metrica = 'observado')                       as ideb,
    max(valor) filter (where metrica = 'projecao')                        as meta_ideb
{%- endmacro %}
