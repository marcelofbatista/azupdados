# Fixtures sintéticas

Arquivos **inventados** que imitam o layout do `microdados_ed_basica` do INEP (separador `;`, encoding LATIN1),
usados nos testes e no CI. Eles reproduzem de propósito as armadilhas 01 (sentinela 88888), 02 (coluna que
só existe em um dos anos) e 06 (inteiro exportado como `12.0`). Não são dados reais.

`sedap/tipo_deficiencia_2024_sintetico.json` imita a resposta da API do SEDAP+ (linhas + estatísticas de privacidade diferencial). Os totais ficam de propósito ~2,6% acima do Censo sintético, como acontece com o dado real (armadilha 09). Também inventado.
