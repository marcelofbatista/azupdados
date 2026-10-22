{#
  GOLD — IDEB por escola. Grão: escola × etapa (anos iniciais, anos finais, ensino médio) × edição.
  Escolas que só aparecem em edições anteriores a 2015 não estão na dim_escola (o Censo carregado começa
  em 2015): ficam com escola_sk nulo, mas com o código INEP preservado.
#}
select
    {{ dbt_utils.generate_surrogate_key(['s.id_escola', 's.etapa', 's.ano_ideb']) }} as fato_ideb_escola_ano_sk,
    e.escola_sk,
    s.id_escola,
    u.co_uf,
    s.co_municipio,
    s.rede,
    {{ etapa_ideb_sk('s.etapa') }} as etapa_sk,
    s.ano_ideb,
    {{ pivotar_ideb() }}
from {{ ref('stg_ideb__escola') }} s
left join {{ ref('dim_escola') }} e on e.co_entidade = s.id_escola
left join {{ ref('dim_uf') }} u on u.sg_uf = s.sg_uf
group by 2, 3, 4, 5, 6, 7, 8, s.etapa
