{#
  GOLD — dimensão de tempo no grão ano (o Censo Escolar é anual).
  Recortes de leitura que se repetem nas análises, para não reescrevê-los em cada consulta:
  - pandemia: 2020 e 2021 foram anos letivos com escolas fechadas ou em ensino remoto em todo o país;
    2022 é o primeiro ano de retorno presencial generalizado.
  - mandatos: os governos federal e estaduais têm o mesmo ciclo (2015–2018, 2019–2022, 2023–2026);
    os municipais, outro (2013–2016, 2017–2020, 2021–2024, 2025–2028). Só o período, sem nomes:
    a política educacional da escola municipal e da estadual responde a ciclos diferentes.
  - SAEB/IDEB: edições bienais, em anos ímpares.
#}
select
    ano                                                         as ano_censo,
    (ano / 10) * 10                                             as decada,
    ano in (2010, 2022)                                         as eh_ano_censo_demografico,
    ano < 2020                                                  as eh_pre_pandemia,
    ano in (2020, 2021)                                         as eh_ano_pandemia,
    ano >= 2022                                                 as eh_pos_pandemia,
    case when ano < 2020 then 'pré-pandemia' when ano <= 2021 then 'pandemia' else 'pós-pandemia' end
                                                                as fase_pandemia,
    (2015 + floor((ano - 2015) / 4.0)::int * 4)::text || '–' || (2018 + floor((ano - 2015) / 4.0)::int * 4)::text
                                                                as mandato_federal_estadual,
    (2013 + floor((ano - 2013) / 4.0)::int * 4)::text || '–' || (2016 + floor((ano - 2013) / 4.0)::int * 4)::text
                                                                as mandato_municipal,
    ano % 2 = 1 and ano >= 2005                                 as eh_edicao_saeb
from generate_series(2007, 2030) as ano
