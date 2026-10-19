# Armadilha 09 — Números do SEDAP+ não são contagens exatas

## O que é

O SEDAP+ (Serviço de Acesso a Dados Protegidos do INEP) dá acesso a variáveis que os microdados
abertos não publicam — entre elas, o **tipo de deficiência** de cada matrícula. Em troca, toda consulta
passa por **privacidade diferencial**: o resultado vem com ruído calibrado, e a resposta traz, para cada
coluna, a taxa de ruído e um intervalo de confiança de 95%.

Dois erros aparecem quando se trata o número do SEDAP+ como contagem do Censo:

1. **Contar o estudante duas vezes.** A tabela de matrículas tem um registro para a escolarização e outro
   para o Atendimento Educacional Especializado (AEE) no contraturno. Sem filtro, os tipos de deficiência
   saem **30% a 53% acima** da Sinopse Estatística. O filtro `IN_ESPECIAL_EXCLUSIVA IS NOT NULL` deixa só a
   escolarização.
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
