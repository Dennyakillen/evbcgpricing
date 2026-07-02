# FUTURE_DEVELOPMENT — Idéer och vidareutvecklings-spår

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde)
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Skapad:** 2026-06-08
**Senast uppdaterad:** 2026-07-02

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

> **NÄSTA SESSION — Phase Z kickoff: produktionssätt i Azure.**
> FAS F är klar (2026-06-11): alla tre modellfamiljer körda på växande data, Step 6-väven körd och
> validerad, modellen kan matas end-to-end (`build_r12_for_model.py`, 99,5 % elasticitet-match).
> Replikeringen är bevisad (FR-1..7, korr 1.000000) och dokumenterad (`REPLIKERING_OCH_VALIDERING.md`).
> Den naturliga nästa fasen är ROADMAP **FAS A** — flytta den städade, validerade strukturen till en
> hållbar Azure-miljö som verksamheten äger, körbar och ev. schemalagd.
>
> **Sessionen i en mening:** ta modellen från "körbar på Jens arbetsstation + VM on-demand" till
> "körbar i en driftmiljö Evidensia äger" — börja med det som inte är blockerat och bygg uppåt.
>
> **Startordning (minst beroende först):**
> 1. **Förutsättnings-grind (FD.1-anda):** lista exakt vad en nattkörning kräver — VM-start/stopp
>    automatiserat, sökvägar, venv, output-placering. Mycket finns redan (`run_step6.py`,
>    `build_r12_for_model.py` är omkörbara; VM-start/deallocate dokumenterat i UBUNTU_AZURE_VM).
> 2. **IT-ask (ROADMAP FAS T → A):** Blob Storage-roll (Storage Blob Data Contributor, blockerad av
>    Owner-behörighet Jens saknar), public-IP-policy, compute. Sammanställ från KRAVSPEC_IT +
>    TECHNICAL_PREREQUISITES. Detta är förutsättningen — bygg inte miljön innan IT gett rollerna.
> 3. **FD.2 Blob Storage** för pull-baserad output (väntar Kent) → **FD.3** schemalagda körningar
>    (Azure Automation / cron) → **FD.4** övervaknings-loggning och larm.
> 4. **Projektavslut (FD.10):** städnings- och konsolideringsfasen — kör `cleanup_plan.ps1`,
>    verifiera att inget brutits, committa den slutliga strukturen.
>
> **Pre-flight (om VM behövs):** sätt rätt subscription FÖRE VM-kommandon (LB.46):
> ```powershell
> az account show --query "{user:user.name, subscription:name}" -o table
> az account set --subscription "ev-lz3-ai (SE)"
> az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
> # Deallocera när klart: az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
> ```
>
> **Förväntat utfall:** en dokumenterad väg från manuell körning till driftmiljö, IT-asken
> sammanställd och inlämnad, och de delar som kan byggas utan IT (omkörbara skript, output-struktur)
> på plats. Det som blockeras av IT-roller väntar — men är specificerat så det kan börja direkt när
> rollerna ges. **Detta ersätter den tidigare NEXT_SESSION.md** (vars FAS F-uppgift nu är klar).

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

