{# GOLD — IDEB por município e rede. Grão: município × rede × etapa × edição. #}
select
    {{ dbt_utils.generate_surrogate_key(['s.co_municipio', 's.rede', 's.etapa', 's.ano_ideb']) }} as fato_ideb_municipio_ano_sk,
    s.co_municipio,
    u.co_uf,
    s.rede,
    {{ etapa_ideb_sk('s.etapa') }} as etapa_sk,
    s.ano_ideb,
    {{ pivotar_ideb() }}
from {{ ref('stg_ideb__municipio') }} s
left join {{ ref('dim_uf') }} u on u.sg_uf = s.sg_uf
group by 2, 3, 4, 5, 6, s.etapa
