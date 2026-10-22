{#
  SILVER — IDEB do Brasil, das regiões e das UFs, formato longo. Os dois arquivos identificam a linha
  pelo NOME (não pelo código); a gold resolve o código pelas dimensões de território.
#}
with longo as (
    {{ desempilhar_ideb('ideb_uf_%', ['no_regiao_uf', 'rede']) }}
    union all
    select no_brasil as no_regiao_uf, rede, etapa, coluna, valor
    from ({{ desempilhar_ideb('ideb_brasil_%', ['no_brasil', 'rede']) }}) b
)
select {{ sem_nota_rodape('no_regiao_uf') }} as no_territorio,
       {{ sem_nota_rodape('rede') }} as rede,   -- "Total (3)(4)" → "Total" (armadilha 11)
       etapa, coluna,
       {{ interpretar_coluna_ideb() }}
from longo
where valor is not null and trim(valor) not in ('-', '')
