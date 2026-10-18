# Bronze

As tabelas bronze não são modelos dbt: são criadas pela ingestão em Python (`ingest/`),
uma por arquivo oficial (`bronze.censo_escolar_escola_<ano>`), com todas as colunas em TEXT.

A silver as descobre dinamicamente com `dbt_utils.get_relations_by_pattern`, então carregar
um novo ano não exige mudar nenhum SQL. A linhagem de cada carga (arquivo, md5, linhas)
fica em `meta.carga_arquivo`.
