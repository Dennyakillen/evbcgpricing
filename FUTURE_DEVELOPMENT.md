# FUTURE_DEVELOPMENT — Idéer och vidareutvecklings-spår

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde)
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Skapad:** 2026-06-08
**Senast uppdaterad:** 2026-06-11

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
| FD.11 | Bundle-modellens färdigställande (parkerat, väv-beroende) | Pausad |
| FD.12 | Bundle Ray-init till config-driven (matcha Cluster/Site) | Idé |
| FD.13 | Sandbox-Excel: dynamisk metodik-förklaring mot beslutsfattare | Specad |
| FD.14 | Väv-vikter växande (ersätt frusen Complete_Product_Data 2025) | Idé |
| FD.15 | Cluster steg-5-blend växande (43 reps, routning fryst 2025) | Idé |

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

### FD.11 — Bundle-modellens färdigställande (PARKERAT — väv-beroende, ej avfärdat)

**Idé:** Köra den tredje modellfamiljen (Bundle / varukorgar) end-to-end på växande data:
Ray-varukorgsbygge → Bundle-modell (steg 1-4 på VM) → steg 5 lokalt. Dataprep-källan är redan
klar (se nedan); det som återstår är varukorgsbygget + modellen.

**Beslut 2026-06-11: parkera, men förbered återbesök.** Cluster (F.7) och Site (F.8) är klara på
växande data och täcker huvudsortimentet. Bundle bedöms inte vara på kritiska vägen mot affärsbeslut
på växande data *just nu* — men beslutet är datadrivet och har en tydlig återbesöks-trigger (se nedan),
inte ett permanent avförande. Bollen: färska affärselasticiteter på huvudsortimentet snabbare, inte
teknisk fullständighet (ROADMAP-tesen, IB.6).

**Materialitet (uppmätt 2026-06-11, `assess_bundle_materiality.py`):**
- Total växande omsättning (brutto, ankare ≥2022-07-01): **12,15 mdr**.
- Alla varukorgs-*transaktioner*: 2,91 mdr (23,9% av total) — MEN detta överlappar Cluster/Site
  (samma pengar, alternativ prissättning), är INTE additivt.
- Av 63 737 definierade varukorgar markerade BCG endast **98** som värda att modellera
  (`To_run_elasticity_analysis=1` = 0,15%).
- De 98 modellerade varukorgarnas omsättning: **526 M** (~4,3% av total, 11,5% av all
  varukorgs-def-omsättning). Detta är den relevanta materialiteten — inte 23,9%.
- Service-mix (var varukorgarna koncentreras): Imaging 32%, Anaesthesia 24%, Hospitalisation 20%,
  Other 12%, Surgery 7%, Consult 6%. → Sjukhustjänster som ofta säljs tillsammans i ett besök.

**Vad som brister utan Bundle:** Per-varukorgs-prissättning på ~526 M i sjukhustjänster (röntgen +
sövning + inläggning säljs ofta ihop). På produkt×klinik-nivå (Cluster/Site) kan enskilda komponenter
ha tunn prisvariation → bli insignifikanta. Som varukorg KAN elasticiteten vara mätbar där komponenten
inte är det. Utan Bundle saknas alltså en möjlig räddningskälla för just dessa KEY:n i fallback-väven.

**Vad utvecklingen öppnar för:** Om sjukhustjänsternas KEY:n visar sig tunna/insignifikanta på
Cluster/Site-nivå, blir Bundle den enda källan som räddar dem i FR-7-väven → varukorgs-prissättning
för hospital-segmentet blir möjlig.

**Återbesöks-trigger (datadriven):** Kör rimlighetsgrinden + Step 6 på Cluster+Site först. **Om**
Imaging/Anaesthesia/Hospitalisation-KEY:n ofta blir insignifikanta eller saknar källa i väven → lyft
Bundle tillbaka till kritiska vägen (då räddar det dem). **Om** de redan prissätts väl av Cluster/Site
→ Bundle förblir parkerat. Bundles sanna drivande effekt = hur ofta det blir *vald källa* i väven,
vilket är strukturellt omätbart utan Step 6 (cirkulärt: Step 6 kräver Bundle-output). Rimlighetsgrinden
ger den fullare domen.

**Redan gjort (dataprep-källan, klar och committad 2026-06-11, commit `1daf093`):**
- Växande `sweden_master_data.parquet` på plats i Bundle-parquet-mappen (27,4M rader, YearFlag t.o.m.
  Jun 26).
- Bundle-SQL-dataprep körd växande via `run_bundle_dataprep.py` (duckdb-Python, AppLocker-rent, LB.2).
  Output `Raw_Data_Clinic_Hospital.csv` verifierat växande (`verify_bundle_growing.py` → max-week
  2026-04-27).
