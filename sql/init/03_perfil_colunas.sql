-- Perfil de cada coluna de cada arquivo carregado e a comparação com o ano anterior (deriva de esquema).
--
-- Dois tipos de teste, de natureza diferente:
--   regra de negócio  (dbt, tests/qualidade): o dado faz sentido? ex.: aprovação + reprovação + abandono = 100.
--   deriva de esquema (aqui e dbt, tests/estrutura): a coluna se comporta como no ano anterior?
-- A regra de negócio não pega tudo: se o INEP deslocar os nomes dos três blocos (aprovação, reprovação e
-- abandono) da mesma forma, a soma continua 100 e a série fica errada. O perfil pega, porque a coluna passa
-- a ter a proporção de "--" de outra etapa. Foi uma contagem assim, feita à mão, que revelou a armadilha 12.
--
-- Gravado na carga (ingest/bronze_indicadores.py), que imprime a deriva antes de alguém olhar a série.

CREATE TABLE IF NOT EXISTS meta.ind_perfil_coluna (
    sigla         TEXT NOT NULL,
    ano           INT  NOT NULL,
    posicao       INT  NOT NULL,
    nome_tecnico  TEXT NOT NULL,
    rotulo        TEXT,
    n_linhas      INT  NOT NULL,
    n_ausente     INT  NOT NULL,   -- "--": etapa não oferecida ou sigilo
    n_vazio       INT  NOT NULL,   -- célula vazia
    n_numerico    INT  NOT NULL,   -- valor que lê como número (vírgula ou ponto decimal)
    PRIMARY KEY (sigla, ano, posicao)
);

-- Para cada coluna, o mesmo indicador no ano anterior disponível, pareado de duas formas:
--   pelo nome técnico  → pega nome que passou a descrever outro dado (rendimento 2018: tap_f04 vira anos finais);
--   pelo rótulo        → pega rótulo que passou a descrever outro dado (o caso que a silver não veria,
--                        porque ela confia no rótulo).
-- Dois motivos de alerta:
--   perfil   a proporção de "--" ou de números mudou 10 pontos ou mais. Compara proporções, não contagens:
--            a cobertura muda de verdade entre anos (TDI: 179 mil escolas em 2015, 140 mil em 2016).
--            No rendimento 2018, tap_f04 vai de 27% para 54% de "--".
--   rotulo   pareado pelo nome, a etapa do rótulo (último trecho, ex. "5º ano") não é a do ano anterior.
--            Existe porque o perfil sozinho falhou no ATU 2018: lá 5º ano e anos finais têm proporções de "--"
--            parecidas (60% e 68%), a troca mexe só 6 a 8 pontos e passava abaixo do limiar.
--            Este critério não depende do dado: o nome mudou de etapa, alguém tem de explicar por quê.
--            Só vale quando os dois anos têm rótulo (colunas de identificação às vezes herdam o título da planilha).
DROP VIEW IF EXISTS meta.ind_deriva_perfil;
CREATE VIEW meta.ind_deriva_perfil AS
WITH p AS (
    SELECT *,
           n_ausente::numeric  / nullif(n_linhas, 0) AS pct_ausente,
           n_numerico::numeric / nullif(n_linhas, 0) AS pct_numerico,
           -- etapa = último trecho do rótulo, normalizado ("5° ano" e "5º Ano" são a mesma)
           lower(trim(translate(regexp_replace(rotulo, '^.*/', ''), '°', 'º'))) AS etapa_rotulo,
           -- rótulo repetido no mesmo arquivo: desempata pela ordem de aparição
           row_number() OVER (PARTITION BY sigla, ano, rotulo ORDER BY posicao) AS ordem_rotulo,
           (SELECT max(a.ano) FROM meta.ind_perfil_coluna a
             WHERE a.sigla = c.sigla AND a.ano < c.ano) AS ano_anterior
    FROM meta.ind_perfil_coluna c
),
pares AS (
    SELECT 'nome' AS pareado_por, atual.*, ant.posicao AS posicao_anterior, ant.rotulo AS rotulo_anterior,
           ant.etapa_rotulo AS etapa_anterior,
           ant.pct_ausente AS pct_ausente_anterior, ant.pct_numerico AS pct_numerico_anterior
    FROM p atual
    JOIN p ant ON ant.sigla = atual.sigla AND ant.ano = atual.ano_anterior
              AND ant.nome_tecnico = atual.nome_tecnico
    UNION ALL
    SELECT 'rotulo', atual.*, ant.posicao, ant.rotulo, ant.etapa_rotulo, ant.pct_ausente, ant.pct_numerico
    FROM p atual
    JOIN p ant ON ant.sigla = atual.sigla AND ant.ano = atual.ano_anterior
              AND ant.rotulo = atual.rotulo AND ant.ordem_rotulo = atual.ordem_rotulo
),
avaliado AS (
    SELECT *,
           abs(pct_ausente - pct_ausente_anterior) >= 0.10
             OR abs(pct_numerico - pct_numerico_anterior) >= 0.10                         AS mudou_perfil,
           pareado_por = 'nome' AND etapa_rotulo <> etapa_anterior                          AS mudou_rotulo
    FROM pares
)
SELECT sigla, ano, ano_anterior, pareado_por,
       concat_ws(' + ', CASE WHEN mudou_perfil THEN 'perfil' END, CASE WHEN mudou_rotulo THEN 'rotulo' END) AS motivo,
       posicao, posicao_anterior, nome_tecnico, rotulo_anterior, rotulo,
       round(pct_ausente_anterior, 3)  AS pct_ausente_anterior,
       round(pct_ausente, 3)           AS pct_ausente,
       round(pct_numerico_anterior, 3) AS pct_numerico_anterior,
       round(pct_numerico, 3)          AS pct_numerico
FROM avaliado
WHERE mudou_perfil OR mudou_rotulo;
