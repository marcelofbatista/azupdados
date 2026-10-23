{#
  GOLD — nível socioeconômico (INSE) por escola. Grão: escola × edição do SAEB.
  2013 (que cobre 2011–2013) e 2015 usam outra metodologia: `eh_metodologia_saeb` = false. Não emendar
  essas edições na série de 2019 em diante (aviso do próprio INEP).
#}
select
    {{ dbt_utils.generate_surrogate_key(['s.co_entidade', 's.ano_saeb']) }} as fato_inse_escola_edicao_sk,
    e.escola_sk,
    s.co_entidade,
    s.ano_saeb,
    case s.ano_saeb when 2013 then '2011-2013' else s.ano_saeb::text end as edicao,
    s.eh_metodologia_saeb,
    s.qt_alunos_inse,
    s.inse_valor,
    s.inse_classificacao,
    s.inse_nivel,
    {% for n in range(1, 9) %}s.pc_nivel_{{ n }}{{ ',' if not loop.last }}
    {% endfor %}
from {{ ref('stg_ind__inse') }} s
left join {{ ref('dim_escola') }} e on e.co_entidade = s.co_entidade
