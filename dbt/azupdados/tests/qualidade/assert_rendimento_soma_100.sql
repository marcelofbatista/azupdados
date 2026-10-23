{# Aprovação + reprovação + abandono = 100 (com arredondamento de 1 casa em cada taxa). Linhas que fogem
   indicam coluna lida na etapa errada — foi assim que os nomes deslocados do INEP apareceriam (armadilha 12). #}
{{ config(severity='warn') }}
select ano_censo, co_entidade, etapa_indicador_sk, taxa_aprovacao, taxa_reprovacao, taxa_abandono
from {{ ref('fato_rendimento_escola_ano') }}
where taxa_aprovacao is not null and taxa_reprovacao is not null and taxa_abandono is not null
  and abs(taxa_aprovacao + taxa_reprovacao + taxa_abandono - 100) > 0.5
