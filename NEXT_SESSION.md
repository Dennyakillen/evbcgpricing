# NEXT_SESSION — BCG Pricing (efter Spår B: DW-native dataprep validerad)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_SQL.md` (Python/Azure-lärdomar
ligger även där tills separata masters skapas), `UBUNTU_AZURE_VM.md`, `BCG_PRICING_PLAYBOOK.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå ny lärdom (Symptom → Rotorsak → Regel)
> och lägg i relevant master.

---

## Aktuellt projekt

- **Repo (replikering + golden reference):** https://github.com/Dennyakillen/evbcgpricing.git — `C:\Projekt\BCG`
- **Repo (DW-native arbete):** https://github.com/Dennyakillen/Business_Analytics.git — `C:\Projekt\Business_Analytics` (D-B5)
- **DW:** server `se-az-we-bi-sql-01.database.windows.net`, db `se-az-we-bi-dw-sqldb-01`. Anslutning via
  `data_access.py` (pyodbc + DefaultAzureCredential + .env). `az login --scope https://database.windows.net/.default` (token ~4h).
- **Azure-VM:** `bcg-poc-vm`, deallocated. Modellkörningen (nedan) är redan gjord där.

---

## VAR VI STÅR (korrekt bild)

**Modellen (folder 2, Cluster) är REDAN replikerad + validerad bit-för-bit på Azure** (regular_price →
data_prepration → feature_selection → model, 3812 grupper, korr 1,0, max diff 0). **Compute-risken är
stängd** — OOM löstes med `ray: memory:8, cpus:12` på minnesrik VM. Det kördes på den DuckDB-replikerade
preppen (= i praktiken BCG:s data).

**Spår B (denna sessions arbete): DW-native dataprep byggd och validerad.**
- `replicate_dataprep.py` — golden reference (DuckDB), bit-för-bit mot facit. Emitterar nu pre-Top80
  `code_level_baseline.csv` (13 223 koder, Σ SalesTotal 7,985 mdr, Σ SoldQuantity 8,61 M).
- `validate_dw_codelevel.py` (Business_Analytics) — bevisade DW-källan ekvivalent per kod
  (median-kvot 1,0000, korr 0,989). **G1/källfrågan STÄNGD.**
- `discover_l4_mapping.py` — visade att BCG:s L4 inte finns i DW (egen kategorisering).
- `b4b_dw_weekly_elasticity.sql` — DW-native veckovy, totalbevarande mot baslinjen (codes 19 344,
  gross 9,285 mdr, qty 10,17 M). Validerad på kod- och täckningsnivå.

**Bekräftade fakta (se MASTER_SQL L.38-43):** källa = `dbo.Fact_BillingInvoiceRows`; omsättning =
`SalesTotal` (brutto); `TotalNetXVat` = `SalesExVAT` (netto); `NoofUnits` ≠ `SoldQuantity` (separata);
elasticitet = **log-log** (koefficienten ÄR elasticiteten); modellens KEY = `Cluster × ItemCode`.

---

## DET ENDA SOM ÅTERSTÅR (kritisk väg → affärsmål)

Affärsmålet: köra den (validerade) modellen på VÅR DW-data och sedan på FÄRSK data, med diffar små nog
att inte flippa top-line-beslut. Inte att återskapa BCG på gammal data.

| # | Steg | Status | Not |
|---|---|---|---|
| 1 | **PoC-2: b4b (DW) → modellkontrakt → kör modellen** | 🔴 nästa | Byt DuckDB-prep mot DW-prep. Se kontrakt nedan |
| 2 | **Output-rimlighetsgrind** (negativ elasticitet, band, "flippar diffen ett beslut?") | 🔴 | Ersätter facit på färsk data. Bygg FÖRE färsk-körning |
| 3 | Steg 5 — `data_prep_after_model_output.py` (xlwings/Excel, Windows) | 🔴 | Körbar nu på validerad output. Liten |
| 4 | Steg 6 — Fall Back Logic (fixa hårdkodade sökvägar, R6) | 🔴 | Path-fix = ofarlig hygien nu; blend kräver site/bundle |
| 5 | Site (folder 3) + Bundle (folder 5) familjer | 🔴 | För Fall Back-blend |
| 6 | Färsk data: parametrisera datumfönster (G7) + FTE-pipeline (Quinyx) | 🔴 | START_DATE/END_DATE hårdkodat i constants.py |

