# ROADMAP — evbcgpricing: från replikering till produktion

**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Repo:** https://github.com/Dennyakillen/evbcgpricing.git
**Senast uppdaterad:** 2026-06-12 (FAS A PÅGÅR — orchestrator-motorn bevisad: site-steget körs end-to-end via Azure, validerat bit-för-bit mot facit)

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
                  (KLAR)        (öppen)      (KLAR)        (PÅGÅR)
```

**Statusen i en mening (2026-06-12):** Replikeringen är bevisad, färsk-data-driften är klar, och
FAS A har börjat — en orchestrator-motor kör nu site-modellsteget end-to-end via Azure och
reproducerar facit bit-för-bit (6624 KEY, korr 1.000000). Kvar i FAS A: cluster-runner, lokala
Excel-/Step6-faser i sekvensen, extraktions-fas (lokal→Blob→VM, då DW ej når från VM — LB.58),
webbvy, samt full autonomi som beror på IT-roller (FAS T, ABAC-blockerad Blob-dataroll).

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

### ✅ FAS F — Färsk data — KLAR (2026-06-11)
Köra samma logik på 2026-data i stället för BCG:s arkiverade input. **Klar i hela kedjan:**
`transaction_data.parquet` regenererad till 2026-04-30 (27,4M rader), G7-parametrisering komplett,
alla tre modellfamiljer körda växande, Step 6-väven körd och validerad, modellen matbar.

Delsteg (F.7-F.10), alla klara:
- **F.7 Cluster** ✅ — step 5 fallback-blend körd växande (4180 KEY, 33.4%→45.2% signifikans).
- **F.8 Site** ✅ — steg 1-4 på VM (~70 min, 6624 KEY), steg 5 lokalt. Arkitektonisk lärdom: Excel-stegen
  (5 + Step 6) körs lokalt, modellstegen (1-4) på VM (LB.44).
- **F.9 Bundle** ✅ dataprep körd växande, **modellen PARKERAD på evidens** (FD.11): bundle vinner bara
  2,2 % av besluten i väven trots 23,9 % av transaktionsvolymen (IB.12). Återbesöks-trigger dokumenterad.
- **F.10 Step 6** ✅ (`Fall_Back_Logic.py`) — körd första gången växande: 108 979 rader / 15 128 produkter,
  median −0,497, 100 % negativa, 100 % i (−10,0). Körs via `run_step6.py` (tolererar LB.53-mallfelet).
- **Output-rimlighetsgrind** ✅ — på färsk data finns inget facit; grinden bedömer negativ/band/drift.
  Utfall: 95 % drift <0,5, omsättningsvägd elasticitet −0,532→−0,512 (stabilt). MBAS0703 + SBCS0153
  bedömda som svag-signal-brus (IB.10), faller ej ur bandet.
- **Modellmatning** ✅ — `build_r12_for_model.py` producerar R12 volym/oms + elasticitet per kod×site
  (99,5 % match) i copy-paste-format till BCG-Excelens blå flikar.
- **Tre frusna lås** (LF.9): väv-vikter (FD.14), steg-5-routning (FD.15), bundle-gren (FD.11) står på
  2025-värden — medvetet, dokumenterat, med uppdaterings-roadmap. Kärnsignalen är färsk.
**Bevisar:** Vi kan producera färska elasticiteter — själva produkten — och mata in dem i prismodellen.
**Mognad:** Grön/klar. Nästa: FAS A (produktionssättning).

### 🟡 FAS A — Robust Azure-miljö — PÅGÅR (orchestrator-motorn bevisad 2026-06-12)
Flytta den städade strukturen till en hållbar Azure-miljö, körbar och ev. schemalagd — så replikeringen
inte bara bor i Jens repo ("en Ferrari i ett garage"), utan i en driftmiljö verksamheten äger.
**Bevisar:** Produktionsmognad — körbar av fler än Jens, övervakad, återkommande.

**Framsteg 2026-06-12 (Phase Z, första bygg- och körsessionen):**
- **Orchestrator-motorn byggd och bevisad.** `orchestration/` kör site-modellsteget (steg 1-4) end-to-end
  via Azure: startar VM, kör BCG:s `launcher.py` detached (setsid, LB.54), skriver delbar status till
  Blob, hämtar output, deallokerar utfallsstyrt (LB.56). BCG-koden orörd — runnern anropar den som Jens
  gör för hand.
- **Validerat mot facit:** orchestratorns output bit-för-bit identisk med 2026-06-09 manuella körning
  (6624 KEY, korr 1.000000, max_abs_diff 0). Kvitto i `workspace/validation_receipts/`.
- **Tre felmoder bevisat hanterade live:** seg kallstart (CZ.6-retry), SSH-detach-bugg (LB.54, fixad +
  isolerat verifierad 1,4 s), skarp VPN-tunnelglapp mitt i körning (LB.55, svald av retry — körningen
  överlevde).
- **Prefect utrett och förkastat** för denna miljö: dess dashboard når inte kollegan utan publik IP /
  reverse proxy → löser inte nätväggen, lägger till serverkomponent. Hemmabygget (Blob-statusfil) är rätt
  för Evidensias låsta miljö. Återbesök om flera pipelines/utvecklare uppstår.
- **DW-åtkomst från VM mätt = `BLOCKED`** (LB.58): extraktionen kan inte flytta till Azure (IP-vitlistning).
  Beslutad arkitektur: lokal extraktion → Blob → VM (FD.17).

**Kvar i FAS A:** cluster-runner (copy-adapt av site, ~5 konstanter), site steg 5 + Step 6 som lokala
faser i sekvensen, sekvenserare över alla faser, extraktions-fas (FD.17, egen session), webbvy ovanpå
statusfilen, VM-sidigt auto-shutdown-skyddsnät (FD.16). AAD-dataroll för MI (ABAC-blockerad → FAS T)
ersätter kontonyckel-läget.

**Mognad:** Gul→grön på modellsteget (bevisat körbart automatiserat). Beroende kvar: FAS T (IT-roller
för full autonomi — Blob-dataroll bakom ABAC). Startspecifikation i `FUTURE_DEVELOPMENT.md` Phase Z
(FD.1-4, FD.16-17). NEXT_SESSION har konkreta nästa steg.

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
