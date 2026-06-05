# NEXT_SESSION — Handoff från session 2026-06-05

**Projekt:** evbcgpricing (BCG priselasticitet, replikering + växande data)
**Branch:** `fas-f-fresh-data`
**HEAD:** `ed1f88e` (NEXT_SESSION: critical 60% ItemCode dropout finding + diag scripts archived)
**Utvecklare:** Jens Palmö

---

## 🎯 ROTORSAK BEVISAD VID SESSIONSSLUT — kritisk för nästa session

**72.5% av våra ItemCodes saknar ProductGroupL4Name i DW. Detta orsakar 60%-bortfallet.**

### Den definitiva diagnosen (fyrfaldigt validerad)

`data_prepration.py` rad 345 (`yoy_seasonality()`) gör en **inner merge** på `service`-kolumnen
(= ProductGroupL4Name). När `service` är NULL droppas alla rader för den ItemCode.

| Lager | Antal | AAP130 |
|---|---|---|
| Input CSV | 1151 ItemCodes / 4930 KEY | ✅ 7 cluster, 201 veckor, 455 MSEK |
| Efter 103-veckors-filter | 3028 KEY | ✅ 7 cluster passerar |
| Efter yoy_seasonality inner merge | ~317 ItemCodes / 1521 KEY | ❌ DROPPAS (100% NULL pg4) |
| BCG facit | 1276 ItemCodes / 3812 KEY | ✅ Finns (9 rader) |

### Vad har 100% NULL pg4 i vår input?

**834 av 1151 ItemCodes (72.5%) har 100% NULL ProductGroupL4Name.**

M�nstret: **klinik-tjänster** (AAP=undersökning, DUS=ultraljud, AEM=anestesi, ALB/ALT/ANALYS=labb)
saknar mappning. **Varor** (Fingertuta SBAS0004, Övrig försäljning OVR0001) har mappning.

### Affärsmässig konsekvens

Vi har byggt en elasticitetsmodell som **systematiskt utesluter veterinärtjänster** —
sannolikt huvudintäktskällan. Modellen visar bara elasticitet på sortimentvaror,
inte på det som faktiskt prissätts mest aktivt (konsultationer, undersökningar, behandlingar).

### Rotorsak i DW-extraktionen

`export_b4b_for_model.py` rad 75:
```python
i.Master_Underkategori3 AS ProductGroupL4Name,
```

`Master_Underkategori3` är NULL för veterinärtjänster i `Manual.Dim_Item_Extended`.
Detta dokumenterades redan i IB.8 (FAS 10, 2026-06-01): *"L4 (Master_Underkategori3) är halv-NULL,
vilket inte biter på kärnelasticiteten men är relevant för gruppering"*.

**Vi förstod inte konsekvensen då.** yoy_seasonality:s inner merge gör att NULL pg4 = ItemCode
försvinner helt, inte bara att "gruppering blir trasig".

### Tre möjliga lösningar för nästa session

| Väg | Tid | Beskrivning |
|---|---|---|
| 1 | 15 min | Patcha yoy_seasonality till left merge (riskerar NaN i regression) |
| 2 | 30 min | `COALESCE(Master_Underkategori3, 'UNCATEGORIZED')` i export-SQL |
| 3 | 1-2 dagar | Bygg riktig L4-mappning för tjänster (kräver verksamhetskunskap) |

**Rekommendation:** Väg 2 först — snabb fix, ger elasticitet på alla ItemCodes.
Senare förfina mappningen om "UNCATEGORIZED" blir för stor grupp.

### Diagnostik-skripten

Sparade i `archives\diagnostics_2026-06-05\` + `workspace\`:
- `check_aap_dus.py` — bekräftar AAP130 finns i BCG facit (1151 ItemCodes)
- `check_input_layer.py` — bekräftar AAP130 har 1407 rader i vår input
- `check_control_file.py` — bekräftar AAP130 saknas i control_file (downstream-konsekvens)
- `check_pg4_dropout.py` — bevisar 834 ItemCodes har 100% NULL pg4
- `verify_104w_filter.py` — kvantifierar 103-veckors-filtret (5.9% omsättning droppas där)

---

## DAGENS LEVERANS

### Output - var ligger filerna

```
C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\_archive_growing_2026-04-27\
```

OBS: Outputen representerar bara 317 ItemCodes (de med non-null pg4), inte 1151. **Använd inte
för affärsbeslut** innan rotorsaken är fixad. Compare-rapporten är vilseledande.

### Validerad omsättning (för externa rapporter)

Vår input CSV (växande fönster 2022-07 → 2026-04-27):
- Sum TotalNet: **8,269,105,588 SEK** (brutto inkl VAT)
- Sum TotalNetXVat: **6,615,284,470 SEK** (netto ex VAT)
- Sum SoldQuantity: 7,970,132 enheter
- Sum NoofUnits: 91,511,288

Frusen fönster delmängd (2022-07-01 → 2025-06-28), för direkt jämförelse mot BCG:
- TotalNet: 6,495,044,684 SEK (BCG: 6,505,900,000 SEK — diff 0.17%)
- SoldQuantity: 6,473,551

Per år (2022 är halvt år):
- 2022: 975 MSEK
- 2023: 2,217 MSEK
- 2024: 2,280 MSEK
- 2025: 2,134 MSEK
- 2026 (Q1+): 662 MSEK

### Commits från idag

| Steg | Commit |
|---|---|
| F.6: Cluster pipeline på växande | 5b0ac65 |
| LESSONS_BCG.md återställd | 0991aaa |
| LOCKED_ASSUMPTIONS.md (LF.1-7) | 618dd85 |
| Repo-rot städad | 2ea61bc |
| NEXT_SESSION + LF | fbbb810 |
| NEXT_SESSION + diag arkiverade | ed1f88e |

---

## VÄNTAR PÅ EXTERN INPUT

- **Mail till IT skickat.** Väntar på svar.

---

## VAD SKJUTS UPP

- **A+B-bygget** (affärspresentation + rullande volym) — blockerat till pg4-fixen är klar
- F.8/F.9 (Site, Bundle, multi-modell-väv)
- KÄRNPRINCIPER-patch
- TILL_RADERING\ permanent radering

---

## NYA LF-KANDIDATER för LOCKED_ASSUMPTIONS

### LF.8 (kandidat) — yoy_seasonality kräver non-null service

BCG:s pipeline förutsätter komplett `ProductGroupL4Name`-mappning. NULL-värden där betyder
hela KEY tappas. Vår DW-mappning (Master_Underkategori3) är halv-NULL för tjänster —
detta blockerar 72.5% av ItemCodes från modellen.

**Status:** Identifierat. Beslut om handling i nästa session.

---

## SNABBSTART NÄSTA SESSION

1. `cd C:\Projekt\BCG && git status` — verifiera ren
2. Läs ovan: pg4-NULL är rotorsaken
3. Välj Väg 1, 2 eller 3 (rekommendation: Väg 2)
4. Implementera, kör om pipelinen, validera
5. **Detta är blockerande för all framtida elasticitets-analys**

---

*Skapad 2026-06-05 vid sessionsslut efter iterativ djupgrävning. ~8h session.
Stora upptäckter: LF.1-7 formaliserade, repo strukturerad, 60%-bortfall **rotorsak bevisad**:
ProductGroupL4Name halv-NULL → yoy_seasonality inner merge droppar 834 ItemCodes (tjänster).*
