{# GOLD — matrículas da educação básica por cor/raça. Grão: escola × ano × cor/raça (marginal do INEP). #}
{%- set mapa = {'qt_mat_bas_branca': 1, 'qt_mat_bas_preta': 2, 'qt_mat_bas_amarela': 3,
                'qt_mat_bas_parda': 4, 'qt_mat_bas_indigena': 5, 'qt_mat_bas_nd': 9} -%}
select sk as fato_matricula_cor_raca_escola_ano_sk, escola_sk, ano_censo, co_uf, co_municipio,
       tp_dependencia, cor_raca_sk, qt_matriculas
from ({{ desempilhar_recorte(mapa, 'cor_raca_sk') }}) t
