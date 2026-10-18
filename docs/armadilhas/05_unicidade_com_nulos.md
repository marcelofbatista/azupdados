# 05 — Teste de unicidade só sobre valores preenchidos esconde duplicatas

**Problema.** O teste `unique` padrão ignora nulos. Se uma chave composta tem um componente nulo,
duas linhas "iguais" passam pelo teste.

**Correção.** O teste `unicidade_com_nulos` trata nulo como um valor (marcador explícito) antes de
agrupar, e falha se qualquer combinação aparecer mais de uma vez.
