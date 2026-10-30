{{ config(tags=['reconciliacao']) }}
{#
  A média ponderada calculada a partir dos alunos (PySpark → fato_saeb_proficiencia_ano) deve reproduzir a
  média que o próprio INEP publica nas planilhas TS_BRASIL e TS_UF, no recorte total (todas as redes,
  localizações e áreas). Tolerância de 0,05 ponto na escala SAEB: as planilhas vêm com duas casas.
  Série 14 = ensino médio inteiro (3ª e 4ª séries juntas).
#}
with calculado as (
    select ano_saeb, co_uf, serie_saeb, disciplina, soma_peso, soma_peso_prof from {{ ref('fato_saeb_proficiencia_ano') }}
    union all
    select ano_saeb, co_uf, 14, disciplina, soma_peso, soma_peso_prof
    from {{ ref('fato_saeb_proficiencia_ano') }} where arquivo_saeb = '34EM'
),
brasil as (
    select ano_saeb, 'BRASIL' as abrangencia, null::int as co_uf, serie_saeb, disciplina,
           sum(soma_peso_prof) / nullif(sum(soma_peso), 0) as media_calculada
    from calculado group by 1, 4, 5
),
uf as (
    select ano_saeb, 'UF' as abrangencia, co_uf, serie_saeb, disciplina,
           sum(soma_peso_prof) / nullif(sum(soma_peso), 0) as media_calculada
    from calculado group by 1, 3, 4, 5
),
oficial as (
    select * from {{ ref('stg_saeb__resultado_oficial') }}
    where dependencia_adm = 'Total' and localizacao = 'Total' and capital = 'Total'
)
select o.ano_saeb, o.abrangencia, o.co_uf, o.serie_saeb_oficial, o.disciplina,
       o.media_oficial, round(c.media_calculada::numeric, 2) as media_calculada,
       round((c.media_calculada - o.media_oficial)::numeric, 2) as diferenca
from oficial o
left join (select * from brasil union all select * from uf) c
  on c.ano_saeb = o.ano_saeb and c.abrangencia = o.abrangencia
 and c.co_uf is not distinct from o.co_uf
 and c.serie_saeb = o.serie_saeb_oficial and c.disciplina = o.disciplina
where c.media_calculada is null or abs(c.media_calculada - o.media_oficial) > 0.05
