# evbcgpricing

Replikering, validering och drift av BCG:s prissättningsmodell för Evidensia Djursjukvård AB.

**Utvecklare:** Jens Palmö (Senior Business Analyst)
**Status:** Modell-delen (feature_selection + model) körd fullt på Azure-VM (128 GB, 3812 grupper)
och **validerad mot BCG:s frusna facit** — elasticiteten matchar bit-för-bit. Nästa front: input-stegen.

---

## Syfte

Ett externt konsultbolag (BCG X) byggde en priselasticitetsmodell vars input produceras av en
Python-pipeline ovanpå SQL-städad data. Excel-prismodellen behöver uppdaterad input, och målet
är att Evidensia ska kunna **drifta hela flödet själv**. Detta repo håller vårt arbete med att
först *replikera* konsulternas flöde verbatim, *validera* det mot deras frusna facit, och på sikt
*migrera* SQL-prepningen till egna DW-vyer.

Repot innehåller **våra** artefakter (playbook, dokumentation, verktygsscript) — inte BCG:s
datatunga pipeline, som lever i källan och i Azure.

---

## Arkitektur (dataflöde)

```
Rådata (transaktioner, dimensioner)
  + klustermappning (01. Clustering)
  + produktiv tid
        |
        v
  SQL data prep (DuckDB, ersätter Alteryx)  -->  weekly_model_data
        |
        v
  Modellsteg 2/3/5 (OLS per produktgrupp, Ray-parallell, feature-selection)
        |
        v
  Fall Back Logic (blend)  -->  final_elasticity
        |
        v
  BCG Pricing Model vFinal.xlsx (CALC_Elasticity, VTL)  <-- slutkonsument
```

Beräkningskärna: OLS-regression per produktgrupp (`statsmodels`), priskoefficienten = elasticitet.
Parallellisering via Ray. Glesa grupper hanteras via klustring + fallback. Allt config-styrt
(`config.yml`).

---

## Roadmap

| Fas | Innehåll | Status |
|---|---|---|
| 0 | Orientering, struktur-scan, källval, rotorsaksanalys | ✅ Klar |
| 1 | Replikera struktur + kopiera källor verbatim | ✅ Klar |
| 2 | Bygga miljö (venv + requirements) | ✅ Klar (lokalt + Azure-VM) |
| 3 | Ray-config + feature_selection (brute-force) | ✅ Klar (Azure, validerad mot facit) |
| 8 | Azure-motor: VM, miljö, modellkörning | ✅ Klar (två tunga steg körda fullt) |
| 4 (model) | OLS-regression per grupp | ✅ Klar (bit-för-bit-match mot facit) |
| 7 | Validera output mot facit (KPI, population, features) | ✅ Klar (model + feature_selection) |
| 4 (SQL prep) | SQL data prep (duckdb via Python, ej exe) | ⬜ Kvar (input-fas) |
| 5 | `data_prep_after_model` (xlwings/Excel) | ⬜ Windows-uppgift, ej VM |
| 6 | Fall Back Logic (fixa hårdkodade sökvägar) | ⬜ Kvar |
| 9 | Git-baslinje (detta repo) | ✅ Påbörjad |
| B | DW-vyer + Blob input-folder (drift) | ⬜ Senare |

### Vad som validerades 2026-05-21 (ärligt om scope)

- ✅ **Modell-delen** — feature_selection + model — körd fullt på Azure-VM (3812 grupper), på BCG:s
  mellanfil `data_for_model.csv` (väg B, D12).
- ✅ **Bit-för-bit mot facit:** model-elasticiteten identisk på alla 3812 (korr 1,0, max diff 0).
  feature_selection troget: 93,1% identiskt feature-val; avvikelser är gränsfallsfeatures utan
  resultatpåverkan (elasticitet/Adj R2 i praktiken identisk).
- ✅ **OOM avskriven:** 128 GB, Ray-spill till `/tmp/ray_spill`, `Swap 0B` genomgående. CZ.1 bekräftad.
- ⬜ **Input-stegen** (regular_price + data_prepration) ej körda — blockerade på `InScope Mapping.xlsx`
  (O3 bekräftad, saknas lokalt). Det är nästa fas.
- 📌 **Steg 5** (`data_prep_after_model`) är Windows/Excel (xlwings) — ej VM-körbart (D14).

**Detaljerad bash/Linux-handhavande och driftkort:** se `UBUNTU_AZURE_VM.md`.

---

## Innehåll i repot

