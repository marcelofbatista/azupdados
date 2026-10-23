# Fixtures sintéticas

Arquivos **inventados** que imitam o layout do `microdados_ed_basica` do INEP (separador `;`, encoding LATIN1),
usados nos testes e no CI. Eles reproduzem de propósito as armadilhas 01 (sentinela 88888), 02 (coluna que
só existe em um dos anos) e 06 (inteiro exportado como `12.0`). Não são dados reais.

`sedap/tipo_deficiencia_2024_sintetico.json` imita a resposta da API do SEDAP+ (linhas + estatísticas de privacidade diferencial). Os totais ficam de propósito ~2,6% acima do Censo sintético, como acontece com o dado real (armadilha 09). Também inventado.

`indicadores/` imita as planilhas dos indicadores educacionais do INEP por escola (rendimento, distorção idade-série,
alunos por turma, horas-aula, formação, esforço e regularidade docente, complexidade de gestão, INSE), geradas por
`indicadores/gerar_fixtures.py`. Reproduzem de propósito a armadilha 12: no ATU 2017, os rótulos de código e nome da
escola vêm trocados no cabeçalho; no rendimento 2018 e no ATU 2017, os nomes técnicos vêm deslocados em relação aos
dados. Inventadas.
