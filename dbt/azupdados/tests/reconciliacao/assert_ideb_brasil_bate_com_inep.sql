{{ config(tags=['reconciliacao']) }}
{# O IDEB do Brasil calculado da planilha deve ser o número divulgado pelo INEP (uma casa decimal). #}
select o.etapa_sk, o.ano_ideb, o.ideb_oficial, f.ideb
from {{ ref('ref_ideb_oficial') }} o
left join {{ ref('fato_ideb_agregado_ano') }} f
  on f.nivel = o.nivel and f.rede = o.rede and f.etapa_sk = o.etapa_sk and f.ano_ideb = o.ano_ideb
where f.ideb is null or round(f.ideb, 1) <> o.ideb_oficial
