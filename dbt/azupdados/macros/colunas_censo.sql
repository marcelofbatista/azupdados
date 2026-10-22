{#
  Catálogo único das colunas do Censo Escolar usadas no projeto, por tema. A silver tipa todas;
  cada fato da gold seleciona o seu tema. Nomes conferidos no cabeçalho real de 2015, 2019 e 2024.
  Colunas que só existem em parte dos anos entram como nulo nos demais (armadilha 02).
#}
{% macro colunas_censo() -%}
{{ return({
  'infra_indicadores': [
    'in_agua_potavel', 'in_agua_rede_publica', 'in_agua_inexistente',
    'in_energia_rede_publica', 'in_energia_inexistente',
    'in_esgoto_rede_publica', 'in_esgoto_inexistente', 'in_lixo_servico_coleta',
    'in_banheiro', 'in_banheiro_pne', 'in_banheiro_ei',
    'in_cozinha', 'in_refeitorio', 'in_alimentacao',
    'in_biblioteca', 'in_biblioteca_sala_leitura', 'in_sala_leitura',
    'in_laboratorio_ciencias', 'in_laboratorio_informatica',
    'in_quadra_esportes', 'in_quadra_esportes_coberta', 'in_parque_infantil',
    'in_patio_coberto', 'in_area_verde', 'in_sala_professor',
    'in_sala_atendimento_especial', 'in_material_ped_edu_esp', 'in_material_ped_bil_surdos',
    'in_internet', 'in_internet_alunos', 'in_internet_aprendizagem', 'in_banda_larga',
    'in_acessibilidade_rampas', 'in_acessibilidade_corrimao', 'in_acessibilidade_elevador',
    'in_acessibilidade_pisos_tateis', 'in_acessibilidade_sinal_sonoro', 'in_acessibilidade_sinal_tatil',
    'in_acessibilidade_sinal_visual', 'in_acessibilidade_vao_livre', 'in_acessibilidade_inexistente',
    'in_local_func_predio_escolar', 'in_predio_compartilhado'
  ],
  'infra_quantidades': [
    'qt_salas_utilizadas', 'qt_salas_utilizadas_dentro', 'qt_salas_utilizadas_fora',
    'qt_salas_utilizadas_acessiveis', 'qt_salas_utiliza_climatizadas',
    'qt_desktop_aluno', 'qt_comp_portatil_aluno', 'qt_tablet_aluno'
  ],
  'docentes_turmas': [
    'qt_doc_bas', 'qt_doc_inf', 'qt_doc_inf_cre', 'qt_doc_inf_pre', 'qt_doc_fund', 'qt_doc_fund_ai',
    'qt_doc_fund_af', 'qt_doc_med', 'qt_doc_prof', 'qt_doc_eja', 'qt_doc_esp', 'qt_doc_esp_cc', 'qt_doc_esp_ce',
    'qt_tur_bas', 'qt_tur_inf', 'qt_tur_fund', 'qt_tur_fund_ai', 'qt_tur_fund_af', 'qt_tur_med',
    'qt_tur_prof', 'qt_tur_eja', 'qt_tur_esp', 'qt_tur_esp_cc', 'qt_tur_esp_ce',
    'qt_tur_inf_int', 'qt_tur_fund_int', 'qt_tur_med_int'
  ],
  'profissionais': [
    'qt_prof_gestao', 'qt_prof_coordenador', 'qt_prof_pedagogia', 'qt_prof_secretario',
    'qt_prof_administrativos', 'qt_prof_servicos_gerais', 'qt_prof_alimentacao', 'qt_prof_seguranca',
    'qt_prof_bibliotecario', 'qt_prof_monitores', 'qt_prof_saude', 'qt_prof_psicologo',
    'qt_prof_fonaudiologo', 'qt_prof_nutricionista', 'qt_prof_assist_social',
    'qt_prof_trad_libras', 'qt_prof_revisor_braille'
  ]
}) }}
{%- endmacro %}
