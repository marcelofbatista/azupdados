{# GOLD — matrículas da educação básica por faixa etária. Grão: escola × ano × faixa (marginal do INEP). #}
{%- set mapa = {'qt_mat_bas_0_3': 1, 'qt_mat_bas_4_5': 2, 'qt_mat_bas_6_10': 3, 'qt_mat_bas_11_14': 4,
                'qt_mat_bas_15_17': 5, 'qt_mat_bas_18_mais': 10} -%}
select sk as fato_matricula_faixa_etaria_escola_ano_sk, escola_sk, ano_censo, co_uf, co_municipio,
       tp_dependencia, faixa_etaria_sk, qt_matriculas
from ({{ desempilhar_recorte(mapa, 'faixa_etaria_sk') }}) t
