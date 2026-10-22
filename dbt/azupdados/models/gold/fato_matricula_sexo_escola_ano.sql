{# GOLD — matrículas da educação básica por sexo. Grão: escola × ano × sexo (marginal do INEP). #}
{%- set mapa = {'qt_mat_bas_masc': 1, 'qt_mat_bas_fem': 2} -%}
select sk as fato_matricula_sexo_escola_ano_sk, escola_sk, ano_censo, co_uf, co_municipio,
       tp_dependencia, sexo_sk, qt_matriculas
from ({{ desempilhar_recorte(mapa, 'sexo_sk') }}) t