- YearFlag-kapningen i `01_process.sql` patchad till konstant-ankare-filter (ingen tyst kapning framåt,
  `patch_bundle_yearflag.py`).
- Tre statiska inputs lokaliserade + recept dokumenterat (`input/README.md`).

**Återstår (kartlagt 2026-06-11, ej löst — den tekniska skulden):**
- **Ray-varukorgsbygget** (`2.Sweden_Bundle_Clinic_Model_Data_Creation.py` + `bundle_utils.py`) har
  UK-rester och otestade input-kontrakt:
  - Config-nyckel `uk_bundles` läses som `sweden_bundles` av scriptet → **KeyError** vid körning.
  - `config_data_prep.yml` pekar på BCG:s frusna `0826_*`/`0825_*`-filnamn, inte våra växande outputs.
    `data/`-mappen är tom — våra outputs måste placeras med rätt namn.
  - `build_bundle_for_type` joinar `txn.ProductCode` mot `uk_bundles["Product Code"]` — varukorgs-input
    ska vara den EXPLODERADE `Bundle_Clinic_Data.csv` (en rad per Bundle×ProductCode), inte
    `sweden_bundle_analysis.csv` (komma-separerad Bundle-sträng).
  - FTE trippel-mismatch: scriptet gör `pd.read_excel` + förväntar `Clusters`/`FTE`-kolumner; vår
    dataprep gav CSV med `Cluster`/`total_FTE`. Kräver en format- och kolumn-bro.
- **VM-patchar** (samma som Cluster/Site): `feature_selection.py` ray_spill C:\→/tmp (LB.34),
  `bundle_utils.py` object_store 2GB→8GB (se FD.12).

**Estimerad omfattning:** Medel-Hög (UK-kod-broar + premiär VM-körning av tredje familjen).

**Status:** Pausad (dataprep-källa klar; varukorgsbygge + modell kvarstår som väv-beroende utveckling).

**Datum identifierad:** 2026-06-11 / efter materialitetsmätning + UK-kod-kartläggning.

---

### FD.12 — Bundle Ray-init till config-driven mönster

**Idé:** `bundle_utils.py` rad 14 har `object_store_memory=2 * 1024**3` hårdkodat, utanför
config.yml. Cluster löste Ray-minne via `config.yml ray: memory: 8` (LB.4), men Bundle lade init i
separat fil → config/env biter inte. Migrera Bundle-Ray-init till att läsa från config (som
Cluster/Site), så Ray-minnet styrs konsekvent på ett ställe.

**Värde:** Konsekvent Ray-konfiguration över alla tre familjer; inga gömda hårdkodade minnesgränser
som kväver kombinatoriken på VM.

**Beror på:** FD.11 (relevant först när Bundle-modellen körs).

**Estimerad omfattning:** Låg (~1h). Vid premiär-körning gjordes medvetet hårdpatch till 8 GB istället
(scope-disciplin — config-migrering är inte premiär-arbete).

**Status:** Idé.

**Datum identifierad:** 2026-06-10 / Bundle Ray-inventering (Blockare 3 i F9_BUNDLE_INVENTORY).

---

### FD.13 — Sandbox-Excel: dynamisk metodik-förklaring mot beslutsfattare

**Idé:** En dynamisk Excel-fil där modellens alla steg hänger ihop med **exempeldata** (sandbox-tänk):
transaktion → veckoaggregering → regular-price → feature-selektion → OLS-elasticitet → fallback-väv
→ slutelasticitet per ProductKey. Grov men sammanhängande — inte exakt replik, utan så att en
beslutsfattare kan *följa* hur en prisförändring propagerar genom kedjan och förstå var elasticiteten
kommer ifrån. Steg synliga, formler spårbara, exempel man kan ändra och se effekten.

**Värde:** Översätter en komplex Python/Ray/DuckDB-pipeline till något verksamheten kan följa och
LITA på. Skillnaden mellan "modellen funkar tekniskt" och "verksamheten vågar prisbesluta på den".
Särskilt värdefullt för fallback-väven (FR-7), som är svårast att förklara muntligt — i Excel kan
man visa hur en KEY får sin elasticitet från Cluster, Site eller Bundle beroende på signifikans.
Knyter an till bollen: affärsbeslut på växande data kräver att besluts­fattare förstår underlaget.

**Beror på:** Inget hårt — kan börjas när som helst. Mognar bäst när Step 6-väven är körd på växande
data (då finns riktiga exempel att grovmodellera kring).

**Estimerad omfattning:** Medel (1-2 dagar för en genomtänkt, sammanvävd sandbox med exempeldata och
spårbara formler per steg).

**Status:** Specad (idé formulerad 2026-06-11).

**Datum identifierad:** 2026-06-11 / sessionsdialog om metodik-förståelse mot beslutsfattare.

---

