# DRIFT — Köra & förvalta BCG-prismodellen

**Projekt:** `evbcgpricing` — replikering, validering och löpande drift av BCG:s
priselasticitetsflöde på Evidensias egen växande data.
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Det här dokumentets roll:** den *operativa* körhandboken — hur modellen körs end-to-end
på färsk data, hur resultatet valideras, och hur det matas in i BCG:s prismodell-Excel.
För *varför* modellen är byggd som den är, se `README.md` (arkitektur),
`docs/governance/` (beslut, låsta antaganden, roadmap) och
`REPLIKERING_OCH_VALIDERING.md` (det fullständiga bevisarbetet).

---

## 0. Snabböversikt — produktionskörningen, start till slut

```
1.  Uppdatera källdata    →  Pipeline\01–02 dataprep (DuckDB/Alteryx)
2.  Kör elasticiteter      →  Cluster + Site-modeller (växande fönster)
3.  Väv ihop nivåerna       →  verify_tool\run\run_step6.py        (F1–F7 fallback)
4.  Validera utfallet       →  verify_tool\run_all_*  +  provenance / freshness
5.  Bygg modellmatningen    →  verify_tool\run\build_r12_for_model.py
6.  Klistra in i modellen   →  Model_Feed_<datum>.xlsx → BCG-Excelens blå flikar
7.  Lägg ett prisantagande  →  Excelen beräknar omsättningseffekten
```

Allt från steg 3 och framåt körs lokalt med `py -3.11` (globala Python 3.11, som har
duckdb / pandas / openpyxl / xlwings). Azure-VM:en behövs bara för de tunga modellstegen
1–4; steg 6 och all validering körs på arbetsstationen.

---

## 1. Miljö

- **Python:** använd `py -3.11`. Globala 3.11 har de paket som krävs (duckdb, pandas,
  openpyxl, xlwings). 3.13 kan sakna pandas — använd den inte för dessa skript.
- **IT-policy:** installera paket med `python -m pip` (inte bara `pip`); `.ps1`-skript
  kräver `Unblock-File`; PyInstaller-EXE är blockerade; Hyper-V är begränsat av
  grupppolicy. Citera alltid PowerShell-sökvägar som innehåller mellanslag.
- **PowerShell-fälla:** bädda inte in långa `python -c "..."`-oneliners med nästlade
  citattecken — de bryts (LB.21). Skriv en `.py`-fil (eller en here-string till
  `$env:TEMP\x.py`) och kör den istället.
- **Azure-VM** (`bcg-poc-vm`, subscription `ev-lz3-ai`, RG `ev-openai-swce-rg-test`,
  `ssh azureuser@172.18.148.4`): bara för modellsteg 1–4. Se `docs/ops/MASTER_AZURE.md`
  och `docs/ops/UBUNTU_AZURE_VM.md`.

---

## 2. R12-fönstret för växande data (viktigt)

BCG:s ursprungsmodell kördes på ett fast fönster t.o.m. **2025-06**. Den växande pipelinen
kör **samma 12-månaderslängd (R12)** men med slutdatumet framflyttat till senaste
**kompletta** månad i datan. Elasticiteten och volymerna måste dela det fönstret — de
kommer från samma extrakt, så det gör de per konstruktion.

`build_r12_for_model.py` väljer fönstret automatiskt (senaste kompletta månad) om du inte
anger `--end YYYY-MM`. Ankaret för det växande elasticitetsfönstret är fast vid
**2022-07-01** (se `docs/governance/LOCKED_ASSUMPTIONS.md`, LF.2).

---

## 3. Steg för steg

### 3.1 Kör Step 6 — fallback-väven (F1–F7)

`verify_tool\run\run_step6.py` placerar de tre inputs Step 6 förväntar, kör BCG:s
`Fall_Back_Logic.py`, och verifierar utdata.

```powershell
cd "C:\Projekt\BCG"
py -3.11 verify_tool\run\run_step6.py
```

Vad den gör:
- Placerar **växande** Cluster-modelloutput (splittar `KEY → Cluster + ItemCode`, se
  LB.52) och **växande** Site-modell där `Constant.py` förväntar dem.
- Placerar de **frusna** inputs: Cluster steg-5-blend, väv-vikter och bundle-facit (de tre
  låsen — se LF.9).
- Kör väven; tolererar den kosmetiska xlwings named-range-COM-felet på mall-skrivningen
  (LB.53) — datafilen skrivs *före* det steget, så körningen behandlas som lyckad och
  F-nivå-fördelningen rapporteras.

Utdata: `Pipeline\02. Elasticity\6. Fall Back Logic\output_data\Final_Fallback_Data_<ts>.xlsx`
— ~109k rader, ~15k produkter, en `final_elasticity` per ProductKey, plus `RSQ`,
`PVALUE_PRICE`, `elasticity_level` (vilken F-nivå som gav värdet).

### 3.2 Validera

