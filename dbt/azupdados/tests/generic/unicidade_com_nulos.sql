{#
  Armadilha 05: testar unicidade só sobre valores preenchidos esconde duplicatas.
  Este teste trata nulo como valor (coalesce para um marcador) antes de agrupar.
#}
{% test unicidade_com_nulos(model, colunas) %}
select
    {% for c in colunas %}coalesce({{ c }}::text, '<<nulo>>') as {{ c }}{% if not loop.last %}, {% endif %}{% endfor %},
    count(*) as ocorrencias
from {{ model }}
group by {% for c in colunas %}{{ loop.index }}{% if not loop.last %}, {% endif %}{% endfor %}
having count(*) > 1
{% endtest %}
