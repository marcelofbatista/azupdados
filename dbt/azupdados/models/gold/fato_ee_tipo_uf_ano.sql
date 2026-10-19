{#
  GOLD — Educação especial por tipo de deficiência/TEA/AH-SD.
  Grão: ano × UF × dependência administrativa × tipo.

  Método (armadilha 09): o SEDAP+ fornece só a DISTRIBUIÇÃO por tipo dentro de cada grupo;
  a ESCALA vem do Censo Escolar aberto (qt_mat_esp). O ruído da privacidade diferencial age como um
  fator quase comum a todas as colunas de um grupo, e a razão tipo ÷ total cancela esse fator.

  Um estudante pode ter mais de um tipo: a soma dos tipos excede o total da educação especial.

  Células pequenas: o ruído pode deixar `qt_sedap` NEGATIVO. O valor bruto é mantido (somar células
  com ruído sem cortar os negativos é o que preserva a média sem viés); `qt_estimada` só é calculada
  quando o grupo tem ao menos `sedap_min_ee_confiavel` matrículas na educação especial, e é cortada em 0.
#}
{%- set minimo = var('sedap_min_ee_confiavel', 500) -%}
with sedap as (
    select * from {{ ref('stg_sedap__ee_tipo') }}
),

totais_sedap as (
    select
        ano_censo, co_uf, tp_dependencia,
        max(valor) filter (where metrica = 'total_matriculas')        as total_matriculas_sedap,
        max(valor) filter (where metrica = 'total_educacao_especial') as total_ee_sedap
    from sedap
    group by 1, 2, 3
),

aberto as (
    select ano_censo, co_uf, tp_dependencia,
           sum(qt_mat_bas) as qt_mat_bas_aberto,
           sum(qt_mat_esp) as qt_mat_esp_aberto
    from {{ ref('stg_censo_escolar__escola') }}
    group by 1, 2, 3
),

por_tipo as (
    select s.ano_censo, s.co_uf, s.tp_dependencia, t.tipo_deficiencia_sk, s.valor as qt_sedap
    from sedap s
    join {{ ref('dim_tipo_deficiencia_inep') }} t on t.codigo = s.metrica
)

select
    {{ dbt_utils.generate_surrogate_key(['p.ano_censo', 'p.co_uf', 'p.tp_dependencia', 'p.tipo_deficiencia_sk']) }}
                                                  as fato_ee_tipo_uf_ano_sk,
    p.ano_censo,
    p.co_uf,
    p.tp_dependencia,
    p.tipo_deficiencia_sk,
    p.qt_sedap,
    ts.total_ee_sedap,
    ts.total_matriculas_sedap,
    a.qt_mat_esp_aberto,
    a.qt_mat_bas_aberto,
    round(p.qt_sedap::numeric / nullif(ts.total_ee_sedap, 0), 6)               as proporcao_no_grupo,
    ts.total_ee_sedap >= {{ minimo }}                                          as eh_celula_confiavel,
    case when ts.total_ee_sedap >= {{ minimo }} then
        greatest(round(p.qt_sedap::numeric / ts.total_ee_sedap * a.qt_mat_esp_aberto), 0)::integer
    end                                                                         as qt_estimada,
    round(ts.total_matriculas_sedap::numeric / nullif(a.qt_mat_bas_aberto, 0) - 1, 4)
                                                                                as desvio_total_sedap_vs_aberto,
    'SEDAP+ (INEP) com privacidade diferencial; escala do Censo Escolar aberto'::text as fonte
from por_tipo p
join totais_sedap ts using (ano_censo, co_uf, tp_dependencia)
left join aberto a using (ano_censo, co_uf, tp_dependencia)
