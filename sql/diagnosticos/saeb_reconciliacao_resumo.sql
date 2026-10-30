-- Resumo da reconciliação do SAEB: quantas médias oficiais foram comparadas e a maior diferença, por recorte.
-- Mesma lógica do teste dbt assert_saeb_media_bate_com_inep. Uso: make sql < sql/diagnosticos/saeb_reconciliacao_resumo.sql
with base as (
    select ano_saeb, co_uf, serie_saeb, disciplina, rede, soma_peso, soma_peso_prof
    from gold.fato_saeb_proficiencia_ano
    union all
    select ano_saeb, co_uf, 14, disciplina, rede, soma_peso, soma_peso_prof
    from gold.fato_saeb_proficiencia_ano where arquivo_saeb = '34EM'
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
    from silver.stg_saeb__resultado_oficial
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
select ano_saeb, abrangencia, recorte, count(*) comparacoes,
       count(*) filter (where media_calculada is null) sem_calculo,
       round(max(abs(media_calculada - media_oficial))::numeric, 4) maior_diferenca
from comparado group by 1,2,3 order by 1,2,3;