| FD.16 | Automatiskt VM-kostnadsskyddsnät (auto-deallocate/larm) | Idé |
| FD.17 | Lokal extraktionskedja → Blob → VM (arkitektur) | Delvis byggd |
| FD.18 | SEK-kostnadsvisning i körlogg + statusvy | Skissad |
| FD.19 | Kollega-vänlig motor-dashboard (lager 2-3) | Skissad |
| FD.20 | Blob-output per familj (namngivning) | Specad |
| FD.21 | Frontend speglar BCG:s mappstruktur | Önskad |
| FD.22 | Live-tickande körtid + summering i frontend | **Byggd** (FAS 18, dashboard.html) — indexrad rättad 2026-07-02 |
| FD.23 | Export per steg + fylligare svenska loggtexter | Önskad |
| FD.24 | --launch-test ärver poll-loopens tunneltolerans | Specad |
| FD.25 | Orchestrator frozen/growing-väljbar (replikerings-demo) | Idé |
| FD.26 | run_data.py: ett kommando kör hela lokala bränsleledet | Nästa sessions mål |
| FD.27 | Webapp-vägledning i extraction-steget (how_sv-fält) | Designad, ej byggd |
| FD.28 | Container-per-familj som speglar BCG:s mappstruktur | Önskad (finåkning) |
| FD.29 | AAD-övergång för upload_inputs när Blob-datarollen finns | Väntar FAS T/Kent |
| FD.30 | Avslutade körningar sätter sluttillstånd | Byggd |
| FD.31 | Cluster/Site/Step5/Step6/R12-runners lager 2-status | Delvis |
| FD.32 | Webapp facit→nu: rimlighet & liv, ej modellöverlägsenhet | Byggd |
| FD.33 | Migrera Blob till BCG-speglande pipeline-struktur | Önskad (A räcker) |
| FD.34 | Bundle aktiverad som fullvärdig familj (skuld stängd) | Byggd 2026-06-16 |
| FD.35 | Konto-spretighet: ett hem för status+output+facit | MÅSTE lösas före end-to-end |


### FD.26 — run_data.py: ett kommando kör hela det lokala bränsleledet
**Idé:** En orkestrerande runner (run_site_model.py-stil) som körs en gång — från terminal ELLER
genom att öppna och trycka Kör i VS Code — och kedjar: (1) regenerera parqueten
(regenerate_transaction_parquet_chunked.py), (2) kör data prep (replicate_dataprep.py), (3) ladda upp
parqueten till Blob (upload_inputs, verifierad 2026-06-15). Flaggor: --skip-regen/--skip-prep/--skip-
upload/--end ÅÅÅÅ-MM-DD.
**Värde:** Jens "så lite Python som möjligt utanför Azure" = få MOMENT, inte få rader. Ett skript att
peka på i webappen. Anropar BEFINTLIGA bevisade skript (A.9), återimplementerar inte.
**Beror på:** upload_inputs (KLAR). Korsar tre repon — runnern limmar, äger inte stegen.
**Designfakta (mätt 2026-06-15):** upload 1 GB ≈ 2 min, ~9 MB/s → SYNKRONT steg, ingen detach behövs.
**Estimerad omfattning:** Medel. **Status:** Nästa sessions primära mål. Bygg utan statusrapportering
först (lager 1); statuskontrakt-skrivning som lager 2 (extraction-fasen finns i run_status.py).
**Datum identifierad:** 2026-06-15.

### FD.27 — Webapp-vägledning i extraction-steget (how_sv-fält)
**Idé:** how_sv-fält på extraction-fasen i story_config.py + renderingsrad i dashboard.html (samma
if(st.X)-mönster som why/use/without, rad 228-231). Texten säger kollega-vänligt HUR datan når Azure:
kör run_data.py lokalt (var det ligger, att DW kräver VPN), output → Blob.
**Värde:** webappen "ser ut" som ett sammanhängande flöde även när data prep med nödvändighet är lokal;
ärvbart. Sömmen lokalt/moln förklaras, göms inte.
**Beror på:** FD.26 (texten ska peka på ett skript som FAKTISKT finns). Lindas ihop med FD.26.
**Estimerad omfattning:** Låg. **Status:** Designad denna session, ej byggd.
**Not:** dashboard.html är ren UTF-8 — skriv å/ä/ö direkt.
**Datum identifierad:** 2026-06-15.

