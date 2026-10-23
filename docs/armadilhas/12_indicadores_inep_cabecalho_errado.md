# Armadilha 12 — Nos indicadores do INEP por escola, o cabeçalho técnico às vezes mente

Os indicadores educacionais por escola (rendimento, distorção idade-série, alunos por turma, horas-aula,
formação, regularidade e esforço docente, complexidade de gestão, INSE) vêm em planilhas com linhas de
título, rótulos em três níveis (grupo / etapa / série) e, por último, uma linha de nomes técnicos
(`TAP_F14`, `FUN_AI_CAT_0`...). O natural seria confiar nos nomes técnicos. Em pelo menos dois casos
isso produz um dado errado sem nenhum erro aparente.

## 1. Código e nome trocados (ATU 2016–2018)

O cabeçalho manteve a ordem de 2015 (`NO_MUNICIPIO, CO_MUNICIPIO, NO_ENTIDADE, CO_ENTIDADE`), mas os
dados vieram na ordem nova (código antes do nome). A coluna chamada `CO_ENTIDADE` traz o **nome** da
escola. Lido pelo nome, o arquivo tem 0 escolas; lido "consertando" só o filtro, tem 178 mil escolas com
código e nome trocados — e o join com o Censo falha em silêncio.

**Correção (bronze):** antes de escolher a coluna-chave, o carregador olha as primeiras 500 linhas. Se a
coluna "código" não tem cara de código (8 dígitos para escola, 7 para município) e a coluna "nome" tem
(menos de 50% contra mais de 90%), troca os rótulos e registra `CORREÇÃO:` no log.

## 2. Nomes técnicos deslocados em relação aos dados (Rendimento 2018–2020 e ATU 2018)

Em 2018, `TAP_F04` (5º ano) aparece logo depois de `TAP_F14` (anos iniciais), e todos os nomes seguintes
ficam uma posição à frente. Os **rótulos** (texto acima) continuam na ordem certa. Qual dos dois descreve
o dado? Contando escolas com `--` (etapa não oferecida):

| arquivo | coluna | rótulo | escolas com `--` |
|---|---|---|---|
| 2017 | `tap_f58` | Anos Finais | 75.459 |
| 2017 | `tap_f04` | 5º Ano | 37.439 |
| 2018 | `tap_f04` (posição 12) | Anos Finais | 72.982 |
| 2018 | `tap_f58` (posição 13) | 1º Ano | 33.739 |

A coluna de 2018 chamada `tap_f04` se comporta como anos finais, não como 5º ano: **o dado segue o
rótulo; o nome técnico está errado.** Usar o nome faria a "aprovação nos anos finais" de 2018–2020 ser,
na verdade, a de outra série — um degrau falso no meio da série histórica.

**Correção (silver):** o de-para das colunas é feito pelo **rótulo e pela posição**, guardados pela bronze
em `bronze.ind_colunas`, não pelo nome técnico. O modelo `stg_ind__mapa_colunas` registra, para cada coluna de
cada arquivo, a etapa que o rótulo indica e a que o nome indicaria. Na base real, eles divergem em quatro
arquivos — rendimento 2018, 2019 e 2020 (18 colunas cada) e ATU 2018 (6 colunas) — e só neles.

**Prova na base real:** o teste `assert_rendimento_soma_100` exige aprovação + reprovação + abandono = 100 em
cada escola, etapa e ano. Ele passa em todos os 12,3 milhões de linhas de 2015–2025, inclusive 2018–2020; se
alguma coluna tivesse sido lida na etapa errada, a soma quebraria em milhares de escolas.

## Outras características (não são erro, mas exigem cuidado)

- Cada zip traz o mesmo conteúdo em `.xlsx` e `.ods`, e um `.txt` com o md5 oficial. Três arquivos não
  conferem com o próprio `.txt` (ATU 2022, HAD 2020, HAD 2021); o tamanho bate com o anunciado pelo
  servidor e a planilha abre normalmente, então o mais provável é o `.txt` desatualizado. Ficam marcados
  em `meta.carga_arquivo.md5_oficial_ok = false`.
- Os nomes técnicos mudam de geração: até 2018/2020 `tap_f14`, `mird`, `dependad`, `pk_cod_entidade`;
  depois `1_cat_fun_ai`, `edu_bas_cat_0`, `no_dependencia`, `co_entidade`. O ano da troca varia por
  indicador (2019 na maioria; 2021 no rendimento).
- `--` é ausência de dado (etapa não oferecida ou sigilo), não zero.
- A cobertura muda: o HAD tem ~152 mil escolas em 2016–2021 e ~173 mil a partir de 2022; o TDI de 2015 tem
  179 mil escolas e o de 2016, 140 mil. Contar escolas entre anos sem olhar isso cria tendência falsa.
- O INSE 2013 (edição 2011–2013) e o de 2015 usam metodologia anterior, com escala ~0–100 e classificação
  própria — sete níveis nominais em 2013 ("Muito Baixo" a "Muito Alto"), "Grupo 1–6" em 2015 — diferentes das
  edições de 2019 em diante ("Nível I–VIII", escala do SAEB). O INEP avisa que não são comparáveis.
- A média de alunos por turma passa de 100 em cerca de 60 escolas por ano (máximo de 1.270 em 2025). São os
  valores publicados; a gold os mantém e o teste de faixa só avisa.
