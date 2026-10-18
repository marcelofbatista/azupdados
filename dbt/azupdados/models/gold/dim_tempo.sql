-- GOLD — dimensão de tempo no grão ano (o Censo Escolar é anual).
select
    ano                                   as ano_censo,
    (ano / 10) * 10                       as decada,
    ano in (2010, 2022)                   as eh_ano_censo_demografico
from generate_series(2007, 2030) as ano
