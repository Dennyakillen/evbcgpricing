# NEXT_SESSION — Patcha export_b4b + kör om Cluster på VM

**Projekt:** evbcgpricing (BCG priselasticitet, växande data)
**Branch:** `fas-f-fresh-data`
**HEAD:** `ed1f88e` (NEXT_SESSION: critical 60% ItemCode dropout finding + diag scripts archived)
**Utvecklare:** Jens Palmö
**Beräknad tid:** 3-4 timmar

---

## SESSIONEN I EN MENING

Patcha `export_b4b_for_model.py` så `ProductGroupL4Name` lyfts från BCG:s 0828-CSV istället för
DW:s `Master_Underkategori3` — sedan kör om hela cluster-pipelinen på VM och få ut elasticiteter
för alla 1151 ItemCodes (inklusive 834 tjänster som idag droppas).

---

## ORSAKSSAMBANDET (visualiserat)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ORSAK: Manual.Dim_Item_Extended.Master_Underkategori3 är NULL för       │
│        tjänster eftersom kolumnen kommer från MasterListProducts-       │
│        joinen, som bara har butikssortiment. Tjänster (Klinisk/Lab)     │
│        får inte denna mappning.                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ EXTRAKTION: export_b4b_for_model.py rad 75:                             │
│             i.Master_Underkategori3 AS ProductGroupL4Name               │
│                                                                          │
│   → 834 av 1151 ItemCodes får NULL pg4 i input-CSV (73%)                │
│   → Tjänster: AAP, DUS, AEM, ALB, ALT, ANALYS, ASU, ARCCRE, ...         │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PIPELINE: data_prepration.py rad 345 yoy_seasonality():                 │
│           df.merge(df_seasonality, on=['service', 'WEEK'])              │
│           (default = inner merge)                                        │
│                                                                          │
│   → NaN matchar inte med NaN i pandas merge → rader droppas             │
│   → ItemCodes med 100% NULL pg4 → HELT borta från output                │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ KONSEKVENS: F.6-output 1521 KEY från 317 ItemCodes                      │
│             (BCG facit: 3812 KEY / 1276 ItemCodes)                      │
│                                                                          │
│   → 73% av ItemCodes saknas — alla veterinärtjänster                    │
│   → Compare-rapporten är vilseledande (jämför olika populationer)       │
│   → Affärsmässigt: modellen utesluter huvudintäktskällan                │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ LÖSNING: Lyft pg4 från BCG:s 0828-CSV (samma fil vi redan läser för    │
│          facit_pairs). 0828 har 100% komplett pg4-mappning för alla    │
│          1151 ItemCodes över 23 distinkta kategorier.                   │
│                                                                          │
│   Verifierat:                                                            │
│   - 1:1 mapping (0 mixed, 0 multi-value per ItemCode)                   │
│   - Inga NULL i 0828                                                     │
│   - 23 kategorier inkluderar tjänster (Consult, Imaging, Surgery, ...)  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## EXAKT PATCH (export_b4b_for_model.py)

### Ändring 1 — `load_facit_selection()` läser även pg4

Hitta funktionen (omkring rad 110-117). Ersätt med:

```python
def load_facit_selection():
    fac = pd.read_csv(FACIT_CSV, encoding="cp1252", encoding_errors="ignore",
                      usecols=["ItemCode", "Cluster", "ProductGroupL4Name"],
                      low_memory=False)
    fac["ItemCode"] = fac["ItemCode"].astype(str).str.strip().str.upper()
    fac["Cluster"] = fac["Cluster"].astype(str).str.strip()
    pairs = fac[["ItemCode", "Cluster"]].drop_duplicates()
    pg4_map = (fac.dropna(subset=["ProductGroupL4Name"])
                  .drop_duplicates("ItemCode")[["ItemCode", "ProductGroupL4Name"]]
                  .rename(columns={"ProductGroupL4Name": "ProductGroupL4Name_BCG"}))
    print(f"Facit selection: codes={pairs['ItemCode'].nunique()} KEY={len(pairs)}")
    print(f"Facit pg4 mapping: {len(pg4_map)} ItemCodes have BCG pg4")
    return pairs, pg4_map
```

### Ändring 2 — `main()` tar emot båda returvärden

Hitta raden (omkring rad 145):
```python
    facit_pairs = load_facit_selection()
```
Ersätt med:
```python
    facit_pairs, pg4_map = load_facit_selection()
```