| Fil | Roll |
|---|---|
| `README.md` | Denna — syfte, arkitektur, roadmap, daglig drift |
| `BCG_PRICING_PLAYBOOK.md` | Fullständigt nuläge: beslut, faser, risker, lärdomar |
| `NEXT_SESSION.md` | Kall-start för nästa arbetspass |
| `UBUNTU_AZURE_VM.md` | Linux/bash-handhavande, encoding-fällor, tmux, driftkort |
| `make_smoke_control.py` | Bygger rökstest-control-fil (N grupper `RUN=YES`, resten `NO`) |
| `compare_to_facit.py` | Validerar model `output_summary.xlsx` mot facit (KPI/population/kolumner) |
| `compare_features_to_facit.py` | Validerar feature_selection mot facit (feature-val/elasticitet/R2) |
| `Scan-BCGFolder.ps1` | Kartlägger källmappens struktur (mappar, ej 50k filer) |
| `Build-Structure.ps1` | Speglar V2_New:s mappstruktur till ren arbetsfolder |
| `Copy-Sources.ps1` | Kopierar kod/SQL/config/input verbatim till strukturen |

Versionsstyrs **inte** (se `.gitignore`): `Pipeline/` (BCG:s verbatim-kod + GB data), venv,
parquet/csv/xlsx, körutfall. Azure-resultatet hämtas lokalt till
`...\2. Product Cluster Level Models\output\azure_run_model\` (gitignorerat).

---

## Daglig drift — Azure-VM (driftkort)

VM:en (`bcg-poc-vm`, 128 GB RAM) kostar **~8–10 kr/timme igång, nära noll deallokerad**.
Disken består vid deallocate — omstart bygger inte om något. Mönster: starta → jobba →
**deallokera så fort den inte används aktivt** (CZ.2 — vanligaste dyra missen).

Alla kommandon nedan körs i **PowerShell på Windows** om inget annat anges.

### Starta en arbetsdag

```powershell
az login --scope https://management.core.windows.net//.default
```
```powershell
az account set --subscription "ev-lz3-ai (SE)"
```
Aktivera PIM-rollen Contributor på `ev-openai-swce-rg-test` (Portal → PIM) om utgången.

```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
```powershell
ssh azureuser@172.18.148.4
```

På VM:en (bash): aktivera venv innan arbete. tmux-sessioner överlever **inte** en
deallocate/start-cykel — starta en ny vid behov.

```
source ~/bcg/cluster/.venv/bin/activate
```

### Köra en lång körning frikopplad (tmux)

Starta en namngiven session, kör med tee:ad logg, koppla loss med `Ctrl+B` följt av `D`.
Körningen lever då på VM:en oberoende av din SSH/dator. Detaljer i `UBUNTU_AZURE_VM.md`.

```
tmux new -s bcgrun
```
Inne i sessionen:
```
source ~/bcg/cluster/.venv/bin/activate
cd ~/bcg/cluster/code
python model.py 2>&1 | tee ~/run_log_PC_full.txt
```

### Kolla status utifrån (utan att gå in i sessionen)

Körs från PowerShell — stör inte den rullande körningen:

```powershell
ssh azureuser@172.18.148.4 "pgrep -af model.py; grep -c 'Model running for' ~/run_log_PC_full.txt"
```
```powershell
ssh azureuser@172.18.148.4 "tail -3 ~/run_log_PC_full.txt"
```
```powershell
ssh azureuser@172.18.148.4 "free -h"
```

Tolkning: `pgrep` tom = processen slut (klar eller kraschad — kolla `tail`). `grep -c`-talet
växer = jobbar framåt. `tail` visar `Total Models built:` = klar. `free -h` med `available`
nära 0 och växande `Swap` = minnespress (reagera).

### Hämta hem resultat

```powershell
scp -r azureuser@172.18.148.4:~/bcg/cluster/output/model "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\output\azure_run_model"
```

### Avsluta (KRITISKT — annars tickar kostnaden)

```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```
```powershell
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[?starts_with(code, 'PowerState')].displayStatus" --output tsv
```
→ Ska visa `VM deallocated`. `deallocate` (inte `stop`) stoppar debiteringen.

> **Token-utgång (E.3/CZ.3):** din `az login`-token dör efter 4 h (Conditional Access,
> `AADSTS70043`). Logga in igen vid behov. Körningen på VM:en påverkas **inte** — den rör inte
> Azure-API:t. För riktig drift: Managed Identity, inte din CLI-token.

### Vid sessionsslut i repot

```powershell
git add <ändrade filer>
git commit -m "<imperativ engelsk fras>"
git push
```
Uppdatera `NEXT_SESSION.md` med ny startpunkt, och relevanta MASTER_*.md med nya lärdomar.

---

## Miljönoteringar (Evidensia IT)

- **Inga `.exe`** i lösningen (AppLocker) — allt via `python -m`; duckdb = `pip install duckdb` på Linux.
- **Inga publika IP:n** (tenant-policy) — Azure-VM nås via privat IP från kontorsnätet.
- Azure-detaljer, behörigheter och PIM: se `MASTER_AZURE.md` / `MASTER_AZURE_COMPUTE.md`.
- Linux/bash-handhavande för VM:en: se `UBUNTU_AZURE_VM.md`.
