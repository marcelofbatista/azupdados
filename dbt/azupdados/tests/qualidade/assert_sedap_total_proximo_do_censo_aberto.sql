{{ config(severity='warn') }}
{#
  O total de matrículas do SEDAP+ deve ficar perto do total do Censo aberto no mesmo grupo.
  Tolerância de 5% em grupos com 1.000+ matrículas; abaixo disso o ruído domina (armadilha 09).
  Severidade WARN: o desvio é propriedade da privacidade diferencial, não erro de carga —
  mas um desvio sistemático em muitos grupos indica filtro errado na consulta.
#}
select ano_censo, co_uf, tp_dependencia, total_matriculas_sedap, qt_mat_bas_aberto, desvio_total_sedap_vs_aberto
from {{ ref('fato_ee_tipo_uf_ano') }}
where qt_mat_bas_aberto >= 1000
  and abs(desvio_total_sedap_vs_aberto) > 0.05
group by 1, 2, 3, 4, 5, 6
