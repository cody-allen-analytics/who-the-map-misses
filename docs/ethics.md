# Ethics & Indigenous Data Sovereignty
# Ética y soberanía de datos indígenas

## Abstract
## Resumen

**EN:** This project evaluates whether a poverty map created using machine learning (the Meta Relative Wealth Index) underestimates poverty in Indigenous communities in Mexico, comparing it to the 2020 Population and Housing Census by INEGI, and how much this error would cost in the distribution of public resources.

**ES:** Este proyecto evalúa si un mapa de pobreza creado mediante aprendizaje automático (el Meta Relative Wealth Index) subestima la pobreza en comunidades indígenas de México, comparándolo con el Censo de Población y Vivienda 2020 del INEGI, y cuánto costaría este error en la distribución de recursos públicos.

**EN:** Only aggregated results are published: no tables identify localities, and the maps show regional patterns, not communities. The communities studied did not participate in the design of this research.

**ES:** Solo se publican resultados agregados: ninguna tabla identifica localidades, y los mapas muestran patrones regionales, no comunidades. Las comunidades estudiadas no participaron en el diseño de esta investigación.

## Community Feedback
## Retroalimentación de la comunidad

**EN:** If you belong to an affected community, or collaborate with one, and have observations or objections, you can:

**ES:** Si perteneces a una comunidad afectada, o colaboras con una, y tienes observaciones u objeciones, puedes:

- **EN:** Open an issue on GitHub, or
- **ES:** Abrir un *issue* en GitHub, o
- **EN:** Write to the author (contact information is in `[CITATION.cff]`).
- **ES:** Escribir al autor (la información de contacto está en `[CITATION.cff]`).

## Community Feedback

If you belong to an affected community, or collaborate with one, and have observations or objections, you can:

- Open an issue on GitHub, or
- Write to the author (contact information is in `[CITATION.cff]` <!-- replace with the actual file, e.g. CITATION.cff, CONTACT.md, README -->).
## Studying the algorithm, not the communities

This project audits a tool and the institutions that use it. It does not build a new instrument for
profiling Indigenous communities, and it does not publish rankings of specific localities as
candidates for or against programs. When the map errs, the finding is about the map and the decisions
built on it, not about the communities it describes.

## Whose data these are

Indigenous data sovereignty is the right of Indigenous peoples to govern data about their peoples,
lands and resources: how the data are collected, who uses them, for what, and to whose benefit. It
follows from the right to self-determination recognized in the UN Declaration on the Rights of
Indigenous Peoples, including the rights to take part in decisions that affect them (Article 18) and
to shape the economic and social programs that affect them (Article 23); in ILO Convention 169, which
Mexico ratified in 1990 and which gives Indigenous peoples a part in formulating, implementing and
evaluating development plans and programs that affect them (Article 7); and in Article 2 of Mexico's
Constitution.

Every input to this project is data about Indigenous peoples and their lands that they did not govern:

| Data | Produced by | Indigenous participation in this use |
|---|---|---|
| Census results by locality (ITER) | INEGI, under Mexico's statistical law, for official statistics | None: this is a secondary use of census data |
| Relative Wealth Index | Meta and university partners, from household surveys, satellite imagery and connectivity data | None |
| AlphaEarth satellite embeddings | Google and Google DeepMind, from Earth observation data | None |
| Rank errors, model predictions and results | This project | None so far |

