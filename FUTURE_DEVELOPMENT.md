# FUTURE_DEVELOPMENT — Idéer och vidareutvecklings-spår

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde)
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Skapad:** 2026-06-08
**Senast uppdaterad:** 2026-06-08

---

## Vad detta dokument är (och inte är)

`FUTURE_DEVELOPMENT.md` är en **idébank** för vad projektet skulle kunna bli efter att kärnleveransen
är klar. Här ligger förslag som upptäckts under arbetet men som **inte är blockerande för pågående
fas**.

**Detta är inte:**
- **Pågående arbete** → `NEXT_SESSION.md`
- **Lärdomar / fällor som hänt** → `LESSONS_BCG.md` (LB.N)
- **Affärsinsikter** → `INSIGHTS_BCG.md` (IB.N)
- **Låsta designbeslut** → `LOCKED_ASSUMPTIONS.md` (LF.N)
- **Roadmap-faser** → `ROADMAP.md`

**När en idé härifrån mognar till en konkret leverabel → flyttas den till `ROADMAP.md` som ny fas.**

---

## Format för varje post

```
### FD.N — Kort titel
**Idé:** Vad det handlar om
**Värde:** Vad det skulle möjliggöra
**Beror på:** Vad som behöver vara klart innan
**Estimerad omfattning:** Hög/Medel/Låg
**Status:** Idé / Skissad / Specad / Pausad
**Datum identifierad:** YYYY-MM-DD / Källa
```

---

## Snabbindex

| ID | Idé | Status |
|---|---|---|
| FD.1 | Nattkörningar — fire-and-forget automation | Idé |
| FD.2 | Azure Blob Storage för pull-baserad output | Skissad (väntar Kent) |
| FD.3 | Schemalagda körningar (cron / Azure Automation) | Idé |
| FD.4 | Övervaknings-loggning och larm | Idé |
| FD.5 | Excel-varning i validation-receipts | Skissad (känd, ej kritisk) |
| FD.6 | README för valideringsmetodik som generell standard | Skissad |
| FD.7 | FTE Way 2 — DW-native från Quinyx | Specad (IB.3) |
| FD.8 | DW-native L4-mappning (ersätt LF.8-beroende) | Idé |
| FD.9 | `check_env.ps1 -StartVm` med flagga för riktiga körningar | Idé |
| FD.10 | Projekt-avslutande städnings- och konsoliderings-fas | Specad |

---

## Phase Z — Productionization (FD.1–FD.4)

Dessa fyra hänger ihop som ett block — när BCG-pipelinen mognat tillräckligt för att vara produktion
istället för analys, behöver vi bygga om körnings-infrastrukturen från manuell till automatisk.

### FD.1 — Nattkörningar (fire-and-forget automation)

**Idé:** Pipeline körs på VM helt automatiskt över natten. Skriptet:
1. Startar VM via Azure CLI
2. Kör steg 1-4 sekvenserat
3. Säkerhetskopierar output till lokal disk eller Blob Storage
4. Deallokerar VM
5. Loggar utfall för granskning nästa morgon

**Värde:** Tar bort ~3-4h aktiv tid per fresh-data-körning. Frigör arbetstid för analys av output
istället för rutinmässig pipeline-orkestrering.

**Beror på:** FD.2 (Blob Storage för pull-baserad output, så VM kan deallokera utan manuell scp)
ELLER acceptans att VM:s disk används som mellanlagring tills nästa manuell hämtning.

**Estimerad omfattning:** Medel (2-3 dagars bygge inkl testning + watchdog för fallback)

**Status:** Idé. Diskuterades 2026-06-07 kväll men sköts upp som "inte ikväll, efter mer
end-to-end-bevis". Bevisat 2026-06-08 — vi har nu basen som krävs.

**Datum identifierad:** 2026-06-07 / sessionsdialog efter pg4-fix-validering

---

### FD.2 — Azure Blob Storage för pull-baserad output

**Idé:** Output-filer (output_summary, model_summary, model_results) pushas till Azure Blob Storage
av VM direkt efter körning. Lokal sida pullar när Jens behöver det — inte beroende av att VM är
igång.

**Värde:** Två fördelar: (1) VM kan deallokeras direkt efter körning utan att vi tappar output;
(2) versionerad output-arkivering över tid (Blob har soft delete och versionering).

