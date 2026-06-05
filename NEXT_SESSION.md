# NEXT_SESSION — Handoff från session 2026-06-05

**Projekt:** evbcgpricing (BCG priselasticitet, replikering + växande data)
**Branch:** `fas-f-fresh-data`
**HEAD:** `2ea61bc` (Cleanup: structure C:\Projekt\BCG repo root for clarity)
**Utvecklare:** Jens Palmö

---

## 🔴 KRITISK UPPTÄCKT VID SESSIONSSLUT — HÖGSTA PRIORITET

**60% av ItemCodes saknas i vår växande output mot BCG:s facit.**

| Lager | KEY | ItemCodes | AAP130 status |
|---|---|---|---|
| BCG fryst facit | 3812 | 1276 | ✅ finns (9 cluster-rader) |
| Vår input CSV (växande) | — | 1151 (rader: 610,039) | ✅ finns (1407 rader, 7 cluster, 455.6 MSEK) |
| **Vår växande output** | **1521** | **~297** | **❌ SAKNAS HELT** |

**Bekräftat:** AAP130 (och liknande klinik-koder som DUS, AAP-serie) finns i:
- BCG:s 0828-facit-input (1151 ItemCodes totalt)
- Vår DW-extraktion (samma 1151 ItemCodes, full data, alla 7 cluster, 201 veckor)
- BCG:s output (full 9 cluster-rader per kod)

Och saknas helt i:
- Vår växande output (1521 KEY, ~75% av ItemCodes droppas)

**Slutsats:** Pipeline-bortfall, inte extraktions-bortfall. Bortfallet sker i `data_prepration.py` eller `feature_selection.py`.

### Verifiering som finns i workspace\
- `workspace\diagnose_missing_keys.py` — diagnos-skript
- `workspace\check_aap_dus.py` — AAP/DUS-koll i BCG-facit
- `workspace\check_input_layer.py` — input-lager-verifiering (AAP130 finns i input)

### Hypoteser att verifiera

**H1 (mest sannolik):** Pipeline filtrerar internt på `END_DATE = 2025-06-29` även när input innehåller data till 2026-04-27. constants.py rad 22 är env-overridable — kördes pipelinen med rätt `BCG_END_DATE`?

**H2:** `SPECIAL_WEEKS` eller annan filterlogik i `data_prepration.py` droppar ItemCodes pga interna kvalitetsgater på växande data.

**H3:** `feature_selection.py` med Ray-parallellisering droppar tyst på minnesbrist eller annan run-time-anledning.

### Diagnos-steg nästa session

1. Verifiera `BCG_END_DATE`-environment-variabel sattes vid F.6-körning
2. Räkna ItemCodes vid varje pipeline-steg (input → after data_prepration → after feature_selection → output)
3. Trace AAP130 specifikt genom varje fil
4. Pipeline-walk: kör steg för steg lokalt på smoke-set inklusive AAP130

---

## DAGENS FAKTISKA LEVERANS (skall hyllas innan kritiken)

### Output - var ligger filerna

**Cluster-modellen körd på växande fönster (2022-07 → 2026-04-27, 1521 KEY):**
```
C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\_archive_growing_2026-04-27\
```

