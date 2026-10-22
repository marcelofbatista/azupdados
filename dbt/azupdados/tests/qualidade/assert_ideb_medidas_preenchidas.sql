{#
  Cada medida do IDEB precisa ter valor em pelo menos uma linha de cada fato. Uma medida toda nula
  quer dizer que o nome da coluna no arquivo do INEP mudou e o pivô da gold deixou de reconhecê-lo.
#}
{%- set medidas = ['taxa_aprovacao', 'indicador_rendimento', 'nota_matematica', 'nota_portugues',
                   'nota_media_padronizada', 'ideb', 'meta_ideb'] -%}
{%- set consultas = [] -%}
{%- for fato in ['fato_ideb_escola_ano', 'fato_ideb_municipio_ano', 'fato_ideb_agregado_ano'] -%}
{%- for m in medidas -%}
{%- do consultas.append("select '" ~ fato ~ "' as fato, '" ~ m ~ "' as medida where not exists (select 1 from "
                        ~ ref(fato) ~ " where " ~ m ~ " is not null)") -%}
{%- endfor -%}
{%- endfor %}
{{ consultas | join('\nunion all\n') }}
