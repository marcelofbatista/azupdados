# Armadilha 11 — As planilhas do IDEB não são tabelas

As divulgações do IDEB são planilhas formatadas para leitura humana, não arquivos de dados:

- **Nove linhas de título e rótulos** antes do cabeçalho técnico (`SG_UF`, `VL_OBSERVADO_2023`...).
  Os rótulos legíveis trazem até notas de rodapé coladas no ano ("Taxa de Aprovação - 20212").
- **Colunas de identificação sem nome** no arquivo de UFs e regiões; no de Brasil, elas se chamam
  `BRASIL` e `rede`. O carregador dá nomes padronizados a elas.
- **Território pelo nome, não pelo código**, nos agregados: "Distrito Federal", "Centro-Oeste". A gold
  resolve o código comparando nomes sem acento com `dim_uf` e `dim_regiao`, e um teste exige que toda
  linha tenha nível (Brasil, região ou UF).
- **Nome de coluna repetido.** No arquivo de 2025, o indicador de rendimento de 2025 sai rotulado
  `VL_INDICADOR_REND_2023`, repetindo o nome da edição anterior. O carregador não descarta nada: a segunda
  ocorrência vira `vl_indicador_rend_2023__2`, e a silver a lê como a edição seguinte (2025). Se a regra
  deixar de valer em algum arquivo, a unicidade da silver quebra e o build para.
- **Coluna sem nome técnico no meio da série.** No arquivo do Brasil (anos finais), o IDEB observado de
  2023 vem sem cabeçalho, entre `VL_OBSERVADO_2021` e `VL_OBSERVADO_2025`. O carregador só dá nome a uma
  coluna assim quando os dois vizinhos confirmam (mesma métrica, anos separados por 4) e registra o caso
  no log; senão, ela fica como `col_<n>` e fora da silver. Foi o teste de reconciliação com o IDEB oficial
  que encontrou esse buraco.
- **Notas de rodapé coladas nos rótulos.** Rede vem como "Total (3)(4)" ou "Pública (4)"; a silver remove
  os marcadores.
- **UF com nome abreviado.** "M. G. do Sul", "R. G. do Norte" e "R. G. do Sul" — resolvidas pela seed
  `ref_territorio_alias`, com a fonte de cada apelido.
- **`-` como ausente**, em vez de vazio.

Vantagem escondida: as planilhas de 2025 trazem a série inteira desde 2005 (ensino médio desde 2017),
então os arquivos de edições anteriores não são necessários. As metas (`VL_PROJECAO`) só vão até 2021.
