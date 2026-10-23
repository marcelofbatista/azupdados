{# SILVER — indicador INEP por escola (TDI): escola × ano × etapa, uma coluna por medida. Etapa e medida vêm do RÓTULO (armadilha 12). #}
-- depends_on: {{ source('bronze', 'ind_colunas') }}
{{ ind_por_escola('TDI') }}
