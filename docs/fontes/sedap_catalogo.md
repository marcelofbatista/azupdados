# Catálogo de bases do SEDAP+ (INEP)

Bases disponíveis para consulta pela API do SEDAP+ (aba Integração), conforme a lista da plataforma em
19/10/2026. Nas consultas SQL, cada base é referenciada como `raw.<NOME>` (ex.: `raw.BAS_MATRICULA_2024`).

Todas passam por privacidade diferencial: use só agregados em grão grosso e veja a
[armadilha 09](../armadilhas/09_sedap_privacidade_diferencial.md). Cada consulta consome orçamento de
privacidade do projeto — consulte só o que for usar.

| Família | Base | Anos | Uso no `azupdados` |
|---|---|---|---|
| Educação básica (Censo Escolar) | `BAS_MATRICULA_<ano>` | 2007–2024 | ✅ tipo de deficiência por UF × dependência (2015–2024) |
| | `BAS_ESCOLA_<ano>` | 2007–2024 | — (o microdado aberto já cobre) |
| | `BAS_TURMA_<ano>` | 2007–2023 | — |
| | `BAS_DOCENTE_<ano>` | 2007–2023 | ⏳ candidato: perfil docente agregado |
| ENEM | `ENEM_<ano>_SEDAP` | 2009–2024 | — |
| SAEB | `SAEB_ALUNO_5EF_<ano>_SEDAP`, `SAEB_ALUNO_9EF_<ano>_SEDAP`, `SAEB_ALUNO_3EM_<ano>_SEDAP` | 2011–2023 (bienal) | ⏳ comparação com o microdado aberto |
| Educação superior | `SUP_ALUNO_<ano>`, `SUP_CURSO_<ano>`, `SUP_IES_<ano>` | 2009–2024 | — |
| | `SUP_DOCENTE_<ano>`, `SUP_DOCENTE_CURSO_<ano>` | 2009–2023 | — |
| Economia | `PIB_MUNICIPIOS_2010_2023` | 2010–2023 | ⏳ candidato: contexto socioeconômico municipal |

O dicionário de colunas de cada base está no ícone ⓘ ao lado do nome, na própria plataforma.