### Ändring 3 — Override DW pg4 med BCG pg4 efter aggregering

Hitta `grouped["QuantitySold(SalesTotal>0)"] = grouped["SoldQuantity"]` (omkring rad 175).
Lägg till DIREKT EFTER:

```python
    # Override DW pg4 (Master_Underkategori3, NULL for services) with BCG's frozen pg4
    grouped = grouped.merge(pg4_map, on="ItemCode", how="left")
    grouped["ProductGroupL4Name"] = grouped["ProductGroupL4Name_BCG"].combine_first(
        grouped["ProductGroupL4Name"]
    )
    grouped = grouped.drop(columns=["ProductGroupL4Name_BCG"])
    n_filled = grouped["ProductGroupL4Name"].notna().sum()
    print(f"pg4 coverage after BCG fill: {n_filled}/{len(grouped)} = "
          f"{100*n_filled/len(grouped):.1f}%")
```

### Förväntat utfall efter patch

```
Facit selection: codes=1151 KEY=4949
Facit pg4 mapping: 1151 ItemCodes have BCG pg4
...
pg4 coverage after BCG fill: 484XXX/484XXX = 100.0%
```

---

## KÖRNINGSSEKVENS (linjär, 3-4h)

### Steg 1 — Patcha lokalt (5 min)

```powershell
cd C:\Projekt\Business_Analytics
& ".\.venv\Scripts\Activate.ps1"
# Öppna export_b4b_for_model.py och applicera Ändring 1, 2, 3 ovan
# (Eller låt Claude leverera färdig fil)
```

### Steg 2 — Pre-flight (5 min)

```powershell
cd C:\Projekt\BCG\_session_prep
.\check_env.ps1
# Förväntat: 16+ PASS, inga FAIL
```

### Steg 3 — Kör DW-extraktion lokalt (10 min)

```powershell
cd C:\Projekt\Business_Analytics
$env:BCG_END_DATE = "2026-04-27"
az login --scope https://database.windows.net/.default
python export_b4b_for_model.py
```

Förväntat: `Saved: C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\data\0828_Sweden_weekly_model_data_P_C.csv`
**Verifiera pg4 coverage rad: ~100%**

### Steg 4 — Verifiera den nya CSV:n (1 min)

```powershell
python C:\Projekt\BCG\workspace\check_pg4_dropout.py
```
Förväntat: `ItemCodes med 100% NULL pg4: 0`

### Steg 5 — Pre-flight inför VM (5 min)

```powershell
cd C:\Projekt\BCG\_session_prep
.\check_env.ps1 -StartVm
```

### Steg 6 — Ladda upp till VM (5 min)

(Använd samma scp-mönster som F.6 från sessions-historik)

### Steg 7 — Kör pipeline på VM (2-3h)

```bash
# På VM:
ssh azureuser@172.18.148.4
cd ~/bcg/cluster
source .venv/bin/activate
export BCG_END_DATE=2026-04-27

# Skapa output-mappar (CZ.5)
mkdir -p output/model/automl/results output/regular\ price

# Radera gamla control_file.xlsx (KRITISKT — annars 1521-stalen ärvs!)
rm -f code/control_files/control_file.xlsx

# Steg 1
python code/regular_price.py 2>&1 | tee ~/run_log_step1.txt

# Steg 2
python code/data_prepration.py 2>&1 | tee ~/run_log_step2.txt
# Förväntat: "Unique Key Beginning = ~4500-5000" (jämfört med 3027 idag)
# Förväntat: "Unique Key Data for model = ~4500-5000"

# Steg 3 (feature_selection — VM-tung, 60-90 min, kör i tmux)
tmux new-session -d -s fs 'python code/feature_selection.py 2>&1 | tee ~/run_log_step3.txt'

# När klar: Steg 4
python code/model.py 2>&1 | tee ~/run_log_step4.txt
```

### Steg 8 — Hämta hem (2 min)

```powershell
# Lokalt: scp tillbaka output_summary, model_summary, control_file, model_results
```

### Steg 9 — Deallokera VM (1 min)

```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```

### Steg 10 — Validera (10 min)

```powershell
cd C:\Projekt\BCG\verify_tool
py -3.11 run_all.py
# FR-1..4 ska fortfarande PASS (samma frusen-replikering, inga regressioner)

cd C:\Projekt\BCG
python fallback_blend.py --output-summary "..." --prod-file "..." --facit "..." --out "..."

python compare_elasticity_runs.py
# NU jämför vi äkta populations — ~4000+ KEY vs BCG:s 3812
```

