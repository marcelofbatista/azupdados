{# SILVER — IDEB por município e rede, formato longo. #}
with longo as ({{ desempilhar_ideb('ideb_municipio_%', ['sg_uf', 'co_municipio', 'rede']) }})
select upper(trim(sg_uf)) as sg_uf, {{ para_inteiro('co_municipio') }} as co_municipio,
       trim(rede) as rede, etapa, coluna,
       {{ interpretar_coluna_ideb() }}
from longo
where valor is not null and trim(valor) not in ('-', '')
