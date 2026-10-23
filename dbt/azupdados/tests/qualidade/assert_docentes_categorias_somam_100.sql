{# Os grupos de adequação da formação (1–5) e os níveis de esforço docente (1–6) repartem os docentes da
   etapa: devem somar 100 (tolerância de arredondamento). #}
{{ config(severity='warn') }}
select 'AFD' as indicador, ano_censo, co_entidade, etapa_indicador_sk,
       coalesce(pct_grupo_1,0)+coalesce(pct_grupo_2,0)+coalesce(pct_grupo_3,0)+coalesce(pct_grupo_4,0)+coalesce(pct_grupo_5,0) as soma
from {{ ref('fato_formacao_docente_escola_ano') }}
where abs(coalesce(pct_grupo_1,0)+coalesce(pct_grupo_2,0)+coalesce(pct_grupo_3,0)+coalesce(pct_grupo_4,0)+coalesce(pct_grupo_5,0) - 100) > 1
union all
select 'IED', ano_censo, co_entidade, etapa_indicador_sk,
       coalesce(pct_nivel_1,0)+coalesce(pct_nivel_2,0)+coalesce(pct_nivel_3,0)+coalesce(pct_nivel_4,0)+coalesce(pct_nivel_5,0)+coalesce(pct_nivel_6,0)
from {{ ref('fato_esforco_docente_escola_ano') }}
where abs(coalesce(pct_nivel_1,0)+coalesce(pct_nivel_2,0)+coalesce(pct_nivel_3,0)+coalesce(pct_nivel_4,0)+coalesce(pct_nivel_5,0)+coalesce(pct_nivel_6,0) - 100) > 1