### Steg 11 — Arkivera (2 min)

Skapa ny arkivmapp `_archive_growing_2026-04-27_v2` med samma struktur som dagens.

---

## DOKUMENTATION FÖR DENNA SESSION (gör vid sessionsslut)

### Nya LB-kandidater att lägga in i LESSONS_BCG.md

**LB.XX — "Biter inte på kärnelasticiteten" ≠ "harmless"**

*Symptom:* Vid FAS 3 och FAS 10 noterades Master_Underkategori3 som halv-NULL. IB.8 dokumenterade
"relevant för gruppering, inte för kärnelasticitet". Detta minimerade konsekvensen.

*Rotorsak:* Pipeline-stegen efter regression (yoy_seasonality inner merge) droppar hela KEY för
NULL-pg4-rader. "Påverkar inte regression" stämmer för kvarvarande KEY, men förutsätter att KEY:n
överlever till regressionen.

*Regel:* När en datakvalitetsbrist flaggas — fråga "vid vilket pipeline-steg används denna kolumn,
med vilken merge-typ?" innan slutsatsen "harmless". `pandas.merge(how="inner")` på NULL-värden =
total dropout.

**LB.XX — Validering på producerade rader fångar inte populations-bortfall**

*Symptom:* `verify_dataprep.py` rapporterade FR-1 PASS med corr=1.0 mot BCG:s 0828. Detta dolde
att 834 av 1151 ItemCodes droppades senare i pipelinen.

*Rotorsak:* Validering mäter "matchar de rader vi har" — inte "matchar vi alla rader vi *borde* ha".

*Regel:* Varje pipeline-steg ska logga **ItemCode-count** in vs ut. Avvikelse > 1% kräver
förklaring. Verify-suiten bör inkludera täckningsgrad-KPI: `vår_codes ∩ facit_codes / facit_codes`.

### Ny LF-kandidat till LOCKED_ASSUMPTIONS.md

**LF.8 — pg4 lyfts från BCG:s 0828-CSV, inte från DW**

*Förutsättning:* `ProductGroupL4Name` för pipelinen hämtas från BCG:s frusna 0828-CSV
(`bcg_inputs\0828_Sweden_weekly_model_data_P_C.csv`), inte från `Manual.Dim_Item_Extended.
Master_Underkategori3`.

*Varför låst:* `Master_Underkategori3` kommer från `Manual.MasterListProducts`-joinen som bara
har butikssortiment-mappning. Tjänster (Klinisk/Lab) får NULL där. Detta orsakar 73%-bortfall i
yoy_seasonality:s inner merge.

*Vad som händer om vi bryter:* 834 ItemCodes (alla veterinärtjänster) droppas från modellen.

*Vad krävs för revision:* Egen L4-mappning för Klinisk/Lab byggs i DW. Tills dess: BCG:s 0828
är källan.

*Datum låst:* 2026-06-05 (efter F.6-bortfallets diagnos)

---

## VALIDERINGSPUNKTER (rött ljus om någon faller)

| Punkt | Förväntat värde | Var |
|---|---|---|
| pg4-coverage efter export | 100% | Steg 3 log |
| ItemCodes i ny CSV med 100% NULL pg4 | 0 | Steg 4 check |
| Unique KEY in data_prepration | 4500-5000 | Steg 7 log |
| ItemCodes i output_summary | 1100-1150 | Steg 8 |
| AAP130 i output_summary | 7 rader | Excel-kontroll |
| FR-1..4 verify | PASS | Steg 10 |

Om någon punkt faller — stoppa, diagnostisera, rapportera. Kör inte vidare.

---

## VAD SOM FORTFARANDE SKJUTS UPP

- A+B-bygget (affärspresentation + rullande volym) — NU kan vi göra det med riktig data
- F.8/F.9 (Site, Bundle, multi-modell-väv)
- KÄRNPRINCIPER-patch
- TILL_RADERING\ permanent radering

---

*Skapad 2026-06-05 efter iterativ 10-stegs djupgrävning. Proppen lokaliserad till en kodrad
i export_b4b_for_model.py (rad 75). Patchen är 3 ändringar, ~10 rader. VM-körning är identisk
med F.6 men producerar ~4000+ KEY istället för 1521.*
