{#
  GOLD — Proficiência no SAEB, agregada a partir dos microdados por aluno (PySpark).
  Grão: edição × série × UF × rede × localização × área × disciplina × cor/raça × sexo × nível INSE ×
  situação no Censo.

  Medidas são SOMAS (aditivas). A média ponderada de qualquer recorte é
      sum(soma_peso_prof) / sum(soma_peso)
  `proficiencia_media` é essa conta já feita no grão da linha: serve para ler a linha, NUNCA para somar
  ou tirar média de médias.

  Não há escola nem município: no arquivo público do aluno o INEP substitui os dois por códigos fictícios,
  renumerados a cada edição (ver docs/armadilhas/13). Nota por escola vem do IDEB (fato_ideb_escola_ano).
#}
select
    {{ dbt_utils.generate_surrogate_key(['a.ano', 'a.arquivo', 'a.id_serie', 'a.id_uf', 'a.in_publica',
        'a.id_localizacao', 'a.id_area', 'a.disciplina', 'a.cor_raca_censo', 'a.sexo_codigo', 'a.nivel_inse',
        'a.in_situacao_censo']) }}                                       as fato_saeb_proficiencia_ano_sk,
    a.ano                                                                as ano_saeb,
    a.arquivo                                                            as arquivo_saeb,
    a.id_serie                                                           as serie_saeb,
    a.id_uf                                                              as co_uf,
    case a.in_publica when 1 then 'pública' when 0 then 'privada' end    as rede,
    a.id_localizacao                                                     as tp_localizacao,
    case a.id_area when 1 then 'capital' when 2 then 'interior' end      as area,
    a.disciplina,
    c.cor_raca_sk,
    a.cor_raca_censo,
    s.sexo_sk,
    a.sexo_codigo,
    a.nivel_inse,
    a.in_situacao_censo,
    a.n_alunos,
    a.n_presentes,
    a.n_com_proficiencia,
    a.soma_peso,
    a.soma_peso_prof,
    a.soma_peso_prof2,
    a.soma_peso_prof / nullif(a.soma_peso, 0)                            as proficiencia_media
from {{ source('spark', 'saeb_agregado') }} a
left join {{ ref('dim_cor_raca') }} c on c.codigo_educacenso = a.cor_raca_censo
left join {{ ref('dim_sexo') }} s on s.codigo_inep = a.sexo_codigo
