# NEXT_SESSION — BCG Pricing (efter komplett VM-replikering)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md`, `MASTER_AZURE.md`,
`MASTER_AZURE_COMPUTE.md`. Linux/bash-handhavande: `UBUNTU_AZURE_VM.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant MASTER_*.md.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git
- **Lokal arbetsrot:** `C:\Projekt\BCG`
- **Källa (facit):** `C:\Projekt\BCG\Elasticity\Product_Cluster\...` samt V2_New i OneDrive
- **Azure-VM:** `bcg-poc-vm` i `ev-openai-swce-rg-test` (sub `ev-lz3-ai`), privat IP `172.18.148.4`
- **Status:** VM **deallocated**. Allt arbete består på disken.
- **Azure-resultat hämtat lokalt** (gitignorerat):
  - `...\output\azure_run_model\` (model-output)
  - `...\output\azure_run_automl\` (feature_selection, 3812 _All_itrs + results/)
  - `...\output\azure_run_dataprep_data_for_model.csv` (vår input-prep-output)

---

## Status vid sessionsstart

**Hela den VM-körbara pipelinen är replikerad och validerad mot facit. VM-arbetet är avslutat.**

Validerad kedja (allt körts på Azure-VM, validerat mot BCG:s frusna facit):
- regular_price → data_prepration → vår `data_for_model.csv` = **BIT-FÖR-BIT identisk med BCG:s**
  (max diff 1e-15, floating-point-brus; enda filskillnad = radslut CRLF/LF).
- feature_selection (3812 grupper) → troget mot facit (93,1% identiskt feature-val, elasticitet/R2 korr 1,0).
- model (3812 grupper) → output_summary elasticitet **bit-för-bit** mot facit (korr 1,0, max diff 0).

Bekräftat: `InScope Mapping.xlsx` / competitor-data var DÖD CONFIG — koden läser dem aldrig.

---

## Mål för denna session — välj spår (inget är VM-bundet)

### Spår A: Steg 5 — `data_prep_after_model_output.py` (Windows/Excel)
Sista pipeline-steget, matar in i prismodell-arbetsboken. **Kräver Excel + Windows** (xlwings, D14) —
körs lokalt, INTE på VM. Läs scriptet först (vad det läser/skriver), kör mot vår/BCG:s model-output,
validera resultatet. Mindre session.

### Spår B: SQL data prep (migrering, eget spår)
Ersätt DuckDB-flödet med Python/DW-vyer. Detta är migrering, inte replikering — större. Egen session,
ev. flera. Avgör först: ren Python-duckdb-replik, eller direkt mot DW-vyer (spår B i playbook §B)?

### Spår C: Fall Back Logic (fas 6)
Oläst. Hårdkodade sökvägar (R6). Läs först, storleksbedöm sedan. Egen session.

**Rekommendation:** Spår A (steg 5) är minst och stänger den sista pipeline-rutan; ta den först om
prismodell-input behövs snart. Annars B om driftmålet (egen prep) prioriteras.

---

## Driftrutin om VM behövs igen

Se `README.md` → "Daglig drift" + `UBUNTU_AZURE_VM.md`. Kort: `az login` → `az account set` → PIM →
`az vm start` → vänta ~1 min → `ssh` → `source .venv/bin/activate`. tmux-sessioner borta efter
deallocate. **Deallokera efter användning.**

---

## Standarder särskilt relevanta nu

- **Läs koden, inte configen** — `InScope`-lärdomen: död config lurade oss; `Select-String` avslöjade.
- **R7:** verifiera filen, aldrig loggraden.
- **Kostnad:** spår A/C kräver ingen VM. Bara starta VM om något måste köras där.
- **Token (E.3):** `az`-token dör efter 4 h.
- **D13/D14:** plattformsanpassningar minimalt + loggas; xlwings-steg hör till Windows.

## Öppna / kvar

| # | Fråga | Status |
|---|---|---|
| O1 | Owner på RG | Kent — endast om Blob/DW-drift (spår B-drift) ska sättas upp |
| O4 | Blob + DW-vyer (drift) | Senare, efter att replikeringen är komplett dokumenterad |

*Skapad 2026-05-21 vid avslut av den kompletta VM-replikeringssessionen.*
