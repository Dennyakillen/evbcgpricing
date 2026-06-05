# NEXT_SESSION — Handoff från session 2026-06-05

**Projekt:** evbcgpricing (BCG priselasticitet, replikering + växande data)
**Branch:** `fas-f-fresh-data`
**HEAD:** `2ea61bc` (Cleanup: structure C:\Projekt\BCG repo root for clarity)
**Utvecklare:** Jens Palmö

---

## DAGENS OUTPUT — VAR LIGGER FILERNA

**Cluster-modellen körd på växande fönster (2022-07-01 → 2026-04-27, 1521 KEY):**
```
C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\_archive_growing_2026-04-27\
```

| Fil | Innehåll |
|---|---|
| `output_summary.xlsx` | 1521 KEY × elasticitet, p-värde, RSQ — **HUVUDFILEN** |
| `blended_output_growing.csv` | Post-fallback (cp1252-encoded) |
| `compare_growing_vs_bcg_2026-06-05.xlsx` | **3-flikars jämförelse mot BCG fryst facit** |
| `model_summary.xlsx` | Per-KEY modell-koefficienter |
| `model_results.csv` | Vecko-nivå predictions (129 MB) |
| `data_for_model.csv` | Pipeline input (73 MB) |
| `_run_logs\` | Alla körningsloggar |

**BCG fryst facit (skrivskyddad sanning):**
```
C:\Users\jepa02\OneDrive - Evidensia Djursjukvård AB\Datastrategi\BCG\BCG_orginal_V2_New\02. Elasticity\2. Product Cluster Level Models\output\model\output_summary.xlsx
```
3812 KEY, fönster 2022-07-01 → 2025-06-28.

**Jämförelsen i `compare_growing_vs_bcg_2026-06-05.xlsx` visar:**
- 1310 KEY i båda (inner join)
- 322 tecken-flippar (24.6%)
- Median absolut diff: 0.39
- Pre-fallback Significant?: Växande 23.8% vs BCG 40.4%

---

## DETTA HAR DAGEN GJORT

| Steg | Status | Commit |
|---|---|---|
| F.6: Cluster pipeline steg 1-4 på växande fönster | KLART | 5b0ac65 |
| F.7: Cluster-fallback (steg 5) på växande | DELVIS — post = pre pga LF.1 (saknad CH-hierarki, medvetet val) | (inom F.6) |
| LESSONS_BCG.md återställd (LB.29-37) | KLART | 0991aaa |
| LOCKED_ASSUMPTIONS.md skapad med LF.1-7 | KLART | 618dd85 |
| Repo-rot städad (24 filer flyttade) | KLART | 2ea61bc |

**Värt att veta:** BCG når 48.4% post-fallback med sin 4-nivå-hierarki (Clinics_CH/Hospital_CH). Vi når 23.8% med vår 2-nivå platta. Detta är **LF.1** — låst designval för affärs-referensram. Skall **inte** revideras impulsivt.

---

## NÄSTA STEG (i ordning, A+B-bygget)

Du valde **A+B** kombinerat: affärspresentation från Cluster-output + rullande 12-månaders volym.

### Steg 1: Bygg jämförelse-Excel för chefer

En Excel som visar BCG fryst facit vs Vår växande körning per KEY, med:
- KEY, ItemCode, ItemDescription, Service (L4), Cluster
- BCG elasticitet + p-värde (fryst)
- Vår elasticitet + p-värde (växande)
- Skillnad (absolut + procent)
- Volym 12-månader rullande
- "Affärsmässig vikt" = volym × |skillnad| för sortering

Period: **senast stängda månad** = 2025-05 → 2026-04.

### Steg 2: Bygg rullande 12-månaders volym-extraktion

Detta är ett `Business_Analytics`-jobb, inte `evbcgpricing`-jobb. Använder befintlig `export_b4b_for_model.py` som mall, aggregerar veckor till rullande 12-mån per ItemCode × Cluster.

**Öppen fråga:** TotalNet (omsättning brutto), SoldQuantity (enheter), eller båda? Inte besvarad. Beslut vid start.

---

## VÄNTAR PÅ EXTERN INPUT

- **Mail till IT skickat** angående nästa steg (hosting, Storage Blob role från Kent, etc). **Väntar på svar.**
- KRAVSPEC_IT.md finns i repo-rot som referens.

---

## VAD SKJUTS UPP

- **F.8 (Site + Bundle på växande)** — ej rätt prioritet givet affärsmålen. Kanske framtida sessioner när chefer börjar fråga om Department- eller Bundle-granularitet.
- **F.9 (Steg 6 multi-modell-väv)** — beror av F.8.
- **KÄRNPRINCIPER-patch** (6.5 + 6.6) — pending manuell formulering av Jens.
- **TILL_RADERING\ permanent radering** — 1.36 GB granskning innan slutgiltig Remove-Item.

---

## VIKTIGA STÅENDE PRINCIPER

- **LF.1** (cluster-hierarki 2-nivå platt) gäller. CH-mellannivån återskapas INTE.
- **LF.2** (anchor 2022-07-01) gäller. Inga rolling windows utan affärsbeslut.
- **LF.3** (BCG-facit + verifierade outputs skrivskyddade) gäller.
- **LF.4-7** se LOCKED_ASSUMPTIONS.md.
- Vid lärdom under sessionen — flytta in i rätt master-fil FÖRE sessionsslut (STÅENDE INSTRUKTION i Claude:s minne).

---

## SNABBSTART NÄSTA SESSION

1. `cd C:\Projekt\BCG && git status` — verifiera ren
2. Bestäm A eller B först (eller parallellt)
3. För A: öppna `_archive_growing_2026-04-27\output_summary.xlsx` + `compare_growing_vs_bcg_2026-06-05.xlsx`, ladda upp till Claude som start
4. För B: börja i `C:\Projekt\Business_Analytics\`, hitta `export_b4b_for_model.py`

---

*Skapad 2026-06-05 vid sessionsslut. Branch fas-f-fresh-data @ 2ea61bc. Förra sessionen: F.6 + F.7 + dokumentstädning + LF.1-7 + repo-cleanup. Cirka 6.5h total session-tid.*