**Beror på:** Kent eller IT ger `Storage Blob Data Contributor`-roll till antingen Jens-Owner på
RG, eller direkt på storage account. Mejlutkast existerar i FAS 1-session (per KRAVSPEC_IT.md §2.1).

**Estimerad omfattning:** Låg (1 dags bygge när rollen finns)

**Status:** Skissad — väntar på Kent.

**Datum identifierad:** Tidigare faser, formaliserad i KRAVSPEC_IT 2026-06-05

---

### FD.3 — Schemalagda körningar (cron / Azure Automation)

**Idé:** När FD.1 fungerar fire-and-forget — automatisera även **starten**. Cron på lokal maskin
ELLER Azure Automation Account triggar månatlig körning första vardagen.

**Värde:** Komplett automation från extraktion till output. Affärsverksamheten kan räkna med
fresh-data första veckan varje månad utan att be om körning.

**Beror på:** FD.1 + FD.2.

**Estimerad omfattning:** Låg (skript-jobbet är enkelt; svårigheten är att garantera robustness
över månader).

**Status:** Idé.

---

### FD.4 — Övervaknings-loggning och larm

**Idé:** När FD.3 är på plats — bygg dashboards/larm:
- Slack/teams-notifiering när körning lyckats / misslyckats
- Drift-tracking: hur mycket har totaleelasticiteten flyttat sedan förra månaden?
- Validation-receipt-länk i notifieringen

**Värde:** Operativ trygghet. Jens behöver inte aktivt kolla varje månad.

**Beror på:** FD.3.

**Estimerad omfattning:** Medel (1-2 dagar bygge + integration mot Slack/Teams).

**Status:** Idé.

---

## Övriga vidareutveckling

### FD.5 — Excel-varning i validation-receipts

**Idé:** Trots XML-character-sanering + CRLF-normalisering ger Excel `"We found a problem with
some content"` när validation-receipts öppnas. Filerna fungerar efter "Yes" men varningen är
fortfarande där.

**Värde:** Cleaner UX för externa kollegor som inte är vana att klicka bort Excel-varningar.

**Beror på:** Inget.

**Estimerad omfattning:** Låg (1-2 timmar djupdykning i openpyxl + ev. font-referens / tomma
trailing rows / specifik Excel-quirk).

**Status:** Skissad — utreds nästa session efter VM-körningens flyt återställts. Inte stoppande.

**Datum identifierad:** 2026-06-07 — kvarvarande efter första försöket att fixa.

---

### FD.6 — README för valideringsmetodik som generell standard

**Idé:** Dokumentera vad som funkar bra i Jens valideringsmetod:
- Single-sheet raw stdout Excel-kvitto (matchar verify_tool-stil från 28 maj)
- Master-runner som kör alla i sekvens
- Status-summering (PASS / REVIEW / FAIL / INFO / SKIP)
- Datumstämplad arkivmapp `receipts/YYYY-MM-DD/`

Lärdom som ska bli **generell standardprincip för alla framtida valideringspipelines** i Jens
projekt — inte bara BCG.

**Värde:** Återanvändbart mönster. Nästa projekt slipper återuppfinna.

**Beror på:** Inget.

**Estimerad omfattning:** Låg (1 dag att skriva utförlig README-fil + templates).

**Status:** Skissad. Borde bli `MASTER_VALIDATION.md` när tiden är inne.

**Datum identifierad:** 2026-06-07 / vid receipt-format-omarbetning.

---

### FD.7 — FTE Way 2 — DW-native från Quinyx

**Idé:** Ersätt Way 1 (BCG:s frusna interpolerade FTE-fil, slutar 2025-06) med Way 2 (egen
härledning från `Manual.Fact_Quinyx_DayClinic`). Beskrivet i `INSIGHTS_BCG.md` (IB.3) och
`TECHNICAL_PREREQUISITES.md`.

**Värde:** Eliminerar FTE-coverage-gapet (19.89% NULL för perioder efter 2025-06). Fresh-data-
körningar får komplett FTE.

**Beror på:** Bevis att Cluster/Site/Bundle alla fungerar på växande data (= FAS F klar). Sedan
parallellt delprojekt: design + bygg + validering av Quinyx-aggregering mot BCG:s Way 1 på
överlappande period.

