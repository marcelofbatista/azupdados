{#
  SILVER — Censo Escolar, grão escola × ano.
  Une todas as tabelas bronze.censo_escolar_escola_<ano> carregadas, tipa as colunas
  e trata sentinelas. Colunas ausentes em algum ano entram como nulo (armadilha 02).
#}
{%- set relacoes = dbt_utils.get_relations_by_pattern('bronze', 'censo_escolar_escola_%') -%}
{%- set cols = colunas_existentes(relacoes) -%}
{%- set quantidades = [
    'qt_mat_bas', 'qt_mat_inf', 'qt_mat_inf_cre', 'qt_mat_inf_pre',
    'qt_mat_fund', 'qt_mat_fund_ai', 'qt_mat_fund_af', 'qt_mat_med',
    'qt_mat_prof', 'qt_mat_eja', 'qt_mat_esp', 'qt_mat_esp_cc', 'qt_mat_esp_ce',
    'qt_mat_inf_int', 'qt_mat_inf_cre_int', 'qt_mat_inf_pre_int',
    'qt_mat_fund_int', 'qt_mat_fund_ai_int', 'qt_mat_fund_af_int', 'qt_mat_med_int',
    'qt_doc_bas', 'qt_tur_bas'
] -%}

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
    _dbt_source_relation                               as _tabela_bronze
from uniao
