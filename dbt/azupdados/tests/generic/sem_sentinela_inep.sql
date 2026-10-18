{# Armadilha 01: falha se algum código-sentinela do INEP sobreviveu à silver. #}
{% test sem_sentinela_inep(model, column_name) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} in (77777, 88888, 99999)
{% endtest %}
