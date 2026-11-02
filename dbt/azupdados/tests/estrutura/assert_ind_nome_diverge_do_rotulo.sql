{# Auditoria (armadilha 12): colunas cujo nome técnico indica uma etapa e o rótulo, outra. A silver usa o
   rótulo; este teste só lista os arquivos afetados, para a documentação acompanhar o dado. #}
{{ config(severity='warn') }}
select sigla, ano_censo, count(*) as colunas_divergentes,
       string_agg(nome_tecnico || '→' || etapa, ', ' order by posicao) as exemplos
from {{ ref('stg_ind__mapa_colunas') }}
where not eh_identificacao and etapa_pelo_nome is distinct from etapa
group by sigla, ano_censo
