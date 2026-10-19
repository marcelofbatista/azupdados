{# SILVER — estatísticas de privacidade diferencial devolvidas pelo SEDAP+, por ano e métrica. #}
select
    {{ para_inteiro('ano') }}               as ano_censo,
    lower(metrica)                          as metrica,
    coluna_inep,
    funcao,
    nullif(taxa_ruido, '')::numeric         as taxa_ruido,
    nullif(media, '')::numeric              as media_por_grupo,
    nullif(mediana, '')::numeric            as mediana_por_grupo,
    nullif(nivel_confianca, '')::numeric    as nivel_confianca,
    nullif(ic_inferior, '')::numeric        as ic_inferior,
    nullif(ic_superior, '')::numeric        as ic_superior
from {{ source('bronze', 'sedap_ee_tipo_estatisticas') }}
