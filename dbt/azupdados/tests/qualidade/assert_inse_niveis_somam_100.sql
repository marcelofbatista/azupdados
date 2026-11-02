{# Regra de negócio: os percentuais de alunos por nível do INSE (2019 em diante) somam 100 em cada escola.
   Foi este teste que decidiu um alerta do teste de esquema: no INSE 2023 três colunas pc_nivel caem de 100% para
   66% de valores numéricos. Com vazio = 0, todas as 69.756 escolas somam 100 — era formato, não dado faltando.
   Tolerância de 0,5 ponto para o arredondamento dos percentuais publicados. #}
{{ config(severity='warn') }}
select ano_saeb, co_entidade,
       pc_nivel_1 + pc_nivel_2 + pc_nivel_3 + pc_nivel_4 + pc_nivel_5 + pc_nivel_6 + pc_nivel_7 + pc_nivel_8 as soma
from {{ ref('stg_ind__inse') }}
where eh_metodologia_saeb and pc_nivel_1 is not null
  and abs(pc_nivel_1 + pc_nivel_2 + pc_nivel_3 + pc_nivel_4 + pc_nivel_5 + pc_nivel_6 + pc_nivel_7 + pc_nivel_8 - 100) > 0.5
