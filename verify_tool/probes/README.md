# verify_tool/probes -- diagnostiska sonder

Återanvändbara verktyg för att hitta rotorsak när en pipeline ger fel/tomt
resultat utan att krascha, och för att validera att en modell tål växande data
*innan* den körs. Kodifierar sond-metodiken (KÄRNPRINCIPER P.5, LESSONS_BCG LB.76).

Till skillnad från `output_rationality/` (validerar modell-OUTPUT efter körning)
sonderar dessa pipeline-KEDJAN — var data tappas och var ursprungsmiljöns
antaganden (UK/Alteryx) biter på Evidensia-data.

## Verktyg

| Fil | När | Vad |
|---|---|---|
| `chain_population_probe.py` | output tomt/fel men ingen krasch | Mall: följ data genom kedjan, mät population efter varje steg. "N→0 på rad X" = boven. Testa flera hypoteser i samma körning. Löste bundle-tömningsbuggen (LB.75). |
| `model_chain_validator.py` | innan modellkörning på ny period/familj | Statisk skanning av alla skript i en code-mapp för fem växande-risker: env-fönster, datum-filter, hårdkodade år, inner-merge/isin/dropna, cp1252. |
| `support_files_check.py` | innan modellkörning | Verifierar att config-refererade stödfiler finns. Skiljer blockerare från dött config-arv (t.ex. InScope Mapping, FD.36). |

## Arbetsflöde (ny familj eller ny period)

1. `support_files_check.py` — finns alla stödfiler? (saknad ≠ blockerare om koden ej läser den)
2. `model_chain_validator.py` — tål kedjan växande? (allt left/outer + env-fönster = grönt)
3. Om körning ger tomt/fel: `chain_population_probe.py` — pinpointa tappet

## Princip (varför sond, inte lager-för-lager)

Reaktiv felsökning (kör→krascha→fixa→upprepa) ser ett lager i taget; mest tid går
åt att upptäcka att det finns ett till. En sond följer datan genom HELA kedjan i ett
svep och testar flera hypoteser parallellt → minuter till rotorsak i stället för
en dag. Bundle-buggen 2026-06-17 är beviset (LB.76).

*Förvaltas av Jens Palmö (Senior Business Analyst).*
