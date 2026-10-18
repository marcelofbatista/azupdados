# 02 — O layout do Censo Escolar muda entre anos

**Problema.** Colunas são criadas, renomeadas ou extintas de um ano para outro. Um `UNION` ingênuo
quebra, e um SQL escrito para um ano falha silenciosamente em outro.

**Correção.** Cada ano entra na bronze como tabela própria, com o cabeçalho original. A silver une
todas com `dbt_utils.union_relations` e usa a macro `coluna_ou_nulo()`: uma coluna que não existe em
nenhum ano carregado vira nulo explícito em vez de erro de compilação.

**Pendente.** Mapear colunas renomeadas entre anos a partir dos dicionários oficiais.