### FD.14 — Väv-vikter på växande data (ersätt frusen `Complete_Product_Data.xlsx`)

**Idé:** Step 6:s fallback-väv viktar elasticiteter med omsättning (`wt_elas = elasticity ×
TotalNet`). Vikterna kommer från `6. Fall Back Logic\input_data\Complete_Product_Data.xlsx` —
en Alteryx-output med kolumnen `SalesTotal_YearEnding25` (hårdkodat 2025-årtal). Filen är BCG-facit
(108 984 rader, identifierad av `verify_provenance` 2026-06-11). Bygg en växande motsvarighet så
vikterna speglar färsk omsättning.

**Värde:** Idag viktas även växande Cluster/Site-elasticiteter med **frusen 2025-omsättning**. Själva
elasticiteten (priskänsligheten) är färsk, men aggregeringen/viktningen är låst vid 2025. För
top-line-beslut spelar det troligen liten roll (elasticiteten är huvudsignalen), men vikterna avgör
hur enskilda KEY:n väger i service-/produkt-fallbacknivåerna (F5-F7). Växande vikter gör hela väven
färsk, inte bara elasticiteterna.

**Beror på:** Alteryx Modul 4 (producerar `Complete_Product_Data`) — eller en DuckDB-ersättning som
bygger samma kolumner (`ItemCode, ItemDescription, ProductGroupL4Name, ID_Department, Cluster,
New_Cluster, SalesTotal, SalesTotal_YearEnding25`) från växande masterdata. Det senare är i linje med
att vi redan ersatt Modul 1/2/3/6 med DuckDB (Modul 4 var det sista Alteryx-beroendet).

**Estimerad omfattning:** Medel (DuckDB-bygge som speglar Modul 4:s aggregering + validering mot facit-
strukturen). Notera: `YearEnding25`-kolumnen bör generaliseras till ett rullande 12M-fönster, inte ett
hårdkodat årtal (samma princip som LB.50 konstant-ankare).

**Status:** Idé. Identifierad av `verify_provenance`-suiten (provenance-validering) 2026-06-11.

**Datum identifierad:** 2026-06-11 / provenance-validering av Step 6-inputs.

---

### FD.15 — Cluster steg-5-blend på växande data (43 reps / service-granularitets-routning)

**Idé:** Step 6 läser `final_model_cluster_granularity.xlsx` (steg-5-blendens 43 representanter, som
routar varje tjänst till sin blend-granularitet). Den enda versionen i repot är `_Ivce`-facit
(2025-12-08) — steg-5-blenden regenererades **aldrig** på växande data, bara Cluster-modellens steg
1-4 (`output_summary`). Kör `fallback_blend.py` på växande Cluster-output så routningen blir färsk.

**Värde:** Routningen som avgör vilken granularitet varje tjänst får i väven är idag fryst vid BCG:s
2025-struktur. Om tjänste-/klustersammansättningen ändrats (nya kliniker, omklassningar — jfr IB.11
drift) kan routningen vara fel för växande data. Färsk steg-5-blend säkrar att representant-valet
speglar nuläget.

**Beror på:** Växande Cluster steg 1-4 output (finns, `_archive_growing_2026-04-27_v2_pg4fix`).
`fallback_blend.py` är redan validerad bit-för-bit (FR-3, 43/43 reps) — det här är att köra den på
växande input istället för facit.

**Estimerad omfattning:** Låg-Medel (kör befintlig validerad `fallback_blend.py` på växande Cluster-
output, verifiera 43-reps-strukturen håller, placera outputen där Step 6 letar).

**Status:** Idé. Identifierad av `verify_provenance`-suiten 2026-06-11.

**Datum identifierad:** 2026-06-11 / provenance-validering av Step 6-inputs.

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
| 2026-06-11 | FD.11-13 tillagda. FD.11 Bundle-modellen PARKERAD (dataprep-källa klar + committad `1daf093`, varukorgsbygge/modell kvarstår) — beslut datadrivet: 98 modellerade varukorgar = 526 M (~4,3%), överlappar Cluster/Site, sann väv-effekt avgörs av rimlighetsgrind (återbesöks-trigger: sjukhustjänsters signifikans). FD.12 Bundle Ray-config. FD.13 sandbox-Excel för metodik-förståelse mot beslutsfattare. |
| 2026-06-11 | FD.14-15 tillagda efter `verify_provenance`-suiten byggdes. Provenance-validering av Step 6-inputs avslöjade tre frusna lås: väv-vikter (FD.14, frusen Complete_Product_Data 2025), steg-5-blend/routning (FD.15, _Ivce-facit 2025-12, aldrig regenererad växande), och bundle-grenen (FD.11). Step 6 vilar på växande Cluster+Site-elasticiteter men frusen viktning/routning/bundle. Suiten ligger i `verify_tool/provenance/`. |
