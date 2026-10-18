{#
  GOLD — fato de matrículas. Grão: uma linha por escola × ano.
  Dependência e localização ficam aqui também, porque mudam ao longo do tempo.
#}
select
    {{ dbt_utils.generate_surrogate_key(['s.co_entidade', 's.ano_censo']) }} as fato_matricula_escola_ano_sk,
    e.escola_sk,
    s.ano_censo,
    s.co_municipio,
    s.tp_dependencia,
    s.tp_localizacao,
    s.tp_situacao_funcionamento,
    s.qt_mat_bas,
    s.qt_mat_inf,
    s.qt_mat_inf_cre,
    s.qt_mat_inf_pre,
    s.qt_mat_fund,
    s.qt_mat_fund_ai,
    s.qt_mat_fund_af,
    s.qt_mat_med,
    s.qt_mat_prof,
    s.qt_mat_eja,
    s.qt_mat_esp,
    s.qt_mat_esp_cc,
    s.qt_mat_esp_ce,
    s.qt_mat_bas_integral
from {{ ref('stg_censo_escolar__escola') }} s
join {{ ref('dim_escola') }} e using (co_entidade)
