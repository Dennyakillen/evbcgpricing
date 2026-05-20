# evbcgpricing

Replikering, validering och drift av BCG:s prissättningsmodell för Evidensia Djursjukvård AB.

**Utvecklare:** Jens Palmö (Senior Business Analyst)
**Status:** Infrastruktur byggd och verifierad — väntar på första validerade körningen (Azure-PoC).

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
| 2 | Bygga miljö (venv + requirements) | ✅ Klar (lokalt) |
| 3 | Ray-config + första modellkörning | ⚠️ Config klar; lokal körning OOM → flyttad till Azure |
| 8 | Azure-motor: VM byggd, nåbar via SSH | 🔄 **Pågår — VM klar, nästa: kör** |
| 4 | SQL data prep (duckdb via Python, ej exe) | ⬜ Kvar |
| 5 | Övriga modellsteg (Site, Bundle) | ⬜ Kvar |
| 6 | Fall Back Logic (fixa hårdkodade sökvägar) | ⬜ Kvar |
| 7 | Mata pricing-modellen + validera KPI mot facit | ⬜ Kvar |
| 9 | Git-baslinje (detta repo) | ✅ Påbörjad |
| B | DW-vyer + Blob input-folder (drift) | ⬜ Senare |

**Nästa konkreta steg:** få upp kod + data på Azure-VM:en, köra klusternivå-steget hela vägen,
och validera `output_summary.xlsx` mot BCG:s frusna facit. Detaljer i `NEXT_SESSION.md`.

---

## Innehåll i repot

| Fil | Roll |
|---|---|
| `README.md` | Denna — syfte, arkitektur, roadmap |
| `BCG_PRICING_PLAYBOOK.md` | Fullständigt nuläge: beslut, faser, risker, lärdomar |
| `NEXT_SESSION.md` | Kall-start för nästa arbetspass |
| `Scan-BCGFolder.ps1` | Kartlägger källmappens struktur (mappar, ej 50k filer) |
| `Build-Structure.ps1` | Speglar V2_New:s mappstruktur till ren arbetsfolder |
| `Copy-Sources.ps1` | Kopierar kod/SQL/config/input verbatim till strukturen |

Versionsstyrs **inte** (se `.gitignore`): `Pipeline/` (BCG:s verbatim-kod + GB data), venv,
parquet/csv/xlsx, körutfall.

---

## Daglig rutin

### Starta en arbetsdag

```powershell
az login --scope https://management.core.windows.net//.default
az account set --subscription "ev-lz3-ai (SE)"
```
Aktivera PIM-rollen Contributor på `ev-openai-swce-rg-test` (Portal → PIM) om utgången.

```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
ssh azureuser@172.18.148.4
```

### Avsluta en arbetsdag (KRITISKT — annars tickar kostnaden)

VM:en kostar ~8–10 kr/timme **igång**, nära noll stoppad. Stäng alltid av:

```powershell
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```

`deallocate` (inte bara `stop`) stoppar debiteringen; disken består så omstart bygger inte om.
Bekräfta även att lokala körningar är döda: `Get-Process python` ska vara tom.

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
- Azure-detaljer, behörigheter och PIM: se `MASTER_AZURE.md`.