| Fil | Innehåll |
|---|---|
| `output_summary.xlsx` | 1521 KEY × elasticitet, p-värde, RSQ |
| `blended_output_growing.csv` | Post-fallback (cp1252-encoded) |
| `compare_growing_vs_bcg_2026-06-05.xlsx` | 3-flikars jämförelse mot BCG fryst facit |
| `model_summary.xlsx` | Per-KEY modell-koefficienter |
| `model_results.csv` | Vecko-nivå predictions (129 MB) |
| `data_for_model.csv` | Pipeline input (73 MB) |
| `_run_logs\` | Alla körningsloggar |

**BCG fryst facit (skrivskyddad sanning):**
```
C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG\BCG_orginal_V2_New\02. Elasticity\2. Product Cluster Level Models\output\model\output_summary.xlsx
```
3812 KEY, fönster 2022-07-01 → 2025-06-28.

### Commits från idag

| Steg | Status | Commit |
|---|---|---|
| F.6: Cluster pipeline steg 1-4 på växande fönster | KLART | 5b0ac65 |
| F.7: Cluster-fallback (steg 5) på växande | DELVIS — post = pre pga LF.1 | (inom F.6) |
| LESSONS_BCG.md återställd (LB.29-37) | KLART | 0991aaa |
| LOCKED_ASSUMPTIONS.md skapad med LF.1-7 | KLART | 618dd85 |
| Repo-rot städad (24 filer flyttade) | KLART | 2ea61bc |

### Validerad omsättning (för externa rapporter)

Vår input CSV (växande fönster 2022-07 → 2026-04-27):
- Sum TotalNet: **8,269,105,588 SEK** (brutto inkl VAT)
- Sum TotalNetXVat: **6,615,284,470 SEK** (netto ex VAT)
- Sum SoldQuantity: **7,970,132** enheter

---

## URSPRUNGLIGT NÄSTA STEG (A+B) — Skjuts tills bortfallsfrågan är löst

Du valde A+B kombinerat: affärspresentation från Cluster-output + rullande 12-månaders volym.

**Detta är värdelöst innan bortfallsfrågan är löst.** Att bygga en affärs-Excel som visar elasticitet för 297 ItemCodes (av 1151) skulle leda till felaktiga slutsatser — vi vet inte vilka koder som faktiskt har förändrats vs vilka pipelinen tappat bort.

**Ordning för nästa session:**

1. **PRIO 1:** Diagnos av 60%-bortfall (1-3h beroende på rotorsak)
2. **PRIO 2:** Om rotorsak är enkel (env-var saknad) — kör om pipelinen
3. **PRIO 3:** A+B-bygget mot reparerad output

**Öppen fråga:** TotalNet (omsättning brutto), SoldQuantity (enheter), eller båda i Excel? Inte besvarad. Beslut vid start av A+B.

---

## VÄNTAR PÅ EXTERN INPUT

- **Mail till IT skickat** angående nästa steg (hosting, Storage Blob role från Kent). **Väntar på svar.**
- KRAVSPEC_IT.md finns i repo-rot som referens.

---

## VAD SKJUTS UPP

- **F.8 (Site + Bundle på växande)** — ej rätt prioritet
- **F.9 (Steg 6 multi-modell-väv)** — beror av F.8
- **KÄRNPRINCIPER-patch** (6.5 + 6.6) — pending manuell formulering av Jens
- **TILL_RADERING\ permanent radering** — 1.36 GB granskning innan slutgiltig

---

## VIKTIGA STÅENDE PRINCIPER

- **LF.1** (cluster-hierarki 2-nivå platt) gäller
- **LF.2** (anchor 2022-07-01) gäller
- **LF.3** (BCG-facit + verifierade outputs skrivskyddade) gäller
- **LF.4-7** se LOCKED_ASSUMPTIONS.md
- **Vid lärdom under sessionen** — flytta in i rätt master-fil FÖRE sessionsslut (STÅENDE INSTRUKTION)

### LB-kandidat för nästa session

**LB.XX — Validering ska inkludera täckningsgrad, inte bara matchning på producerade rader.**

Symptom: Replikerade pipelinen validerades mot BCG-facit och fick korrelation 1.0 på producerade KEY. Detta sa **inget om hur stor andel av facit som faktiskt producerades**. När vi körde på växande data upptäcktes 60% bortfall flera sessioner efter validering bekräftades grön.

Regel: Varje validering ska inkludera räknor på täckningsgrad (vår_output ∩ facit / facit) som separat KPI vid sidan av korrelationsmått på matchade rader.

---

## SNABBSTART NÄSTA SESSION

1. `cd C:\Projekt\BCG && git status` — verifiera ren
2. Öppna denna NEXT_SESSION.md för full kontext på 60%-bortfallet
3. Börja med **diagnos-skripten i workspace\** för att återkalla läge
4. Sedan: pipeline-walk för att identifiera var AAP130 droppas

---

*Skapad 2026-06-05 vid sessionsslut. Branch fas-f-fresh-data @ 2ea61bc. ~7h session. Stora upptäckter: LF.1-7 formaliserade, repo strukturerad, 60%-bortfall identifierat vid sessionsslut.*
