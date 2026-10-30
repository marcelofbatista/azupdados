# Armadilha 14 — Um teste de reconciliação que passa sem comparar nada

> **EN summary.** The first version of the SAEB reconciliation test filtered the official spreadsheet on
> `dependencia_adm = 'Total'`, a label that does not exist there. The comparison set was empty and the test
> passed. Reconciliation tests now fail when there is nothing to compare, and are checked against a
> deliberately wrong value.

Testes dbt "de linhas" passam quando a consulta devolve zero linhas. Isso é ótimo quando as linhas são os erros —
e perigoso quando um filtro errado esvazia o conjunto que deveria ser comparado.

## O que aconteceu

O teste `assert_saeb_media_bate_com_inep` comparava a média calculada com a das planilhas oficiais filtrando
`dependencia_adm = 'Total'`. Nas planilhas, esse rótulo não existe: a linha de todas as redes se chama
`Total - Federal, Estadual, Municipal e Privada`. O filtro devolvia zero linhas, o teste não achava nenhuma
divergência e passava. Só foi descoberto porque a carga do gabarito imprime os valores distintos encontrados.

## A regra que ficou

1. Todo teste de reconciliação tem uma **guarda**: se o gabarito filtrado estiver vazio para uma edição carregada,
   o teste falha.
2. Antes de confiar num PASS, o teste é **provocado**: um valor oficial é adulterado de propósito e o teste
   precisa falhar. (Feito para o SAEB: 999 numa média → FAIL; rótulo "Total" de volta → FAIL pela guarda.)
3. Além do PASS, um diagnóstico mostra **quantas** comparações foram feitas e a maior diferença
   (`sql/diagnosticos/saeb_reconciliacao_resumo.sql`).
