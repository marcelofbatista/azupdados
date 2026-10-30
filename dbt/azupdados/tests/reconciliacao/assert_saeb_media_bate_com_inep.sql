{{ config(tags=['reconciliacao']) }}
{#
  A média ponderada calculada a partir dos alunos (PySpark → fato_saeb_proficiencia_ano) deve reproduzir a
  média que o próprio INEP publica nas planilhas TS_BRASIL e TS_UF.

  Recortes comparados, sempre com localização e área = Total:
    'Total - Federal, Estadual, Municipal e Privada'  → todas as redes
    'Total - Federal, Estadual e Municipal'           → rede pública  (in_publica = 1)
    'Privada'                                         → rede privada  (in_publica = 0)
  (Estadual e municipal separadas não dá: o arquivo do aluno só traz IN_PUBLICA.)

  Série 14 = ensino médio inteiro (3ª e 4ª séries juntas). Tolerância: 0,05 ponto (planilhas com 2 casas).

  Guarda contra o teste vazio: se o gabarito filtrado não tiver nenhuma linha para uma edição carregada, o
  teste FALHA. (A primeira versão filtrava dependência = 'Total', rótulo que não existe nas planilhas, e
  passava sem comparar nada.)
#}
with base as (
    select ano_saeb, co_uf, serie_saeb, disciplina, rede, soma_peso, soma_peso_prof
    from {{ ref('fato_saeb_proficiencia_ano') }}
    union all
    select ano_saeb, co_uf, 14, disciplina, rede, soma_peso, soma_peso_prof
    from {{ ref('fato_saeb_proficiencia_ano') }} where arquivo_saeb = '34EM'
),
recortes as (
    select 'todas' as recorte, * from base
    union all
    select rede, * from base where rede is not null
),
calculado as (
    select ano_saeb, 'BRASIL' as abrangencia, null::int as co_uf, recorte, serie_saeb, disciplina,
           sum(soma_peso_prof) / nullif(sum(soma_peso), 0) as media_calculada
    from recortes group by ano_saeb, recorte, serie_saeb, disciplina
    union all
    select ano_saeb, 'UF', co_uf, recorte, serie_saeb, disciplina,
           sum(soma_peso_prof) / nullif(sum(soma_peso), 0)
    from recortes group by ano_saeb, co_uf, recorte, serie_saeb, disciplina
),
oficial as (
    select *,
           case dependencia_adm
               when 'Total - Federal, Estadual, Municipal e Privada' then 'todas'
               when 'Total - Federal, Estadual e Municipal' then 'pública'
               when 'Privada' then 'privada'
           end as recorte
    from {{ ref('stg_saeb__resultado_oficial') }}
    where localizacao = 'Total' and capital = 'Total'
),
comparado as (
    select o.ano_saeb, o.abrangencia, o.co_uf, o.recorte, o.serie_saeb_oficial, o.disciplina,
           o.media_oficial, c.media_calculada
    from oficial o
    left join calculado c
      on c.ano_saeb = o.ano_saeb and c.abrangencia = o.abrangencia and c.co_uf is not distinct from o.co_uf
     and c.recorte = o.recorte and c.serie_saeb = o.serie_saeb_oficial and c.disciplina = o.disciplina
    where o.recorte is not null
)
select ano_saeb, abrangencia, co_uf, recorte, serie_saeb_oficial, disciplina, media_oficial,
       round(media_calculada::numeric, 2) as media_calculada,
       round((media_calculada - media_oficial)::numeric, 2) as diferenca,
       null::text as problema
from comparado
where media_calculada is null or abs(media_calculada - media_oficial) > 0.05
union all
select e.ano_saeb, null, null, null, null, null, null, null, null, 'gabarito vazio para a edição'
from (select distinct ano_saeb from {{ ref('stg_saeb__resultado_oficial') }}) e
where not exists (select 1 from comparado c where c.ano_saeb = e.ano_saeb and c.recorte = 'todas')
