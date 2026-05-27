# ROADMAP — evbcgpricing: från replikering till produktion

**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Repo:** https://github.com/Dennyakillen/evbcgpricing.git
**Senast uppdaterad:** 2026-05-27 (vid FR-7-stängning, commit `96fe7a3`)

Detta dokument visar **var projektet står** och **vart det bär** — för Jens som genomförare och för
beställare/beslutsfattare. Varje fas har en mognadsbedömning: är vi redo att börja, eller beror den på
något som inte finns än?

---

## Den stora bilden

Målet är inte att replikera BCG:s modell exakt på gammal data — det bevisar bara insikter konsulterna
redan levererat (`IB.6`). Målet är att **köra BCG:s metod på Evidensias färska data, i en miljö vi själva
äger och förvaltar**. Replikeringen är grunden som bevisar att vi förstår logiken; produkten är den färska
körningen i drift.

Vägen dit, i ärlig ordning:

```
  [FR-1..7]  -->  [FAS V]  -->  [FAS T]  -->  [FAS F]  -->  [FAS A]
  Replikering     Bevis-        Teknisk      Färsk         Robust
  (KLAR)          bibliotek     skuld→IT     data          Azure-miljö
```

---

## Faser & mognad

### ✅ FR-1..7 — Replikering (KLAR, bevisad 2026-05-27)
Hela BCG-kedjan (dataprep → cluster → site → bundle → blend → fallback) replikerad och validerad mot
BCG:s eget facit. Steg 6 (F1–F7-väv) bit-för-bit identisk: korr 1,000000, |diff|=0, 100 % nivåmatch.
**Bevisar:** Vi förstår och äger BCG:s metod fullt ut.
**Lärdom från fasen:** Nästan varje hinder var fel i vår egen dokumentation, inte i BCG:s kod. Källan
trumfar anteckningarna.

### 🟢 FAS V — Bevis-bibliotek (`verify_tool`) — REDO NU
Ett bibliotek av **oberoende, repeterbara** verifierare — en per modelldel (cluster/site/bundle/fallback).
Var och en körs ensam, på begäran, och visar live *vad som jämförs mot vad* och att det stämmer.
**Användningsfall:** Beslutsfattare ifrågasätter en specifik del → kör just den verifieraren live → skärmen
visar grupper/elasticiteter/diff mot facit → tvivlet besvaras konkret.
**Bevisar:** Replikeringen är inte ett engångspåstående — den är repeterbart bevisbar när som helst.
**Mognad:** Allt finns (outputs hemtagna, facit lokaliserat, mönstret satt av `verify_fallback.py`).
Enda förarbetet: inventera befintliga `verify_*`-script så vi väver ihop, inte återuppfinner.
**Varför denna fas FÖRST:** Skuldregistret till IT (FAS T) blir trovärdigt först när det finns ett körbart
bevis bakom — "det här fungerar, därför behöver jag en miljö för det" slår en önskelista.

### 🟢 FAS T — Teknisk skuld → IT — REDO NU (parallellt med V, kräver ingen kod)
Strukturera de hinder som tvingat fram work-arounds, så IT kan ge en hållbar miljö. Vi vet dem redan:
- **Lokal OOM** på Stage 2 (~2450 grupper, 120+ min, kraschade) → därför VM. Replikeringen kan inte köras
  på en vanlig kontorsdator.
- **AppLocker** blockerar `.exe` / `pip.exe` → allt via `python -m`.
- **Execution policy** blockerar osignerade `.ps1` (`LB.21`).
- **Blob Storage-roll** (Storage Blob Data Contributor) blockerad — kräver Owner Jens ej har.
- **Public-IP-policy** på tenant → VM måste i befintlig VNet utan publik IP.
- **G7 datumhårdkodning** — inte IT, men en spärr mot färsk data som måste lyftas.
**Bevisar (för IT):** En motiverad investering, inte en önskelista. Förutsättning för FAS A.
**Mognad:** Klar att sammanställas — all kunskap finns i `LESSONS_BCG.md` / `TECHNICAL_PREREQUISITES.md`.

### 🟡 FAS F — Färsk data — DELVIS (en blockerare måste byggas först)
Köra samma logik på 2026-data i stället för BCG:s arkiverade input.
- **G7-parametrisering** — `constants.py` hårdkodar `START_DATE 2022-07-01 / END_DATE 2025-06-29`; färsk
  2026-data filtreras annars **tyst** bort. Enskilt största spärren mot affärsmålet.
- **Output-rimlighetsgrind** — på färsk data finns inget facit; grinden blir "är elasticiteten negativ,
  inom trovärdiga band, skulle diffen flippa ett prisbeslut?". Byggs INNAN första färsk-körning.
- **SQL_data_prep / DW-vy (B.4b)** — BCG:s metod på vår DW-fakta + DW-hierarki, modellkontrakt
  (`TECHNICAL_PREREQUISITES §8`). **Detta är den del som inte finns än** — DW-vyn är specad, inte byggd.
- **FTE Väg 2** — enda genuina uppströms-inputen (`IB.3`), från `Manual.Fact_Quinyx_DayClinic`. Eget
  delprojekt, blockerar ej.
**Bevisar:** Vi kan producera färska elasticiteter — själva produkten.
**Mognad:** Gul. G7 + rimlighetsgrind är moget; SQL_data_prep (B.4b) kräver bygge innan "egen data via SQL"
ens är möjligt. Att hävda att vi kör "på vår egen data" innan denna del finns vore en halvsanning.

### 🔴 FAS A — Robust Azure-miljö — INTE REDO (beror på T + F)
Flytta den städade strukturen till en hållbar Azure-miljö, körbar och ev. schemalagd — så replikeringen
inte bara bor i Jens repo ("en Ferrari i ett garage"), utan i en driftmiljö verksamheten äger.
**Bevisar:** Produktionsmognad — körbar av fler än Jens, övervakad, återkommande.
**Mognad:** Röd. Beror på FAS T (IT måste ge miljön — roller, compute, nät) OCH FAS F (det måste finnas
något färskt att köra). Att bygga produktionsmiljö nu vore att flytta bilen innan vi vet att den startar
på verklighetens bränsle (vår SQL-data), inte bara BCG:s testbränsle.

---

## Rekommenderad ordning & motivering

**V → T → F → A.** V och T kan löpa parallellt (T kräver ingen kod). F efter att V gett ett bevis och T
gett en miljöriktning. A sist — först när IT levererat miljö (T) och färsk data fungerar (F).

| Fas | Beror på | Kan börja |
|---|---|---|
| V | — | Nu |
| T | — (men trovärdigare efter V) | Nu, parallellt |
| F | SQL_data_prep måste byggas (B.4b) | Delvis nu (G7, grind); SQL-delen efter bygge |
| A | T (IT-miljö) + F (något att köra) | Inte än |

---

*Skapad 2026-05-27 av Jens Palmö (utvecklare) med AI-rådgivaren, vid FR-7-stängning. Ersätter inte
playbookens riktningsblock — kompletterar det med fas-/mognadsvyn för beslutsfattare.*