**Rekommenderad ordning:** PoC-2 → output-rimlighet → (steg 5 Excel som delseger) → familjer → Fall Back
→ färsk data. Steg 5/6 är legitima men nedströms; affärsvärdet sitter i PoC-2 + färsk data.

---

## MODELLKONTRAKTET (vad b4b ska producera — för PoC-2)

`KEY = Cluster + '-' + ItemCode`, `dep_var = QuantitySold(SalesTotal>0)`, `PRICE = TotalNet/UNIT`, log-log.

Kolumner b4b måste leverera (resten härleds i pipelinen):
`ItemCode, ItemDescription, week_starting_monday, Cluster, SoldQuantity, NoofUnits, TotalNet (brutto),
QuantitySold(SalesTotal>0), No of Sites, TotalNetXVat (= SalesExVAT), Sum_FTE_Interpolated, service(=ProductGroupL4Name)`.

b4b idag (byt namn): `Cluster_Internal→Cluster`, `TotalGross→TotalNet`, `No_of_Sites→"No of Sites"`;
lägg till `QuantitySold(SalesTotal>0)` (= SoldQuantity efter SalesTotal>0-filtret), `TotalNetXVat` (=Σ SalesExVAT).

Tre PoC-beslut:
1. **Sum_FTE_Interpolated** ligger i `cols_needed` (obligatorisk) men är Quinyx-uppström, ej byggd. För PoC:
   ta bort den ur `cols_needed` i config (en rad) ELLER platshåll. `Productive_time_per_site` är i col_type
   men används INTE som feature → behöver ej byggas.
2. **service / ProductGroupL4Name**: behövs bara för YOY-säsong (valbar cols_to_try) + output. Påverkar ej
   kärnelasticiteten. PoC: BCG:s loc.Dim_Item-mappning, eller droppa YOY_SEASONALITY ur cols_to_try.
3. **Cluster**: den verkliga grupperingsdrivaren (KEY). PoC = BCG-seed (facit-jämförbar); skalning = Priskluster (D-B2, dubbelspår).

Modellens delmängds-spak för rökstest: `control_file.xlsx`, sätt `RUN="YES"` på några KEYs.

---

## ÖPPNA BESLUT / TECH DEBT

- **D-B6:** PoC på `dbo.Dim_Item`; `Manual.Dim_Item_Extended` (finare) = dokumenterat skalningssteg.
- **D-B2:** Dubbla kluster — bär både `Priskluster` (DW) och BCG-seed. Behöver seed-CSV inbäddad i b4b.
- **G7:** Datumfönster hårdkodat (`constants.py`: START_DATE 2022-07-01, END_DATE 2025-06-29). Parametrisera före färsk data.
- **SPECIAL_WEEKS** (PR/media): hårdkodade datum i constants.py — INTE extern data. Parametrisera.
- **Extern prisdata / competitor:** konfigurerad men `data_prepration.py` läser den ALDRIG — död config.
- **Helger:** Python `holidays.Sweden()` — ingen källa att replikera.

---

## STANDARDER SÄRSKILT RELEVANTA NU

- **Mät, gissa inte** — gäller mappningar OCH Claudes egna antaganden (fel om net/brutto + NoofUnits denna gång).
- **Läs receptet** — M-koden gav källan; modell-Pythonen gav kontraktet. Gissa aldrig när källan finns.
- **Tee + Select-String/grep** strukturella rader (RUN/KPI/MAP/VOL/GATE/Saved/ERROR) — aldrig rådata.
- **DW-script körs i Business_Analytics-venv** (ej WindowsApps-Python). Token dör efter 4h.
- **Ett steg i taget, verifiera mellan steg.**

*Uppdaterad 2026-05-22 vid avslut av Spår B (DW-native dataprep validerad, modellkontrakt kartlagt).*
