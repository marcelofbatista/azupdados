# Armadilha 10 — IBGE e INEP usam códigos diferentes para cor/raça

| Categoria | IBGE | INEP (Censo Escolar) |
|---|---|---|
| Branca | 1 | 1 |
| Preta | 2 | 2 |
| Amarela | **3** | **4** |
| Parda | **4** | **3** |
| Indígena | 5 | 5 |
| Não declarada | 9 | 0 |

Juntar matrícula (INEP) com população (IBGE) pelo código numérico troca pardos por amarelos sem nenhum
erro aparente. Como pardos são o maior grupo da população brasileira e amarelos um dos menores, uma taxa
de atendimento calculada assim sai absurda para os dois grupos.

**No `azupdados`:** a seed `dim_cor_raca` guarda `codigo_ibge` e `codigo_educacenso` lado a lado, e toda
junção entre as duas fontes passa por `cor_raca_sk`. Os testes de unicidade nas duas colunas de código
impedem que uma edição da seed quebre o mapeamento.
