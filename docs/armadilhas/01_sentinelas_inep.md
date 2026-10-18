# 01 — Códigos-sentinela em colunas de quantidade

**Problema.** Em colunas numéricas `QT_*` dos microdados, o INEP usa valores como 88888, 99999 e 77777
para sinalizar situações especiais em vez de contagens. Somar a coluna sem tratar esses valores infla
qualquer total.

**Correção.** Na silver, a macro `quantidade_inep()` converte esses códigos em nulo.

**Teste.** `sem_sentinela_inep` falha se algum desses valores chegar à silver ou à gold.
