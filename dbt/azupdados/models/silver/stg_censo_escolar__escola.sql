{#
  SILVER — Censo Escolar, grão escola × ano.
  Une todas as tabelas bronze.censo_escolar_escola_<ano> carregadas, tipa as colunas
  e trata sentinelas. Colunas ausentes em algum ano entram como nulo (armadilha 02).
#}
{{ config(materialized='table', indexes=[{'columns': ['co_entidade', 'ano_censo']}]) }}
{#- Tabela, não view: as fatos da gold leem esta camada várias vezes, e refazer a união de 10 anos
    × ~400 colunas a cada leitura derrubou o Postgres por falta de memória num servidor de 1,5 GB. -#}
{%- set c = colunas_censo() -%}
{%- set relacoes = dbt_utils.get_relations_by_pattern('bronze', 'censo_escolar_escola_%') -%}
{%- set cols = colunas_existentes(relacoes) -%}
{%- set quantidades = [
    'qt_mat_bas', 'qt_mat_inf', 'qt_mat_inf_cre', 'qt_mat_inf_pre',
    'qt_mat_fund', 'qt_mat_fund_ai', 'qt_mat_fund_af', 'qt_mat_med',
    'qt_mat_prof', 'qt_mat_eja', 'qt_mat_esp', 'qt_mat_esp_cc', 'qt_mat_esp_ce',
    'qt_mat_inf_int', 'qt_mat_inf_cre_int', 'qt_mat_inf_pre_int',
    'qt_mat_fund_int', 'qt_mat_fund_ai_int', 'qt_mat_fund_af_int', 'qt_mat_med_int',
    'qt_mat_bas_branca', 'qt_mat_bas_preta', 'qt_mat_bas_parda', 'qt_mat_bas_amarela',
    'qt_mat_bas_indigena', 'qt_mat_bas_nd',
    'qt_mat_bas_fem', 'qt_mat_bas_masc',
    'qt_mat_bas_0_3', 'qt_mat_bas_4_5', 'qt_mat_bas_6_10', 'qt_mat_bas_11_14',
    'qt_mat_bas_15_17', 'qt_mat_bas_18_mais'
] + c['infra_quantidades'] + c['docentes_turmas'] + c['profissionais'] -%}

with uniao as (
    {{ dbt_utils.union_relations(relations=relacoes) }}
)

select
    {{ para_inteiro('nu_ano_censo') }}                 as ano_censo,
    {{ para_inteiro('co_entidade') }}::bigint          as co_entidade,
    trim(no_entidade)                                  as no_entidade,
    {{ para_inteiro('co_uf') }}                        as co_uf,
    {{ coluna_ou_nulo('sg_uf', cols, 'upper(trim(sg_uf))') }},
    {{ para_inteiro('co_municipio') }}                 as co_municipio,
    {{ coluna_ou_nulo('no_municipio', cols, 'trim(no_municipio)') }},
    {{ para_inteiro('tp_dependencia') }}               as tp_dependencia,
    {{ para_inteiro('tp_localizacao') }}               as tp_localizacao,
    {{ coluna_ou_nulo('tp_situacao_funcionamento', cols, para_inteiro('tp_situacao_funcionamento'), 'integer') }},
    {%- for q in quantidades %}
    {{ coluna_ou_nulo(q, cols, quantidade_inep(q), 'integer') }},
    {%- endfor %}
    {%- for i in c['infra_indicadores'] %}
    {{ coluna_ou_nulo(i, cols, para_booleano(i), 'boolean') }},
    {%- endfor %}
    _dbt_source_relation                               as _tabela_bronze
from uniao