### FD.28 — Container-per-familj som speglar BCG:s mappstruktur (finåkning)
**Idé:** I stället för platta input/output/runstatus — egna containrar (eller prefix) per fas-familj
som speglar BCG:s numrerade struktur, så bränsle/output lättare skiljs "vad från var".
**Värde:** igenkänning/förtroende (jfr FD.21 för frontend); renare separation.
**Beror på:** att MOTORN funkar först (Jens: "göra klart att motorn funkar innan vi tvättar bilen för
att finåka"). Hör ihop med FD.20, FD.21, LB.63 + LB.67.
**Estimerad omfattning:** Medel. **Status:** Önskad 2026-06-15, medvetet uppskjuten till finåkning.
**VIKTIGT:** gör tillsammans med LB.63/LB.67-eskaleringen — container-struktur + entitet-i-nyckel +
auth-läge är samma designprincip, lös en gång.
**Datum identifierad:** 2026-06-15.

### FD.29 — AAD-övergång för upload_inputs när Blob-datarollen finns (Kent)
**Idé:** upload_inputs ärver kontonyckel-läget (PRICINGMODEL_AUTH=key) — Jens-access-beroende. När
MI:n får Storage Blob Data-rollen (FAS T, Kent), byt till AAD: en envariabel-ändring, ingen omskrivning
(blob.py är redan förberedd).
**Värde:** uppladdning överlever att Jens Owner-access försvinner — fullbordar "överlever att du slutar".
**Beror på:** Kent (ABAC-blockerad dataroll). **Estimerad omfattning:** Låg. **Status:** Väntar FAS T.
**Datum identifierad:** 2026-06-15.

### FD.30 — Avslutade körningar ska sätta sluttillstånd
**Idé:** En körning som avslutats (lyckad/dealloc) måste sätta state till ett sluttillstånd
(succeeded/deallocated), annars fastnar statusfilen på running och stale-heartbeat-varningen fyrar
på en gammal, klar körning. Sågs 2026-06-15: förmiddagens VM-körning visade "318 min sedan" + tunnel-
varning trots att jobbet var klart. Dagens run_data.py-körning lämnar också state=running (extraktion
klar men helheten inte) — korrekt nu, men ingen sätter succeeded när alla sex faser en dag är klara.
**Värde:** Varningen (rätt för aktiva VM-körningar, LB.55) slutar ge falsklarm på historik.
**Beror på:** lager 2-statusskrivning. Hör ihop med LB.59 (run_id-datum-kollage).
**Estimerad omfattning:** Låg. **Status:** Idé. **Datum identifierad:** 2026-06-15.

### FD.31 — Cluster/Site/Step5/Step6/R12-runners får lager 2-statusrapportering
**Idé:** Idag rapporterar bara run_data.py (extraction) och run_site_model.py sin fas till
statuskontraktet. För att en körning ska visa alla sex faser gröna när de faktiskt körts måste varje
runner skriva sin fas (start_phase/finish_phase + write_status, best-effort) — samma mönster som
run_data.py fick 2026-06-15. Då rapporterar varje steg sig självt och dashboarden blir sann av sig
själv, utan handpåläggning (handmålning av statusfiler avvisades 2026-06-15 — dashboarden får inte
ljuga, LB.25-anda).
**Värde:** Framtida körningar lyser helt gröna ärligt; dashboarden speglar verklig körning.
**Beror på:** lager 2-mönstret (klart, run_data.py som förlaga). **Estimerad omfattning:** Låg-medel
per runner. Hör ihop med FD.30. **Status:** Specad. **Datum identifierad:** 2026-06-15.

### FD.32 — Webapp facit→nu: rimlighet & liv, inte modellöverlägsenhet (KPI-lärdom)
**Slutsats (2026-06-16, efter felsökning):** appens facit→nu-KPI:er ska INTE visa
"vi slog BCG" eller jaga signifikansgrad (LF.5: projektet optimerar medvetet INTE mot
signifikans). Syftet är förtroende genom att modellen LEVER och bolaget VÄXER:
facit-KPI bredvid nu-KPI tvärs hela modellen visar att talen rör sig (modellen aktiv),
riktningen (+/-) indikerar om bolaget står starkare än vid BCG:s senaste besök, och
en RIMLIG tillväxt (+25,5% rader, +27,2% omsättning) = friskt. En ORIMLIG rörelse
(sjunkande omsättning) vore självavslöjande fel — facit→nu blir därmed ETT inbyggt
rimlighetstest. Djupare bedömning (är förändringen affärsmässigt RÄTT?) ligger UTANFÖR
verktyget — mänsklig analys, ej något appen påstår. Verktyget bevisar rimlighet, ej korrekthet.
**Vad ändrades:** extraction-KPI = dataprep-tillväxt (mätt: kvitto+playbook). Cluster/Site-KPI
= rimlighet mot facit (median, negativ andel, KEY) — signifikans BORTTAGEN. Site-replikering
(6624→6624, korr 1.0) flyttad till bit-för-bit-lagret (var felmärkt som facit→nu). Story-texter
gjorda talfria (förvaltningsfritt: talen bor i korten, texten förklarar bara linsen).
**Talförväxlings-regel (process):** signifikanstalen 33,4/40,4/45,2/18 förväxlades 3-4 ggr för
att de kom ur OLIKA jämförelser (vår rå / BCG-facit / vår post-blend / IB.9-referens). Ett KPI
märkt "facit→nu" MÅSTE vara samma modell, fruset fönster → växande fönster — INTE vår-vs-BCG
(det är replikering/bit-för-bit, hör till proof_chain). Håll de två åtskilda. Mät ur kvitto med
RÄTT population, aldrig ur sessionsminne. **Status:** Åtgärdad i story_config/FUNNEL 2026-06-16.

### FD.33 — Migrera Blob till BCG-speglande pipeline-struktur (önskat, A räcker nu)
**Beslut (2026-06-16):** Jens vill EGENTLIGEN ha en `pipeline`-container med prefix som
speglar BCG:s mappstruktur (02_cluster/, 03_site/, 04_bundle/, 05_step6/ med
input/output/validation per familj) -- för dokumentations-igenkänning. MEN den
befintliga strukturen (containrarna `input`/`output`/`runstatus`) som runners redan
skriver till RÄCKER för syftet (Azure som körmotor, syfte B). Därför: behåll A nu,
gör B vid finåkning.

**Nuläge (mätt 2026-06-16):** motor-output-arkitekturen FINNS redan och fungerar:
  - `run_data.py` -> `upload_inputs` -> container `input` (platt, aktuell bränsle, skrivs över)
  - `run_cluster_model.py` / `run_site_model.py` -> `upload_outputs(date_folder, ...)` -> container `output` under <YYYY-MM-DD>/
  - VM läser input från lokal VM-disk (~/bcg/cluster/data/), inte Blob direkt
  - Status -> container `runstatus`
  - blob.py har inbyggt upload_inputs/upload_outputs/write_status (key-läge, test-konto via env-vars)

**Vad B kräver (när finåkning):** peka om runners upload_outputs att skriva till
02_cluster/output/ etc. i `pipeline`-containern i stället för output/<datum>/.
Mer jobb (rör alla runners), bättre dokumentation. EJ värt mitt i annat arbete.

**Princip bekräftad:** växande körning SKRIVER ÖVER gammalt (overwrite) -- ingen
historik-versionering i Blob behövs. Bara en bråkdel av allt som genereras används
av nästa steg; exporterna är slutsummeringen. Fryst facit behöver bara
valideringsfilerna + output_summary som jämförelse-nollpunkt (redan uppladdat,
upload_frozen_facit.py, container `pipeline` 00_frozen_facit/).

**Loose end:** `pipeline`-containern skapades denna session (steg 1, fryst facit).
Den samexisterar nu med input/output/runstatus. Vid B konsolideras allt i `pipeline`;
tills dess lever facit i `pipeline/00_frozen_facit/` och motor-output i `output/`.
Städa upp dubbel-strukturen vid B (eller medvetet låt facit ligga separat).

### 2c. Lägg till i "Senaste uppdateringar"-tabellen
| 2026-06-15 | FD.26-29 tillagda. Arkitekturbeslut: data prep lokalt (LB.65/66), output→Blob. upload_inputs byggd+bevisad (1 GB, 2 min). FD.26 run_data.py = nästa mål. |


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

### FD.34 — Bundle aktiverad som fullvärdig familj (skuld stängd)
**Beslut (2026-06-16):** Bundle gick från PARKERAD (FD.11) till aktiv familj på Jens
beslut — förtroende: ingen parkerad skuld i en modell man ska försvara. Bundle-MODELLEN
är nu körklar och observerbar som de andra två. Levererat denna session:
- `run_bundle_model.py` (orchestration/runners) — copy-adapt från cluster-runnern, ärver
  bygg 1 (auto-validering mot fryst facit) + bygg 2 (alla VM-output-filer till Blob).
  EXPECTED_KEYS=125, family=bundle, `~/bcg/bundle`. REMOTE_INPUT ANTAGET — mät på VM vid
  första körning (preflight fångar fel sökväg).
- bundle i story_config STORY + FUNNEL (mätta tal ur facit vs azure_run_model: median
  -0,244→-0,211, neg andel 87,2%→85,6%, 125 KEY). Ärlig 2,2%-kontext i berättartexten.
- `bundle_model` som fas i `default_pipeline` (run_status.py), mellan site_model och
  site_step5 — PERMANENT (framtida körningar får den). De tre befintliga statusfilerna
  i Blob handpatchades så bundle syns i appen för gamla körningar (LB.71).
- bundle i PHASE_RECEIPT (app.py) — förberedande; kvitton genereras först vid körning.

**Kvarstår (löses vid end-to-end-körningen):** bundle har ALDRIG körts med bygg 1
auto-validering, så bundle-valideringskvitton finns inte än (drill 3 tom tills körning).
Osäkert om rationality-sviten klarar bundle:s kolumnschema (basket_revenue/Bundle_visits
vs cluster/site 8-kol, LB.28) — verifieras vid körning.

**FD.11-relation:** bundle-MODELLEN är nu körklar. Väv-vikterna (FD.14) och steg-5-
routning (FD.15) är fortfarande frusna 2025 — separata proveniens-skulder, ej bundle-modellen.
Bundle driver fortf. bara ~2,2% av väven; aktiveringen handlar om komplett täckning, ej
om att bundle plötsligt blev affärskritisk.

### FD.35 — Konto-spretighet: ett hem för status + output + facit (före end-to-end)
**Upptäckt (2026-06-16):** statusfiler (container `runstatus`) bor i PROD-kontot
`evipricingmodelstprod` (blob.py default), men fryst facit lades i TEST-kontot
`evbcgpricinginput` (container `pipeline`, FD.33/upload_frozen_facit.py). Appen läser
status från prod; facit ligger i test. Detta är FD.33-spretigheten konkret.

**Risk:** bygg 2 (alla filer till Blob) laddar upp via `upload_outputs` till container
`output` — i VILKET konto avgörs av env-vars vid körning. Om runners skriver output till
ett konto och appen läser status/facit från ett annat blir det förvirrat var sanningen
finns när bygg 2 ska återanvändas av nästa familj (syfte B läs-sida).

**MÅSTE redas ut FÖRE end-to-end-körningen:** välj ETT hemkonto för status + output +
facit. FD.28-designen pekar på test-kontot (`evbcgpricinginput`, där VM:en bor) som hem.
Då: peka blob.py default dit (PRICINGMODEL_STORAGE + PRICINGMODEL_RG), flytta facit dit
(redan där), flytta/regenerera status dit. EN beslutspunkt, verifiera före tunga körningar.

**Gäller om:** end-to-end-körning där output laddas upp och nästa familj ska läsa den.

## Senaste uppdateringar

| Datum | Vad |
|---|---|
| 2026-06-08 | Fil skapad. Initiala FD.1-10 dokumenterade efter VM-körningens slut. |
| 2026-06-11 | FD.11-13 tillagda. FD.11 Bundle-modellen PARKERAD (dataprep-källa klar + committad `1daf093`, varukorgsbygge/modell kvarstår) — beslut datadrivet: 98 modellerade varukorgar = 526 M (~4,3%), överlappar Cluster/Site, sann väv-effekt avgörs av rimlighetsgrind (återbesöks-trigger: sjukhustjänsters signifikans). FD.12 Bundle Ray-config. FD.13 sandbox-Excel för metodik-förståelse mot beslutsfattare. |
| 2026-06-11 | FD.14-15 tillagda efter `verify_provenance`-suiten byggdes. Provenance-validering av Step 6-inputs avslöjade tre frusna lås: väv-vikter (FD.14, frusen Complete_Product_Data 2025), steg-5-blend/routning (FD.15, _Ivce-facit 2025-12, aldrig regenererad växande), och bundle-grenen (FD.11). Step 6 vilar på växande Cluster+Site-elasticiteter men frusen viktning/routning/bundle. Suiten ligger i `verify_tool/provenance/`. |
| 2026-06-16 | FD.32 tillagd (facit→nu = rimlighet+liv, ej modellöverlägsenhet; signifikans-KPI borttaget; site-replikering flyttad till bit-för-bit; story-texter talfria). FD.33 tillagd (migrera Blob till BCG-speglande pipeline-struktur — önskat, A räcker nu; motor-output-arkitektur input/output/runstatus redan på plats). Fryst facit uppladdat till Blob `pipeline/00_frozen_facit/` (upload_frozen_facit.py, key-läge, test-konto). |
| 2026-06-16 | FD.34 tillagd (bundle aktiverad som fullvärdig familj — runner, app-story+FUNNEL, fas i pipeline, PHASE_RECEIPT; copy-adapt från cluster, ärver bygg 1+2). FD.35 tillagd (konto-spretighet: status i prod, facit i test — MÅSTE redas ut till ett hem före end-to-end). Cluster/site/bundle-runners utrustade med auto-validering mot fryst facit (bygg 1) + alla VM-output-filer till Blob med familje-prefix (bygg 2). |
| 2026-07-02 | FD-minipass: FD.38 Robusthetspass delad infra tillagd (uppflyttning BB.9 tar-fetch MOGEN + BB.10 selftest + P.9 io_safe-wiring; SPÄRR till efter cluster-maj-grön). FD.39 Sökvägs-centralisering tillagd (deps-mätning 2026-07-02: 336+66 absoluta sökvägar, levande delmängd mäts om efter brus-städ). FD.22-indexraden rättad (live-tick BYGGD FAS 18 — raden var stale). BB.9 i BACKLOG → FLYTTAD. MANIFEST väv-sökväg → Master-Bibliotek. |

## FD.37 — Efter-kedjans orkestrator (`run_after.py`)

**Status:** Specificerad 2026-06-22, ej byggd. Nästa stora bygge efter att motorn (run_id/finalize/
sonder) validerats.

**Vad:** En lokal orkestrator som kör "Efter — resultat och affärssignal": de steg som måste köras
UTANFÖR Azure (xlwings/COM finns ej på Linux, LB.44), och laddar upp utfallet till Blob så allt sparas
på samma ställe som motorns output. Speglar `run_data.py` (Före-fasen) i anda.

**Ordning (härledd ur sond 6 `after_chain_probe.py` — noll gissning):**
1. **PULL** — ladda ner motorns LIVE-output från Blob (fönster-run_id) → placera på run_step6:s
   LIVE-destinationer: cluster steg 1-4 (growing) + site (growing). De FRUSNA placeringarna
   (FD.11 bundle, FD.14 väv-vikter, FD.15 cluster-steg-5) rör PULL INTE.
2. **STEP 6** — subprocess `verify_tool/run/run_step6.py` (preflightar, placerar, väver F1-F7,
   verifierar R7, tolererar LB.53-mallfelet). → `Final_Fallback_Data_<stamp>.xlsx`.
3. **STEP 7** — subprocess `verify_tool/run/build_r12_for_model.py --tx <growing-csv>`
   (auto-hittar senaste Final_Fallback_Data). → `Model_Feed_<stamp>.xlsx`.
4. **PUSH** — ladda upp Final_Fallback_Data + Model_Feed till Blob (samma fönster-run_id);
   uppdatera statusfilen: `step6` + `build_r12` → gröna, kör `finalize()` → fönstret blir
   "alla sju gröna" → run = SUCCEEDED.

**Beroende att bygga FÖRST:** `blob.py` saknar `download_outputs(run_id)` — PULL-helpern måste byggas
(sond 6 fångade detta). Allt annat orkestrerar BEFINTLIGA, beprövade runners.

**Viktigt (rapportera, dölj ej):** utfallet bär de tre frusna låsen (FD.11/14/15). Provenance-kvittot
märker det REVIEW med flit. `run_after.py` ska RAPPORTERA detta i sin status/logg, inte dölja det —
annars tror någon att hela väven är färsk. (Spegel av LB.77: avsiktlig avvikelse märks på platsen.)

**Vad som INTE ligger i kedjan:** Step 5 (`data_prep_after_model_output.py`) är femte scriptet i varje
familjs egen launcher, INTE ett led i Efter-kedjan — run_step6 placerar omdöpt growing-output + frysta
lager och behöver ingen lokal step 5. `fallback_blend.py` är validering (bevis-spåret), ej produktion.
(Sond 6 klassificerade båda korrekt — bevarar mot att de vävs in av misstag.)

---

## FD.38 — Robusthetspass: delad infrastruktur (tar-fetch, selftest, io_safe-wiring)

**Status:** Specificerad 2026-07-02 — uppflyttning av BACKLOG BB.9 (MOGEN, §5b) + BB.10 +
P.9-resten. **SPÄRR:** byggs EFTER att cluster-maj-relaunchen är grön — en variabel i taget;
relaunchen ska bevisa config-fixen, inte config + ny hämtningsväg samtidigt.

**Vad (tre delar, ETT pass — horisontella metoden BB.13 i praktiken, delad väg träffar alla tre):**
1. **tar-fetch (BB.9, BEVISAD FAS 21):** runnernas `fetch_all_outputs` scp:ar per fil
   (4181 överföringar); tar-varianten hämtade 190 MB på 10 s där per-fil malde 11+ min och
   föll på svenska filnamn (dubbel-UTF-8). Mätt 2026-07-02: bristen identisk i alla tre
   runners (`run_cluster_model.py:385`-mönstret, 3 anropsplatser per runner). Fix: `tar czf`
   på VM + EN `scp_from_vm` — i delad väg + tre runners samtidigt.
2. **selftest realistisk sekvens (BB.10):** `ssh_launch_selftest` kör `sleep 90` i vakuum
   (`azure_vm.py:241–257`) och gav PASS trots att skarp launch dog efter en serie täta
   SSH-anrop. Skärp till preflight-liknande serie + launch så tunnel-blink-klassen fångas
   FÖRE en 50-min-körning. (A2-fixen täcker redan skarpa vägen; TESTEN släpar.)
3. **io_safe-wiring (P.9-resten):** `io_safe.py` + idempotens-audit är byggda och committade
   (`cdd02d3`, triage 164 → ~3–4 relevanta skrivningar) — koppla `io_safe` i de utpekade
   skrivpunkterna så de långa stegen får atomära skrivningar på riktigt.

**Gäller om:** nästa gång en runner rörs, eller som eget dedikerat pass direkt efter maj-grönt.

## FD.39 — Sökvägs-centralisering (env/config-lager för C:\Projekt-beroenden)

**Status:** Fångad 2026-07-02 ur deps-mätningen (`map_cross_project_deps.ps1`, BA-städningen).

**Uppmätt:** 336 absoluta sökvägar i 162 BCG-filer + 66 i 32 BA-filer. Mycket sitter i
`_ATT_RADERA/`, `archives/`, `workspace/` och genererade loggar — den LEVANDE skulden är
mindre och mäts om EFTER brus-städningen (BA-checklistan §4/§5).

**Vad:** centralisera levande `C:\Projekt\...`-beroenden till env-vars/en gemensam
config-modul, i survival-/klon-målets tjänst: en frisk klon på annan maskin ska köra utan
sök-ersätt av sökvägar. Prioritera kod-beroenden (runners, verify_tool, orchestration) —
docs/loggar är dokumentation, inte kontrakt.

**Gate:** eget pass, kandidat efter FAS A grön. Togs INTE på köpet i filflytt-städningen
(VAKTEN trigger 1 — frestelsen fanns, avvärjdes i BA-checklistan §4).
