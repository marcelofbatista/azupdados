{#
  Reconciliação com o oráculo oficial: a soma de matrículas da educação básica na silver
  precisa ser IGUAL ao total divulgado pelo INEP para cada ano em que temos o número oficial.
  Falha (retorna linhas) quando há qualquer diferença.
#}
with calculado as (
    select ano_censo, sum(qt_mat_bas) as matriculas_calculadas
    from {{ ref('stg_censo_escolar__escola') }}
    group by ano_censo
)

select
    o.ano_censo,
    o.matriculas_educacao_basica              as oficial_inep,
    c.matriculas_calculadas                   as calculado,
    c.matriculas_calculadas - o.matriculas_educacao_basica as diferenca
from {{ ref('ref_totais_oficiais_inep') }} o
join calculado c using (ano_censo)
where c.matriculas_calculadas is distinct from o.matriculas_educacao_basica