The last row is the one this project controls. Its locality-level layer (rank errors for every map
tile, and the challenger models' deprivation predictions for every rural locality) would amount to a
new map of Indigenous communities made without them. The publication rules below keep that layer
unpublished.

## The CARE principles: what this project does, and where it falls short

The [CARE Principles for Indigenous Data Governance](https://www.gida-global.org/care) (Global
Indigenous Data Alliance, 2019) complement FAIR data practice with principles about people and
purpose. Listing only what a project does well would misrepresent it, so each row also says where
this one falls short.

| Principle | What this project does | Where it falls short |
|---|---|---|
| **Collective benefit:** data ecosystems designed so Indigenous peoples benefit | Asks whether a public tool under-serves Indigenous communities and what that would cost them in a budget formula (H6). The remedy it points to is better governance of maps, not more mapping of Indigenous communities. | Indigenous communities did not choose this question, and any benefit depends on agencies acting on the results. |
| **Authority to control:** Indigenous peoples' rights and interests in data recognized, and their authority to control them | Publishes only aggregates; locality-level data stay on the analyst's computer. Affected communities can ask for a result to be corrected, given context or withdrawn, and their requests take precedence over the pre-analysis plan. | No Indigenous community or organization governs this project or approved this use. The census categories are the state's, not the communities' own. |
| **Responsibility:** sharing how data are used, building relationships, respecting Indigenous languages and worldviews | Methods, code and the pre-registered plan are public, with a summary in Spanish. Findings are framed as map and institutional error. | There is no relationship with affected communities yet and nothing in Indigenous languages. The three poverty definitions measure deprivation from outside, not Indigenous conceptions of well-being. |
| **Ethics:** Indigenous rights and well-being first, at every stage of the data life cycle | No individual or household data, aggregates only, maps aggregated to regions, and out-of-scope uses stated in the [model card](model_card.md). | Group-level findings can still stigmatize, and because the inputs and code are public, anyone can rebuild the locality-level layer this project declines to publish. |

## Publication rules

These rules are part of the pre-registered plan ([§10](pre_analysis_plan.md#10-publication-and-data-governance))
and are enforced in code where possible.

1. **Aggregates only.** Published tables are broken down by group, decile, locality size or groups of
   municipalities. No table may carry a locality or map-tile identifier or coordinates:
   `mapaudit.publication` checks this in the end-to-end test on every push and in the release check.
2. **Regions, not communities, on maps.** Map tiles are averaged into hexagons about 40 km across,
   weighted by population, and a hexagon holding fewer than five tiles is not drawn.
3. **No named communities in results.** Spot checks against INEGI's tables are run locally, and their
   output is cleared before notebooks are published.
4. **No locality-level predictions.** The challenger models' predictions for individual localities are
   never published: they would be a new deprivation map of Indigenous communities made without their
   consent, which is what this project questions.
5. **Synthetic results are labeled as synthetic** wherever they appear.

## Who counts as Indigenous here

The analysis classifies places, not people. A locality counts as Indigenous when at least 40% of its
residents live in what INEGI calls Indigenous census households, a classification based on the
languages spoken in the household. The 40% cut-off follows the convention of Mexico's federal
Indigenous institute (INPI, formerly CDI). Thresholds of 30% and 50%, and a measure based on
individual speakers of Indigenous languages, are robustness checks.

None of these measures is self-identification, which Mexico's Constitution makes the fundamental
criterion for who is Indigenous (Article 2). Language-based measures miss people who identify as
Indigenous but do not speak an Indigenous language, and all of them treat dozens of distinct peoples,
speaking languages from 68 recognized language groups, as a single category. Results therefore
describe *places classified by census measures*, never people's identities.

## Language

- "Indigenous" is capitalized; specific peoples are named where the data allow.
- Deprivation is described as a lack of services the state should provide, not as a trait of a community.
- Results are reported in whichever direction they go, including if the map turns out to overstate
  Indigenous deprivation.

## Corrections, objections and withdrawal

If you belong to, or work with, a community affected by this analysis and see a problem with how it is
represented, or object to its being studied at all, please open an issue or write to the author (contact
details in [`CITATION.cff`](https://github.com/cody-allen-analytics/who-the-map-misses/blob/main/CITATION.cff)).
Every request is answered and logged below. Requests from affected communities take precedence over the
pre-analysis plan: a result can be corrected, given context or withdrawn, and the change is also
recorded in the plan's [deviations log](pre_analysis_plan.md#deviations-log).

| Date | Request | Response |
|---|---|---|
| | | |

## What would make this work better

- **Co-design.** Deciding with Indigenous organizations which definition of poverty to audit against,
  which errors matter most, and how results are shared.
- **Returning results.** Plain-language summaries in Spanish and, with partners, in Indigenous
  languages, shared with organizations in the regions most affected.
- **Community-governed data.** Statistics produced and governed by Indigenous communities as the ground
  truth, instead of census categories or corporate maps.
- **Open to collaborate.** A [Local Contexts](https://localcontexts.org/) Open to Collaborate Notice,
  telling communities that the project is open to working with them on how their data are used.

## Author's positionality

*Write a short paragraph about your relationship to this topic and to Indigenous communities, and
what you did to check your assumptions. Delete this note.*

## References

- Carroll, S. R., Garba, I., Figueroa-Rodríguez, O. L., et al. (2020). The CARE Principles for
  Indigenous Data Governance. *Data Science Journal*, 19(1), 43. <https://doi.org/10.5334/dsj-2020-043>
- Kukutai, T., & Taylor, J. (Eds.) (2016). *Indigenous Data Sovereignty: Toward an Agenda*. ANU Press.
- International Labour Organization (1989). *Indigenous and Tribal Peoples Convention* (No. 169), Article 7.
- United Nations (2007). *Declaration on the Rights of Indigenous Peoples*, Articles 18 and 23.
- *Constitución Política de los Estados Unidos Mexicanos*, Article 2, as reformed in 2024.
