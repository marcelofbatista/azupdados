{#
  Indicadores educacionais do INEP por escola (bronze.ind_<sigla>_<ano>).

  Armadilha 12: o nome técnico das colunas às vezes não descreve o dado (rendimento 2018–2020 e ATU
  2016–2018 têm os nomes deslocados em relação aos dados). Por isso a etapa e a medida de cada coluna são
  decididas pelo RÓTULO da planilha (texto acima do cabeçalho técnico, guardado em bronze.ind_colunas).
  O nome técnico só é usado para comparar: `etapa_pelo_nome` × `etapa` no modelo stg_ind__mapa_colunas.
#}

{% macro ind_identificacao() %}{% do return(['ano', 'nu_ano_censo', 'no_regiao', 'co_uf', 'sg_uf', 'sigla',
    'co_municipio', 'pk_cod_municipio', 'no_municipio', 'co_entidade', 'pk_cod_entidade', 'no_entidade',
    'tipoloca', 'no_categoria', 'dependad', 'no_dependencia']) %}{% endmacro %}

{% macro ind_chaves_escola() %}{% do return(['co_entidade', 'pk_cod_entidade', 'co_escola', 'id_escola',
    'cod_escola', 'cod_entidade']) %}{% endmacro %}

{# Medidas (slots) de cada indicador, na ordem das colunas da silver. #}
{% macro ind_slots(sigla) %}
  {%- set s = {
      'REND': ['taxa_aprovacao', 'taxa_reprovacao', 'taxa_abandono'],
      'TDI': ['taxa_distorcao'],
      'ATU': ['media_alunos_turma'],
      'HAD': ['media_horas_aula'],
      'AFD': ['pct_grupo_1', 'pct_grupo_2', 'pct_grupo_3', 'pct_grupo_4', 'pct_grupo_5'],
      'IED': ['pct_nivel_1', 'pct_nivel_2', 'pct_nivel_3', 'pct_nivel_4', 'pct_nivel_5', 'pct_nivel_6'],
      'IRD': ['ird_media'],
      'ICG': ['icg_nivel'],
  } -%}
  {% do return(s[sigla]) %}
{% endmacro %}

{% macro ind_sem_acento(texto) %}
  {#- namespace: no Jinja, variável alterada dentro de um for não sobrevive ao laço -#}
  {%- set ns = namespace(t=(texto or '') | lower) -%}
  {%- for a, b in [('á','a'),('à','a'),('â','a'),('ã','a'),('é','e'),('ê','e'),('í','i'),('ó','o'),('ô','o'),
                   ('õ','o'),('ú','u'),('ü','u'),('ç','c')] -%}
    {%- set ns.t = ns.t | replace(a, b) -%}
  {%- endfor -%}
  {% do return(ns.t) %}
{% endmacro %}

{# Etapa a partir do rótulo (texto legível). A ordem das regras importa: "Ensino Médio / Anos Finais"
   (formação docente) é médio; "Anos Iniciais (1º ao 5º Ano)" (rendimento 2015) é anos iniciais. #}
{% macro ind_etapa_do_rotulo(rotulo) %}
  {%- set re = modules.re -%}
  {%- set partes = [] -%}
  {%- for p in (rotulo or '').split(' / ') -%}
    {%- if 'segundo a' not in ind_sem_acento(p) %}{% do partes.append(p) %}{% endif -%}
  {%- endfor -%}
  {%- set r = ind_sem_acento(partes | join(' / ')) -%}
  {%- set etapa = 'basica' -%}
  {%- if 'multietapa' in r or 'unificada' in r -%}{%- set etapa = 'fun_multietapa' -%}
  {%- elif re.search('\\beja\\b', r) -%}{%- set etapa = 'eja_med' if 'medio' in r else 'eja_fun' -%}
  {%- elif 'creche' in r -%}{%- set etapa = 'inf_creche' -%}
  {%- elif 'pre-escola' in r or 'pre escola' in r -%}{%- set etapa = 'inf_pre' -%}
  {%- elif 'infantil' in r -%}{%- set etapa = 'inf' -%}
  {%- elif 'medio' in r -%}
    {%- set m = re.search('([1-4])\\s*[ªa]\\s*serie', r) -%}
    {%- if 'seriado' in r -%}{%- set etapa = 'med_ns' -%}
    {%- elif m -%}{%- set etapa = 'med_0' ~ m.group(1) -%}
    {%- else -%}{%- set etapa = 'med' -%}{%- endif -%}
  {%- elif 'fundamental' in r -%}
    {%- set m = re.search('([1-9])\\s*[º°o]\\s*ano', r) -%}
    {%- if 'anos iniciais' in r -%}{%- set etapa = 'fun_ai' -%}
    {%- elif 'anos finais' in r -%}{%- set etapa = 'fun_af' -%}
    {%- elif m -%}{%- set etapa = 'fun_0' ~ m.group(1) -%}
    {%- else -%}{%- set etapa = 'fun' -%}{%- endif -%}
  {%- endif -%}
  {% do return(etapa) %}
{% endmacro %}

{# Medida (slot) a partir da sigla e do rótulo. Grupo/Nível n (formação e esforço docente) viram slots. #}
{% macro ind_slot_do_rotulo(sigla, rotulo) %}
  {%- set re = modules.re -%}
  {%- set r = ind_sem_acento(rotulo) -%}
  {%- set ultimo = ind_sem_acento((rotulo or '').split(' / ')[-1]) -%}
  {%- set cat = re.search('(grupo|nivel)\\s*([1-9])\\s*$', ultimo) -%}
  {%- set slot = none -%}
  {%- if sigla == 'REND' -%}
    {%- if 'reprova' in r %}{% set slot = 'taxa_reprovacao' %}{% elif 'abandono' in r %}{% set slot = 'taxa_abandono' -%}
    {%- elif 'aprova' in r %}{% set slot = 'taxa_aprovacao' %}{% endif -%}
  {%- elif sigla == 'AFD' and cat -%}{%- set slot = 'pct_grupo_' ~ cat.group(2) -%}
  {%- elif sigla == 'IED' and cat -%}{%- set slot = 'pct_nivel_' ~ cat.group(2) -%}
  {%- elif sigla in ('TDI', 'ATU', 'HAD', 'IRD', 'ICG') -%}{%- set slot = ind_slots(sigla)[0] -%}
  {%- endif -%}
  {% do return(slot) %}
{% endmacro %}

{# Etapa deduzida do NOME técnico (só para comparação; ver armadilha 12). #}
{% macro ind_etapa_do_nome(sigla, nome) %}
  {%- set re = modules.re -%}
  {%- set n = nome or '' -%}
  {%- set nucleo = none -%}
  {%- set m_rend = re.match('^[123]_cat_(.+)$', n) -%}
  {%- set m_novo = re.match('^(.+)_cat_[0-9]$', n) -%}
  {%- set m_velho = re.match('^(tap|tre|tab|tdi|atu|had|afd|ied)_(.+)$', n) -%}
  {%- if m_rend %}{% set nucleo = m_rend.group(1) -%}
  {%- elif m_novo %}{% set nucleo = m_novo.group(1) -%}
  {%- elif m_velho -%}
    {%- set nucleo = m_velho.group(2) -%}
    {%- if m_velho.group(1) in ('afd', 'ied') %}{% set nucleo = nucleo[:-1] %}{% endif -%}
  {%- elif n in ('mird', 'icg', 'complex') %}{% set nucleo = 'edu_bas' -%}
  {%- endif -%}
  {%- set fixo = {'fun': 'fun', 'fun_ai': 'fun_ai', 'fun_af': 'fun_af', 'f14': 'fun_ai', 'f58': 'fun_af',
                  'med': 'med', 'med_ns': 'med_ns', 'mns': 'med_ns', 'ed_inf': 'inf', 'inf': 'inf',
                  'cre': 'inf_creche', 'pre': 'inf_pre', 'mult_eta': 'fun_multietapa',
                  'unificada': 'fun_multietapa', 'eja_fun': 'eja_fun', 'ejaf': 'eja_fun',
                  'eja_med': 'eja_med', 'ejam': 'eja_med', 'edu_bas': 'basica'} -%}
  {%- set etapa = none -%}
  {%- if nucleo in fixo %}{% set etapa = fixo[nucleo] -%}
  {%- elif nucleo and re.match('^f0[0-8]$', nucleo) %}{% set etapa = 'fun_0' ~ (nucleo[2] | int + 1) -%}
  {%- elif nucleo and re.match('^fun_0[1-9]$', nucleo) %}{% set etapa = nucleo -%}
  {%- elif nucleo and re.match('^(m|med_)0[1-4]$', nucleo) %}{% set etapa = 'med_0' ~ nucleo[-1] -%}
  {%- endif -%}
  {% do return(etapa) %}
{% endmacro %}

{# Lê bronze.ind_colunas e classifica cada coluna. Fora da execução (parse/compile), devolve lista vazia. #}
{% macro ind_mapa(siglas) %}
  {%- set saida = [] -%}
  {%- if execute -%}
    {%- set consulta -%}
      select sigla, ano, posicao, nome_tecnico, coalesce(rotulo, '') as rotulo, tabela
      from {{ source('bronze', 'ind_colunas') }}
      where sigla in ('{{ siglas | join("', '") }}')
      order by sigla, ano, posicao
    {%- endset -%}
    {%- set linhas = run_query(consulta) -%}
    {%- for r in linhas -%}
      {%- set eh_id = r['nome_tecnico'] in ind_identificacao() + ind_chaves_escola() -%}
      {%- set slot = none if eh_id else ind_slot_do_rotulo(r['sigla'], r['rotulo']) -%}
      {%- set etapa = none if eh_id else ind_etapa_do_rotulo(r['rotulo']) -%}
      {%- set pelo_nome = none if eh_id else ind_etapa_do_nome(r['sigla'], r['nome_tecnico']) -%}
      {%- do saida.append({'sigla': r['sigla'], 'ano': r['ano'], 'posicao': r['posicao'],
            'nome': r['nome_tecnico'], 'rotulo': r['rotulo'], 'tabela': r['tabela'], 'eh_id': eh_id,
            'slot': slot, 'etapa': etapa, 'etapa_pelo_nome': pelo_nome}) -%}
    {%- endfor -%}
  {%- endif -%}
  {% do return(saida) %}
{% endmacro %}

{# Texto do INEP → número. '--' (ausente) e vazio viram nulo; "Nível 3" (ICG) vira 3. #}
{% macro ind_numero(col) -%}
    case
        when trim({{ col }}) ~ '^-?[0-9]+([.,][0-9]+)?([eE]-?[0-9]+)?$' then replace(trim({{ col }}), ',', '.')::numeric
        when trim({{ col }}) ~* '^n.vel\s*[0-9]+$' then (regexp_match({{ col }}, '([0-9]+)'))[1]::numeric
    end
{%- endmacro %}

{% macro ind_valor_ausente(col) -%}
    ({{ col }} is null or trim({{ col }}) in ('', '-', '--'))
{%- endmacro %}

{#
  Silver de um indicador: uma linha por escola × ano × etapa, uma coluna por medida (slot).
  Para cada tabela bronze, um LATERAL VALUES lista (etapa, coluna da medida 1, coluna da medida 2, ...),
  montado a partir do mapa por rótulo. Duas colunas para a mesma etapa e medida na mesma tabela = erro.
  `qt_valores_invalidos` conta textos que não são ausência nem número (devem ser zero).
#}
{% macro ind_por_escola(sigla) %}
{%- set slots = ind_slots(sigla) -%}
{%- set mapa = ind_mapa([sigla]) -%}
{%- set tabelas = {} -%}
{%- for c in mapa -%}
  {%- if c['tabela'] not in tabelas %}{% do tabelas.update({c['tabela']: {'ano': c['ano'], 'chave': none, 'etapas': {}}}) %}{% endif -%}
  {%- set t = tabelas[c['tabela']] -%}
  {%- if c['nome'] in ind_chaves_escola() and t['chave'] is none %}{% do t.update({'chave': c['nome']}) %}{% endif -%}
  {%- if not c['eh_id'] and c['slot'] -%}
    {%- if c['etapa'] not in t['etapas'] %}{% do t['etapas'].update({c['etapa']: {}}) %}{% endif -%}
    {%- if c['slot'] in t['etapas'][c['etapa']] -%}
      {{ exceptions.raise_compiler_error(c['tabela'] ~ ': duas colunas para ' ~ c['etapa'] ~ '/' ~ c['slot'] ~ ' ('
           ~ t['etapas'][c['etapa']][c['slot']] ~ ' e ' ~ c['nome'] ~ '). Ver armadilha 12.') }}
    {%- endif -%}
    {%- do t['etapas'][c['etapa']].update({c['slot']: c['nome']}) -%}
  {%- endif -%}
{%- endfor %}
{%- if tabelas | length == 0 %}
select null::int as ano_censo, null::bigint as co_entidade, null::text as etapa,
       {% for s in slots %}null::numeric as {{ s }}, {% endfor %}0 as qt_valores_invalidos
where false
{%- endif %}
{%- for tabela, t in tabelas.items() %}
{%- if t['chave'] is none %}{{ exceptions.raise_compiler_error(tabela ~ ': sem coluna de código da escola') }}{% endif %}
select {{ t['ano'] }}::int as ano_censo, co_entidade, etapa,
       {% for s in slots %}{{ ind_numero('v_' ~ s) }} as {{ s }},
       {% endfor %}(
         {%- for s in slots %}(not {{ ind_valor_ausente('v_' ~ s) }} and {{ ind_numero('v_' ~ s) }} is null)::int{{ ' + ' if not loop.last }}{% endfor -%}
       ) as qt_valores_invalidos
from (
    select nullif(trim(t.{{ adapter.quote(t['chave']) }}), '')::bigint as co_entidade, v.*
    from {{ tabela }} t
    cross join lateral (values
    {%- for etapa, cols in t['etapas'].items() %}
        ('{{ etapa }}'{% for s in slots %}, {% if s in cols %}t.{{ adapter.quote(cols[s]) }}{% else %}null::text{% endif %}{% endfor %}){{ ',' if not loop.last }}
    {%- endfor %}
    ) as v(etapa{% for s in slots %}, v_{{ s }}{% endfor %})
) x
where not ({% for s in slots %}{{ ind_valor_ausente('v_' ~ s) }}{{ ' and ' if not loop.last }}{% endfor %})
{% if not loop.last %}union all{% endif %}
{%- endfor %}
{%- endmacro %}

{# Gold de um indicador por escola: liga à dim_escola (left: escola que não está no Censo carregado mantém
   o código) e à dim_etapa_indicador. `com_etapa=false` para indicadores da escola toda (IRD, ICG). #}
{% macro ind_fato(nome_fato, stg, sigla, com_etapa=true) -%}
select
    {{ dbt_utils.generate_surrogate_key(['s.co_entidade', 's.ano_censo'] + (['s.etapa'] if com_etapa else [])) }} as {{ nome_fato }}_sk,
    e.escola_sk,
    s.co_entidade,
    s.ano_censo,
    {% if com_etapa %}d.etapa_indicador_sk,
    {% endif %}{% for s in ind_slots(sigla) %}s.{{ s }}{{ ',' if not loop.last }}
    {% endfor %}
from {{ ref(stg) }} s
left join {{ ref('dim_escola') }} e on e.co_entidade = s.co_entidade
{% if com_etapa %}left join {{ ref('dim_etapa_indicador') }} d on d.codigo = s.etapa{% endif %}
{%- endmacro %}
