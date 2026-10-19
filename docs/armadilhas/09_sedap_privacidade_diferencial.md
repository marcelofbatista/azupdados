# Armadilha 09 — Números do SEDAP+ não são contagens exatas

## O que é

O SEDAP+ (Serviço de Acesso a Dados Protegidos do INEP) dá acesso a variáveis que os microdados
abertos não publicam — entre elas, o **tipo de deficiência** de cada matrícula. Em troca, toda consulta
passa por **privacidade diferencial**: o resultado vem com ruído calibrado, e a resposta traz, para cada
coluna, a taxa de ruído e um intervalo de confiança de 95%.

Dois erros aparecem quando se trata o número do SEDAP+ como contagem do Censo:

1. **Contar o estudante duas vezes.** A tabela de matrículas tem um registro para a escolarização e outros
   para o Atendimento Educacional Especializado (AEE) e para turmas sem etapa (atividade complementar,
   itinerário formativo). Sem filtro, os tipos de deficiência saem **30% a 53% acima** da Sinopse. Os filtros
   `IN_ESPECIAL_EXCLUSIVA IS NOT NULL AND TP_ETAPA_ENSINO IS NOT NULL` deixam só a escolarização.
2. **Ler o total absoluto como exato.** Mesmo com o filtro certo, o mesmo recorte consultado de duas formas
   dá totais diferentes.

## Medido em 2024, rede estadual do DF

| Consulta | Matrículas | Educação especial |
|---|---|---|
| Censo Escolar aberto (`qt_mat_bas`, `qt_mat_esp`) | 418.041 | 19.074 |
| SEDAP+, agrupado por UF × dependência | 429.060 (+2,6%) | 19.578 (+2,6%) |
| SEDAP+, agrupado por UF × dependência × etapa, somado | 416.129 (−0,5%) | 19.054 (−0,1%) |

Não há população a mais: o desvio é da consulta, não do dado. E ele é **o mesmo em todas as colunas do
grupo** (+2,6% no total e na educação especial; −1,0% e −1,0% na rede federal), o que indica um fator
multiplicativo comum ao grupo.

## Por que duas consultas do mesmo recorte dão totais diferentes

Em 2024, a consulta por UF × dependência deu a rede estadual de SP, PR e SC **28% a 39% acima** do Censo
aberto. A consulta por etapa, somada, ficou a ~1% dele. Em todas as UFs testadas, a diferença entre as
duas é **2,0 vezes** o número de matrículas sem etapa (`TP_ETAPA_ENSINO` nulo):

| Rede estadual 2024 | Excesso da consulta por UF | Matrículas sem etapa (consulta por etapa) | Razão |
|---|---|---|---|
| SC | 216.808 | 104.559 | 2,07 |
| PR | 353.085 | 177.907 | 1,98 |
| SP | 1.037.482 | 510.069 | 2,03 |
| DF | 12.931 | 6.429 | 2,01 |

A explicação é a **limitação de contribuição** da privacidade diferencial. A unidade protegida é o aluno,
e cada aluno só pode contribuir para um número limitado de grupos. O aluno que tem uma matrícula regular
e outra numa turma sem etapa (atividade complementar, itinerário formativo em turma própria):

- na consulta por UF, cai duas vezes **no mesmo grupo** e é contado duas vezes;
- na consulta por etapa, cai em **dois grupos**, e só um deles é mantido — ao acaso, metade das vezes o
  grupo "sem etapa". Por isso o grupo sem etapa mostra só metade das matrículas extras.

O filtro `TP_ETAPA_ENSINO IS NOT NULL` elimina as matrículas extras antes da agregação. **Lição geral:**
no SEDAP+, o total de um recorte depende da forma da consulta sempre que um aluno pode cair em mais de
um grupo. Defina a população com filtros explícitos, não pelo agrupamento.

## Como o `azupdados` trata

- **Grão grosso**: só UF × dependência × ano. Em escola ou município o ruído destrói o dado.
- **Proporção do SEDAP+, escala do dado aberto**: `qt_estimada = (tipo ÷ total da educação especial no
  SEDAP+) × qt_mat_esp do Censo aberto`. O fator comum se cancela na razão e o total sempre fecha com o
  INEP. O número protegido (`qt_sedap`) fica ao lado, para auditoria.
- **Teste `assert_sedap_total_proximo_do_censo_aberto`** (severidade *warn*): avisa quando o total do
  SEDAP+ se afasta mais de 5% do Censo aberto num grupo com 1.000+ matrículas.
- **Uma consulta por ano.** Repetir a mesma consulta para tirar a média do ruído consome o orçamento de
  privacidade do projeto e contraria o propósito do mecanismo.
- **Valores negativos.** Na série nacional 2015–2024, 2.145 das 10.700 células por tipo vieram negativas
  — todas onde a contagem real é pequena (tipo raro, rede pequena, UF pequena). O valor bruto é mantido:
  cortar em zero antes de somar puxa a soma para cima. `qt_estimada` só é calculada quando o grupo tem
  ao menos 500 matrículas na educação especial (`eh_celula_confiavel`), e aí é cortada em zero.
- A soma dos tipos excede o total da educação especial: um estudante pode ter mais de um tipo.

## Pendente

Validar `qt_estimada` contra a Sinopse Estatística por tipo em mais de uma UF antes de declarar o método
fechado. No DF 2024, o TEA bruto do SEDAP+ ficou 2,9% abaixo da Sinopse, e o ancorado, ~5% abaixo.
