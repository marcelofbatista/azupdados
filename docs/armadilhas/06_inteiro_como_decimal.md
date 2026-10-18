# 06 — Contagem inteira exportada como "0.0"

**Problema.** Arquivos que passaram por planilhas trazem contagens como `"0.0"` ou `"12.0"`.
O cast direto `TEXT::INTEGER` falha.

**Correção.** A macro `para_inteiro()` passa por `NUMERIC` antes de `INTEGER` e trata string vazia
como nulo.
