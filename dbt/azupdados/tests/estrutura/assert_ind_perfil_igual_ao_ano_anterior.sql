{# Deriva de esquema (armadilha 12): coluna cujo perfil mudou em relação ao ano anterior do mesmo indicador.
   Não é regra de negócio — é a coluna deixar de se comportar como antes. Pega o caso que a soma de 100 não
   pega: nomes deslocados da mesma forma em aprovação, reprovação e abandono mantêm a soma e erram a série.
   A carga (ingest/bronze_indicadores.py) já imprime estas linhas; aqui ficam registradas a cada build.
   Severidade warn: há derivas reais e explicadas (rendimento 2018), listadas na armadilha 12. #}
{{ config(severity='warn') }}
select * from {{ source('meta', 'ind_deriva_perfil') }}