Kör valideringssviterna (var och en skriver ett Excel-kvitto under `verify_tool\receipts\`):

```powershell
cd "C:\Projekt\BCG\verify_tool"
py -3.11 extraction_validation\run_all_validations.py     # DW-extrakt vs facit
py -3.11 output_rationality\run_all_rationality.py        # färsk output rimlighet
py -3.11 provenance\run_all_provenance.py                 # färskt vs fruset + freshness
```

Läs via kvittot, inte konsolen (R7 / lita på filen). Ett `PASS` betyder att kontrollen
höll; ett `REVIEW` på provenance är **avsiktligt** — det flaggar de tre frusna inputs, det
är inte ett fel.

Det sviterna bekräftar:
- Replikeringen är bit-för-bit mot BCG på det gamla fönstret (korrelation 1.000000).
- Färsk output är 100 % negativ, 100 % inom det rationella `(-10, 0)`-bandet.
- Drift mot 2025-baslinjen är ~95 % under 0.5 (stabilt; inom snapshot-driftbandet).
- Bundle vinner bara ~2,2 % av besluten (IB.12).

### 3.3 Bygg modellmatningen

`verify_tool\run\build_r12_for_model.py` aggregerar R12 volym + omsättning per
ItemCode×Site och joinar den färska elasticiteten från Step 6, och skriver en arbetsbok med
tre flikar namngivna exakt som modellens blå indataflikar.

```powershell
cd "C:\Projekt\BCG"
py -3.11 verify_tool\run\build_r12_for_model.py `
  --tx "Pipeline\02. Elasticity\Sweden_Elasticity_Data_Prep_SQL\output\Sweden_weekly_model_data_site_level.csv"
```

Flaggor: `--end 2026-04` (tvinga fönsterslut), `--tx <sökväg>` (transaktions-CSV),
`--fallback <sökväg>` (specifik Step 6-output; default = senaste).

Utdata: `output_model_feed\Model_Feed_<datum>.xlsx` (mappen är **gitignorerad** — matningen
är känslig). Tre flikar:
- **FACT_CodeClinic** — `FACT_CodeClinicKey, ItemCode, SiteCode, Cluster, Quant_25,
  Sales_25, Elasticity, _R2, _pValue`. ~99,5 % av raderna bär en matchad elasticitet.
- **DIM_Code** — per ItemCode: R12 omsättning/volym, prefix, fakturagrupp.
- **DIM_Site** — per site: kluster, site-typ.

Kolumner med **gul rubrik** är avsiktligt tomma — de fylls från externa källor (pris från
Provet, konkurrens/HHI, FTE från Quinyx). Se `presentations\Model_Update_Guide.pdf` för
hela har/kvarstår-kartan.

### 3.4 Klistra in i BCG-Excelen och läs omsättningseffekten

Öppna `Model_Feed_<datum>.xlsx`. För varje flik: markera kolumnerna, kopiera, klistra in i
motsvarande blå flik i BCG:s prismodell (`...BCG_Pricing_Model_vFinal.xlsx`), matchat på
nyckeln. **Rör inte beräkningsflikarna** (Calculations, Pricing Model, dashboards) — de
räknar om automatiskt. Lägg ett prisantagande i modellens input så producerar Excelen
omsättningseffekten.

För en pedagogisk genomgång av hur ett prisantagande flödar till en omsättningseffekt, se
`presentations\Elasticitet_Beslutssnurra_BCG.xlsx` (en end-to-end-beräkningssnurra på en
artikel) och `presentations\Elasticitet_Sandbox_BCG.xlsx` (metoden, steg för steg).

---

## 4. Vad som är färskt vs fruset (operativ sanning)

| Del | Tillstånd | För att göra färsk |
|---|---|---|
| Cluster + Site-elasticiteter | **VÄXANDE** | redan färsk |
| R12 volym & omsättning | **VÄXANDE** | `build_r12_for_model.py` |
| Cluster steg-5-routning | FRUSEN (2025) | FD.15 — billigast; `fallback_blend.py` på växande input |
| Väv-vikter | FRUSEN (2025) | FD.14 — Alteryx Modul 4 / DuckDB-ombyggnad |
| Bundle-gren | FRUSEN (parkerad) | FD.11 — bara 2,2 % väv-vinst; villkorlig |

Kärnsignalen för priskänslighet — de tal som styr prissättningen — är färsk idag. De tre
frusna låsen påverkar en liten, dokumenterad andel av utfallet. Lyft dem i ordningen
FD.15 → FD.14 → FD.11 (kostnad vs påverkan). Se `docs/governance/LOCKED_ASSUMPTIONS.md` LF.9.

---

## 5. Köra om när perioderna växer

Hela kedjan är omkörbar. När en ny månad stänger:
1. Uppdatera källextraktet (den växande vecko-CSV:n).
2. Kör om Cluster + Site-modellerna (VM) → Step 6 (`run_step6.py`).
3. Validera om (`run_all_*`).
4. Bygg om matningen (`build_r12_for_model.py`) — R12-fönstret rullar fram automatiskt.
5. Kör om `analysis\analys_bcg_freshness.py` om du vill uppdatera "vad hände sedan BCG"-
   dekomponeringen och top-management-leveransen.

---

## 6. Var saker bor (efter städning)

```
verify_tool\run\        run_step6, build_r12_for_model, fallback_blend, run_bundle_dataprep
verify_tool\            proof_chain, extraction_validation, output_rationality, provenance
analysis\               analys_bcg_freshness, xlsx_export_bcg_freshness, compare_elasticity_runs
presentations\          elasticity_since_bcg.*, Model_Update_Guide.*, Elasticitet_*.xlsx
output_model_feed\      Model_Feed_<datum>.xlsx (gitignorerad — känslig)
output_analyspaket\     Analyspaket_BCG_Freshness_<datum>.xlsx
docs\governance\        PLAYBOOK, ROADMAP, LOCKED_ASSUMPTIONS, FUTURE_DEVELOPMENT
docs\knowledge\         LESSONS_BCG, INSIGHTS_BCG, F9_BUNDLE_INVENTORY
docs\ops\               TECHNICAL_PREREQUISITES, KRAVSPEC_IT, MASTER_AZURE, UBUNTU_AZURE_VM
Pipeline\               själva modellen (steg 1–6) — orörd
```

---

*Förvaltas av Jens Palmö. Den här handboken speglar läget efter att FAS F (drift på färsk
data) slutförts: Step 6 körs på växande data, utfallet är validerat, och modellen kan matas
och köras end-to-end för varje ny period.*
