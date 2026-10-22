{{ config(severity='warn') }}
{#
  Cada recorte (cor/raça, sexo, faixa etária) deve somar o total de matrículas da escola.
  Divergência indica categoria faltando no mapeamento ou mudança de layout num ano.
#}
with total as (
    select escola_sk, ano_censo, qt_mat_bas from {{ ref('fato_matricula_escola_ano') }} where qt_mat_bas > 0
),
recortes as (
    select 'cor_raca' as recorte, escola_sk, ano_censo, sum(qt_matriculas) as soma
    from {{ ref('fato_matricula_cor_raca_escola_ano') }} group by 2, 3
    union all
    select 'sexo', escola_sk, ano_censo, sum(qt_matriculas) from {{ ref('fato_matricula_sexo_escola_ano') }} group by 2, 3
    union all
    select 'faixa_etaria', escola_sk, ano_censo, sum(qt_matriculas)
    from {{ ref('fato_matricula_faixa_etaria_escola_ano') }} group by 2, 3
)
select r.recorte, r.ano_censo, count(*) as escolas_divergentes
from recortes r join total t using (escola_sk, ano_censo)
where r.soma <> t.qt_mat_bas
group by 1, 2
