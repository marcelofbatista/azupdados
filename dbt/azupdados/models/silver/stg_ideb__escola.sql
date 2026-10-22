{# SILVER — IDEB por escola, formato longo: escola × etapa × métrica × edição. '-' vira nulo e sai. #}
with longo as ({{ desempilhar_ideb('ideb_escola_%', ['sg_uf', 'co_municipio', 'id_escola', 'rede']) }})
select upper(trim(sg_uf)) as sg_uf, {{ para_inteiro('co_municipio') }} as co_municipio,
       {{ para_inteiro('id_escola') }}::bigint as id_escola, trim(rede) as rede, etapa, coluna,
       {{ interpretar_coluna_ideb() }}
from longo
where valor is not null and trim(valor) not in ('-', '')
