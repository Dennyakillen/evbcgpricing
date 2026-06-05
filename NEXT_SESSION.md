# NEXT_SESSION — Fas F, Etapp F.7: Cluster-fallback på växande fönster

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst
på Evidensia Djursjukvård AB. Följ KÄRNPRINCIPER.md samt relevanta MASTER_*.md.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) att lägga i relevant MASTER_*.md. Innan ett LB.X
> föreslås — kontrollera om det är en instans av befintlig kärnprincip. Om ja:
> följ principen, lägg inte till en ny lärdom.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing
- **Lokal sökväg:** `C:\Projekt\BCG`
- **Senaste commit på origin/fas-f-fresh-data:** *(uppdateras vid commit i slutet av denna session)*
- **Branch:** `fas-f-fresh-data`
- **Venv:** Pipeline-venv (`Pipeline\02. Elasticity\.venv`), Python 3.11.9

---

## Status vid sessionsstart

**Cluster-modellen körd klart på växande fönster (1521 KEY, 2022-07-04 → 2026-04-27).
Pipeline steg 1–4 leverade output_summary.xlsx. Nu ska fallback-blenden (steg 5)
köras på växande output för att producera den affärsanvändbara elasticiteten.**

### Klart (verifierat 2026-06-05)

- ✅ Steg 1 (`regular_price.py`) + Steg 2 (`data_prepration.py`) körda lokalt
- ✅ Steg 3 (`feature_selection.py`) körd på VM (~30 min, 1521 grupper, klar exit)
- ✅ Steg 4 (`model.py`) körd på VM (~25 min, model_summary + output_summary skrivna)
- ✅ VM deallokerad efter körning
- ✅ Output arkiverad: `_archive_growing_2026-04-27\` (output_summary, model_summary, model_results.csv + run-loggar)
- ✅ `compare_elasticity_runs.py` byggt — jämför växande (1521 KEY) mot BCG facit (3812 KEY)

### Referensvärden från växande output_summary.xlsx (Cluster, pre-fallback)

| Mätning | Växande | BCG facit |
|---|---:|---:|
| Antal KEY | 1521 | 3812 |
| Gemensamma KEY (inner join) | 1310 | 1310 |
| Signifikanta (IB.2-gate: RSQ≥0.5 AND p≤0.2) | 362 (23.8%) | 1541 (40.4%) |
| Median elasticitet (alla) | -0.11 | (ej beräknad) |
| Tecken-flippar mellan körningarna | 322 (24.6%) | - |
| Max \|elasticitet\| | 12.7 | 820 (BCG har absurda svansvärden, IB.9) |

**Tolkning per IB.10:** Tecken-flippar på fin nivå är svag-signal-OLS, inte fel.
Pre-fallback är inte beslutsunderlag — fallback (steg 5/6) gör det användbart.

### Återstående pending (sessionsmål)

- ⏳ Kör `fallback_blend.py` på växande output → `final_model_cluster_granularity.xlsx`
- ⏳ Mät växande post-fallback Significant?-andel (BCG-facit: 48.4%)
- ⏳ Bedöm rimlighet av växande post-fallback (då först blir affärs-tolkning meningsfull)
- ⏳ Dokumentationspass: KÄRNPRINCIPER-uppdatering enligt sessionsslut 2026-06-05

---

## Mål för denna session

### Primärt: Etapp F.7 — Cluster-fallback på växande fönster

**Syfte:** Producera `final_model_cluster_granularity.xlsx` för växande fönster
och mäta Significant?-andel post-fallback. Detta är den första körningen där
affärs-tolkning av elasticiteterna är meningsfull (per IB.2 och IB.10).

**Leveranser:**

1. **`final_model_cluster_granularity.xlsx`** för växande fönster i `_archive_growing_2026-04-27\`
2. **Post-fallback metrics** — antal Significant?=1 av 1276 (alla cluster-grupper),
   distribution av elasticiteter, antal extremvärden filtrerade bort
3. **Reasonableness-bedömning** — kan vi nu lita på modellen för affärsbeslut?
   Decision-makers vill veta: hur många produkter har trovärdiga elasticiteter,
   och vilka är riskprodukter med "räddade" representanter
4. **Dokumentationspass** vid sessionsslut

**Datakälla:** `_archive_growing_2026-04-27\output_summary.xlsx` (just producerad)

**Förväntad körtid:** `fallback_blend.py` körs **lokalt** (inte Ray, inte tungt) —
~30 sek till några minuter. Ingen VM behövs.

---

## Etappstruktur Fas F (uppdaterad)

| Etapp | Innehåll | Status |
|---|---|---|
| F.1–F.5 | DW-extraktion, lokala steg, smoke, VM-prep, check_env | STÄNGD |
| F.6 | VM-körning steg 3+4, compare-rapport | **STÄNGD 2026-06-05** |
| **F.7** | **Cluster-fallback på växande (steg 5) + rimlighetsbedömning** | **← DENNA SESSION** |
| F.8 | Site- och Bundle-modeller (samma VM-flöde som F.6) | Planerad |
| F.9 | Steg 6 (`Fall_Back_Logic.py`, F1–F7-väv) på växande | Planerad efter F.8 |

**Sequencing-not (Jens 2026-05-25):** Reasonableness gate kommer **sist**, efter
full replikering. F.7 är **inte** rimlighetsgate — det är att producera och
*första* rimlighetsbedömningen av modellen post-fallback. Slutgiltig gate
kommer efter F.9.

---

## Filer att ladda upp vid sessionsstart

### Obligatorisk kontext

| # | Fil | Sökväg |
|---|---|---|
| 1 | KÄRNPRINCIPER.md | Bibliotek/ |
| 2 | MASTER_PYTHON.md | Bibliotek/ |
| 3 | NEXT_SESSION.md | denna fil |
| 4 | INSIGHTS_BCG.md | C:\Projekt\BCG\ — innehåller IB.1, IB.2, IB.9, IB.10 |
| 5 | LESSONS_BCG.md | C:\Projekt\BCG\ |

### Referens vid behov

| # | Fil | Sökväg | Syfte |
|---|---|---|---|
| 6 | BCG_PRICING_PLAYBOOK.md | C:\Projekt\BCG\ | Modell-arkitektur |
| 7 | README.md | C:\Projekt\BCG\ | Projektöversikt |

---

## Pre-flight

### 1. Verifiera output finns och är intakt

```powershell
cd C:\Projekt\BCG
.\Pipeline\"02. Elasticity"\.venv\Scripts\Activate.ps1
```

```powershell
python -c "import pandas as pd; p = r'C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\_archive_growing_2026-04-27\output_summary.xlsx'; df = pd.read_excel(p); print('Shape:', df.shape); print('KEY-unika:', df['KEY'].nunique()); print('Columns:', df.columns.tolist())"
```

**Förväntat:** Shape (1521, 8), 1521 unika KEY, samma 8 kolumner som BCG facit.

### 2. Lokalisera `fallback_blend.py`

```powershell
Get-ChildItem "C:\Projekt\BCG" -Recurse -Filter "fallback_blend.py" -ErrorAction SilentlyContinue | Select-Object FullName, Length, LastWriteTime
```

**Förväntat:** Filen finns (commitad i `163912e` enligt session-loggen). Hittas
inte den — sök bredare i `OneDrive\Datastrategi\BCG` också (kärnprincip 6.4).

### 3. Git-status

```powershell
cd C:\Projekt\BCG
git log --oneline -3
git status
```

**Förväntat:** Branch `fas-f-fresh-data`, working tree clean (efter F.6:s commit).

---

## Sessionens huvudkörning — Fallback-blend på växande

### A) Förstå kontraktet (KÄRNPRINCIP: läs källan innan du bygger)

Inspektera `fallback_blend.py` — vilka argument tar den, vilka filer förväntar
den, vart skriver den output? Detta gjordes i FAS 5-sessionen (commit `163912e`)
mot frusen output. Vi gör samma sak men med växande output som input.

```powershell
Get-Content <sökväg till fallback_blend.py> | Select-Object -First 60
```

Avgör om scriptet tar argv-flagga för input/output-sökväg, eller om vägarna är
hårdkodade och måste patchas/parametriseras för växande körning.

### B) Backup av eventuell befintlig output

Om scriptet skriver till en hårdkodad sökväg som redan har facit-validerad
output (frusen körning från FAS 5) — backupa **innan** växande-körning, så
facit-baselinen inte skrivs över.

```powershell
$facit_output = "<sökväg till final_model_cluster_granularity.xlsx>"
if (Test-Path $facit_output) {
    Copy-Item $facit_output "$facit_output.facit-baseline.bak"
}
```

### C) Kör `fallback_blend.py` på växande input

Förväntat: <5 min, lokalt, ingen Ray. Logg till fil.

```powershell
python <fallback_blend.py> 2>&1 | Tee-Object -FilePath "_archive_growing_2026-04-27\run_log_fallback.txt"
```

**OBS Tee-Object-bugg (LB.31):** Tee fångar inte stderr i PS 5.1. Om körningen
har viktig stderr-output — använd `*>&1` istället.

### D) Verifiera output och mät metrics

```powershell
python -c "
import pandas as pd
p = r'<sökväg till final_model_cluster_granularity.xlsx>'
df = pd.read_excel(p)
print('Shape:', df.shape)
print('Columns:', df.columns.tolist())
print('Significant?=1:', (df['Significant ?']==1).sum() if 'Significant ?' in df.columns else 'KOLUMN SAKNAS')
print('Andel signifikanta post-fallback:', round((df['Significant ?']==1).mean()*100, 1), '%')
"
```

**Jämförvärden:**
- BCG facit post-fallback: **618/1276 = 48.4%** (från SESSION 2026-05-25)
- Vår pre-fallback (steg 4 output): **362/1521 = 23.8%** (från F.6)
- Förväntat post-fallback: någonstans mellan dessa, eller högre om mer data ger bättre signal

### E) Arkivera och commita

```powershell
$dst = "C:\Projekt\BCG\Pipeline\02. Elasticity\2. Product Cluster Level Models\_archive_growing_2026-04-27"
# Kopiera output till arkivet om den hamnat någon annanstans
# (gör detta efter att fallback_blend.py-output är verifierad)
```

---

## Standarder att följa

### Lärdomar relevanta för denna session

- **IB.2** — `Significant?` = `RSQ≥0.5 AND p≤0.2` (inte p<0.05). Rescue sker
  inne i blenden före flaggan räknas.
- **IB.10** — Tecken-flippar på fin nivå är svag-signal-OLS, **rensas bort av
  fallbacken**. Förvänta att de 322 tecken-flippar vi såg i F.6 försvinner i
  post-fallback-output.
- **IB.1** — Rå signifikans 17-18% på fin nivå är normaltillstånd, även hos BCG.
  Fallback är hur 48% nås.
- **LB.24** — Validera mot fryst original, aldrig arbetskopian. BCG-facit ligger
  i `OneDrive\Datastrategi\BCG\BCG_orginal_V2_New\` (skrivskyddad sanning).
- **Kärnprincip 6.4** — Bred filsökning före designresonemang. Innan ny kod
  byggs — sök befintliga artefakter brett (både evbcgpricing-repot och
  OneDrive).
- **A.9** — Läs källan innan du bygger. Innan `fallback_blend.py` körs på ny
  input — bekräfta i koden vilka argument den faktiskt tar.

---

## Risker och kända begränsningar

- **Hårdkodade sökvägar i fallback_blend.py** — om scriptet förutsätter att
  output_summary.xlsx ligger på en specifik plats, måste antingen scriptet
  patchas (G7-mönstret) eller filen kopieras till den platsen tillfälligt.
  Behandla som ett designval, dokumentera.
- **`Significant?`-kolumnnamn** — har mellanslag före frågetecknet
  (`Significant ?`). Det är konsultarvet; bevara stavningen.
- **Tee-Object stderr-bugg (LB.31)** — använd `*>&1` istället för `2>&1 | Tee-Object`
  vid behov av stderr i loggfilen.

---

## Vid sessionsslut

1. Verifiera att VM är deallokerad (även om vi inte rört VM:en denna session,
   bekräfta att den inte tickar)
2. Committa `final_model_cluster_granularity.xlsx` för växande till arkivet
3. Verifiera `git status` är rent
4. Uppdatera denna fil:
   - Ny SHA
   - Startpunkt för Etapp F.8 (Site- och Bundle-modeller på VM)
   - Eventuella nya lärdomar (men: lärdomshierarkin — KÄRNPRINCIPER först,
     LB.X bara om genuint BCG-specifikt)
5. Lägg eventuella nya insikter i `INSIGHTS_BCG.md` (om något konkret om
   modellbeteendet upptäcktes)

---

*Skapad: 2026-06-05 vid avslut av session F.6 (Cluster steg 1–4 på växande
fönster). Inom 2 minuter ska AI:n kunna läsa filen och utan ytterligare kontext
förstå exakt var projektet befinner sig och vad nästa session ska göra.*
