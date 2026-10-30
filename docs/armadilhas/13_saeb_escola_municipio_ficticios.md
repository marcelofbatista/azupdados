# Armadilha 13 — No SAEB por aluno, escola e município são códigos fictícios

> **EN summary.** In INEP's public student-level SAEB files, `ID_ESCOLA` and `ID_MUNICIPIO` look like real
> codes (8 and 7 digits) but are not: none of 27.6 million student records matches a school in the School
> Census, and the IDs are renumbered sequentially in every edition. Per-school scores must come from IDEB.

Os arquivos `TS_ALUNO_*` trazem `ID_ESCOLA` (8 dígitos) e `ID_MUNICIPIO` (7 dígitos), exatamente o formato dos
códigos do Censo Escolar e do IBGE. O natural seria juntar com `dim_escola` para ter nota por escola. Não dá.

## A prova (base nacional, 2019, 2021 e 2023)

| verificação | resultado |
|---|---|
| `ID_ESCOLA` com 8 dígitos | 100% dos 27,6 milhões de registros |
| `ID_ESCOLA` que existe no Censo (`gold.dim_escola`, 277.564 escolas) | **0,0%** em todos os 12 arquivos |
| Faixa dos códigos reais (Censo) | 11000023 … 53088034 — os 2 primeiros dígitos são a UF |
| Faixa no SAEB 2019 · 2021 · 2023 (5º ano) | 61250086–61323668 · 61323671–61398209 · 61398210–61471804 |
| `ID_MUNICIPIO` que existe no IBGE | **0,0%** (5.547 códigos distintos, todos na faixa 63xxxxx) |

As faixas são **sequenciais e encadeadas**: 2021 começa logo depois de onde 2019 termina. O INEP renumera as
escolas a cada edição. Consequências:

- não há nota por escola nem por município a partir do arquivo público do aluno;
- não dá nem para seguir a mesma escola de uma edição para outra;
- dentro de uma edição, o código ainda agrupa os alunos da mesma escola (serve para decompor variância
  entre e dentro de escolas, sem saber que escola é).

A UF (`ID_UF`) e a rede (`IN_PUBLICA`) são reais — e é nelas que o `azupdados` agrega.

## O que o azupdados faz

- A bronze guarda os códigos como vieram; a silver **não os carrega**, para que ninguém faça o join errado.
- A gold `fato_saeb_proficiencia_ano` é por UF × rede × localização × área × perfil do aluno.
- Nota por escola vem do IDEB (`fato_ideb_escola_ano`), que o INEP publica com o código real.
- Verificação reproduzível: `make saeb-verificar-escola` e `spark/amostra_ids_saeb.py`.

## Outras características do SAEB por aluno (não são erro, mas exigem cuidado)

- **Sexo:** 2019 não pergunta. Série de nota por sexo começa em 2021. 2023 acrescenta "não quero declarar".
- **2º ano:** não tem questionário (sem cor/raça, sexo, INSE) e usa escala própria, centrada em 750.
- **Ciências humanas e da natureza:** amostrais (1,5% a 3,6% dos alunos têm nota). Média só com o peso.
- **Escala ancorada:** a média nacional ponderada de CH, CN e 2º ano sai exatamente 250,00 / 750,00 — é assim
  que o INEP fixa essas escalas, e é um bom teste de que os pesos estão sendo aplicados.
- **INSE do aluno (2021, 2023):** com `IN_INSE = 0` o INEP grava nível 1, que significa "não calculado". A silver
  anula o nível nesses casos.
- **Participação na pandemia:** no ensino médio de 2021, só 61% dos alunos esperados têm nota (75% em 2019).
  Comparar médias de 2021 com outras edições é comparar populações diferentes.
