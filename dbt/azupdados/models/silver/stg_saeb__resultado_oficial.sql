-- Médias oficiais do SAEB (TS_BRASIL e TS_UF), tipadas. Uma linha por recorte publicado × série × disciplina.
-- coluna MEDIA_<série>_<disciplina>: série 2, 5, 9, 12 (3ª EM), 13 (4ª EM) e 14 (ensino médio, as duas juntas).
select
    ano::int                                  as ano_saeb,
    abrangencia,
    nullif(co_uf, '')::numeric::int           as co_uf,
    dependencia_adm,
    localizacao,
    capital,
    split_part(coluna, '_', 2)::int           as serie_saeb_oficial,
    split_part(coluna, '_', 3)                as disciplina,
    valor::numeric                            as media_oficial
from {{ source('bronze', 'saeb_resultado_oficial') }}
where coluna ~ '^MEDIA_[0-9]+_[A-Z]+$'
  and valor ~ '^-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