**Estimerad omfattning:** Medel-Hög (egen pipeline-modul, kräver bevisning mot Way 1).

**Status:** Specad (i `LOCKED_ASSUMPTIONS.md` LF.6 och `INSIGHTS_BCG.md` IB.3).

---

### FD.8 — DW-native L4-mappning (ersätt LF.8-beroende)

**Idé:** Bygg egen `Manual.Item_Pg4`-tabell eller utöka `Manual.MasterListProducts` för att täcka
Klinisk + Lab-segmenten. När detta finns kan vi släppa beroendet av BCG:s frusna 0828-CSV för
`ProductGroupL4Name`.

**Värde:** Self-contained datapipeline. Färska ItemCodes som dyker upp efter BCG:s 2025-07-extrakt
får automatisk pg4-mappning. Affärsmässig ägarskap av produkthierarkin för veterinärtjänster.

**Beror på:** Affärs-/förvaltningsbeslut: vem äger den vetenskapliga produktkategoriseringen för
tjänster framåt? Kategorierna ska kunna utvecklas över tid (nya tjänster, omklassningar).

**Estimerad omfattning:** Medel (DW-modellering) + Hög (förvaltningsstruktur).

**Status:** Idé. Logged i LF.8.

**Datum identifierad:** 2026-06-05 / vid pg4-bortfalls-diagnos.

---

### FD.9 — `check_env.ps1 -StartVm` med separat flagga för riktiga körningar

**Idé:** `-StartVm`-flaggan deallokerar idag VM automatiskt om något FAIL upptäcks. Detta är fel
beteende när du faktiskt vill köra pipeline efteråt (du fastnar i loop: check_env -> FAIL ->
deallocate -> kör check_env igen -> dealloc igen).

Lägg till `-StartVmForRun` (eller `-NoDealloc`) som **inte** deallokerar oavsett utfall. Eller:
kör inte deallocation om något steg är FAIL pga SSH-timeout (legitim "ge VM mer tid").

**Värde:** Mindre friktion vid VM-körningar.

**Beror på:** Inget.

**Estimerad omfattning:** Låg (~1h ändring + testning).

**Status:** Idé.

**Datum identifierad:** 2026-06-08 / morgonens VM-omstart.

---

### FD.10 — Projekt-avslutande städnings- och konsoliderings-fas

**Idé:** I slutet av evbcgpricing-projektet (när alla F-faser är gröna och Step 6 Fall_Back_Logic
är validerad), kör en dedikerad fas för:
- (a) Genomgång av all dokumentation (LB/IB/LF/FD är konsekventa, inga dubbletter)
- (b) Städning av repo och arkiv (TILL_RADERING/ permanent rensning, _archive_*/ konsolidering)
- (c) Konsolidering av alla valideringar gjorda bakåt (single source of truth-rapport)
- (d) Tvärgranskning av lärdomar — vad blev MASTER-värdigt, vad förblir projektspecifikt
- (e) Färdigställande av KRAVSPEC_IT och leverans till Kent
- (f) README-uppdatering med slutgiltigt overview

**Värde:** Förvaltbar slutprodukt. Nästa person (eller du själv om 6 månader) kan ta över utan
att gräva i sessions-historik.

**Beror på:** Alla F-faser gröna + Step 6 (Fall_Back_Logic) validerad på växande data.

**Estimerad omfattning:** Medel (1-2 dagars fokuserad genomgång).

**Status:** Specad (i minnet sedan 2026-06-07).

---

## Hur posten levs

Ny FD läggs till när:
- En idé för förbättring/utbyggnad upptäcks under en session
- Något skjuts upp som "inte nu, men senare"
- En begränsning i nuvarande lösning identifieras som inte är blockerande

En FD revideras eller flyttas:
- När idén mognat till konkret leverabel → flyttas till `ROADMAP.md` som ny fas
- När idén visat sig oviktig efter mer kontext → markeras "Avförd" med skäl
- När en LF eller LB exponerar att FD inte längre är aktuell → uppdatera status

---

## Senaste uppdateringar

| Datum | Vad |
|---|---|
| 2026-06-08 | Fil skapad. Initiala FD.1-10 dokumenterade efter VM-körningens slut. |
