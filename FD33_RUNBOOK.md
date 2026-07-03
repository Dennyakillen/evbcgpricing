# FD.33 RUNBOOK — Blob-migreringen till BLOB_MALSTRUKTUR (Etapp A + B)

**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia). **Författare:** Claude-rådgivare, FD.33-passet 2026-07-03.
**Kanonisk design:** `BLOB_MALSTRUKTUR.md` (familj-yttre/fönster-innerst, förenad 2026-07-03-natten).
OBS: FD.33-texten i FUTURE_DEVELOPMENT (2026-06-16, BCG-prefix) är ERSATT av denna design — se §6 korrigeringsblock.

---

## 0. Bärande princip (läs innan körning)

BLOB_MALSTRUKTUR:s fyra-kartor-varning styr allt: runners (1), blob.py (2), appen (3)
och datat (4) måste peka likadant — halvmigrerat är värre än dagens. Därför är passet
delat i två etapper med olika riskprofil:

- **Etapp A (idag, riskfri):** karta 4 exekveras som KOPIA (gamla vägar orörda —
  pipelinen fortsätter fungera oförändrat) + karta 2 landas ADDITIVT (blob.py v2:
  nya byggare, legacy byte-identiskt — bevisat i leveransen).
- **Etapp B (cutover, en commit):** karta 1 + 3 + PULL-flippen (`_AFTER_INPUTS` →
  `after_inputs_v2`) i EN commit, bevisad av uppdaterad dry_run grön. Kräver filerna i §5.

Rollback: Etapp A = `git revert` av blob.py + nya prefix kan lämnas/raderas (original orört).
Destruktivt sker ALDRIG förrän `--purge`, som är gated på granskad karantän + grön Etapp B.

---

## 1. Etapp A — körordning (allt lokalt, ingen VM)

```powershell
# PowerShell, C:\Projekt\BCG
# TOKEN FÖRST — OMEDELBART före, inte "i morse" (LB.88, dagens dyraste läxa):
az account show --query name -o tsv          # MÅSTE: ev-lz3-ai (SE)
az login --scope https://management.core.windows.net//.default
$env:PRICINGMODEL_AUTH = "key"

# 0. Placera filerna (från leveransen):
#    blob_archaeology.py, blob_migrate_fd33.py  ->  C:\Projekt\BCG\tools\
#    blob.py (v2)                               ->  C:\Projekt\BCG\orchestration\infrastructure\blob.py
#    (git diff blob.py FÖRST — verifiera själv att diffen är rent additiv)

# 1. Sanity: blob.py v2 självtest (round-trip + path-kontrakt, rör bara sin testblob)
py -3.11 orchestration\infrastructure\blob.py

# 2. ARKEOLOGI (read-only) — inventera + klassificera allt
py -3.11 tools\blob_archaeology.py
#    GRANSKA kvittot: KNOWN-INVALID/STUB/UNKNOWN-listorna + omappade fönster.
#    Fel fönster-mappning? Redigera DATE_TO_WINDOW-tabellerna i skripthuvudet, kör om.

# 3. PLAN (dry-run, default) — se exakt vad som skulle kopieras vart
py -3.11 tools\blob_migrate_fd33.py
#    GRANSKA: copy-rader rimliga? HOLD-rader förklarade? skip-bulk-volymen ok?

# 4. COMMIT — utför kopior + kvitto-uppladdning + MANIFEST.json (BB.11)
py -3.11 tools\blob_migrate_fd33.py --commit
#    Grind inbyggd: varje kopia/upload storleksverifieras, FAIL rapporteras.

# 5. KARANTÄN — ställ undan ogiltiga generationer (originalen KVAR)
py -3.11 tools\blob_migrate_fd33.py --quarantine

# 6. Verifiera för ögat (mät, gissa inte — även på framgång):
$key = az storage account keys list --account-name evbcgpricinginput --resource-group ev-openai-swce-rg-test --query "[0].value" -o tsv
az storage blob list --account-name evbcgpricinginput --container-name output --prefix "final/2022-07-01_2026-05-31/" --account-key $key --query "[].{name:name, B:properties.contentLength}" -o table
az storage blob list --account-name evbcgpricinginput --container-name receipts --prefix "rationality/2022-07-01_2026-05-31/" --account-key $key --num-results 10 -o table

# 7. Committa verktygen + blob.py v2 (atomärt; git remote -v först)
git add tools\blob_archaeology.py tools\blob_migrate_fd33.py orchestration\infrastructure\blob.py
git commit -m "FD.33 Etapp A: arkeologi + icke-destruktiv migrering till BLOB_MALSTRUKTUR + blob.py layout-lager (legacy byte-identiskt); MANIFEST.json per prefix (BB.11); post-PUSH-verifiering i nya upload-vagarna"
git push origin main
```

**Tidsuppskattning:** arkeologi 1–3 min; plan sekunder; commit 5–20 min (kvitton är många men små; server-side-kopior inom kontot är momentana). `--with-dataprep` (CSV:erna, valfritt) adderar uppladdningstid för ~200–600 MB.

**Kända egenheter:**
- `--purge` körs INTE i Etapp A. Den väntar tills Etapp B är grön och karantänen ögnats.
- REGENERABLE-BULK (automl-träden, tusentals per-KEY-filer) hoppas med flit — de är
  mellandata. Vill du bevara dem: `--include-bulk` (medvetet val, inte default).
- Prod-kontokollen (FD.35-domen): `py -3.11 tools\blob_archaeology.py --also-prod`.
  Når PIM-scopet inte prod degraderar den mjukt (observation loss ≠ failure, AZ.7).

---

## 2. Fyra-kartors-statustavla (uppdatera vid varje steg)

| # | Karta | Fil(er) | Status efter Etapp A |
|---|---|---|---|
| 4 | Datat i nya facken | blob_migrate_fd33 | ✅ KOPIERAT (original orört) |
| 2 | blob.py path-byggare | blob.py v2 | ✅ LANDAT ADDITIVT (v2 oanropat av befintlig kod) |
| 1 | Runners skriver output | run_after + 3 familje-runners | ⬜ ETAPP B (filer krävs, §5) |
| 3 | Appen läser per fönster | app.py (5 kvittofunktioner) + story_config | ⬜ ETAPP B (fil finns uppladdad; flippas MED karta 1) |
| — | Beviset | dry_run_pipeline.py uppdaterad → grön | ⬜ ETAPP B |

---

## 3. Öppna beslut 1–2 (NEXT_SESSION) — rekommendation + färdiga kommandon

**Beslut 1 — `model_results.csv` maj (505 MB, ENBART på VM-disk).**
REKOMMENDATION: **ladda upp, engångs.** Skälet är exakt robusthetsmålet: en nyckelfil
med enda kopia på en disk som överlever deallocate men inte VM-ombyggnad. 505 MB Blob
kostar ören/månad; regenerering kostar en 70-min VM-körning. Nya hemmet:
`output/site/2022-07-01_2026-05-31/model/model_results.csv`.

```powershell
# Kräver VM-start (~5 min). Kör när det passar — inte blockerande för Etapp A/B.
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
scp azureuser@172.18.148.4:~/bcg/site/output/model/model_results.csv "$env:TEMP\model_results.csv"
py -3.11 -c "import os,sys; os.environ['PRICINGMODEL_AUTH']='key'; sys.path.insert(0,r'C:\Projekt\BCG\orchestration\infrastructure'); sys.path.insert(0,r'C:\Projekt\BCG\orchestration\shared'); import blob; from pathlib import Path; svc=blob._client(); bc=svc.get_container_client('output').get_blob_client(blob.output_family_blob('site','2022-07-01_2026-05-31','model/model_results.csv')); p=Path(os.environ['TEMP'])/'model_results.csv'; f=open(p,'rb'); bc.upload_blob(f, overwrite=True, max_concurrency=4); f.close(); print('UP', bc.get_blob_properties().size, 'B ==', p.stat().st_size, 'B lokalt')"
az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
az vm get-instance-view --resource-group ev-openai-swce-rg-test --name bcg-poc-vm --query "instanceView.statuses[1].displayStatus" -o tsv
```

**Beslut 2 — automl-mappen på VM (april-era).**
REKOMMENDATION: **dokumentera som regenererbar, ladda EJ upp.** Per-KEY-mellandata,
tusentals småfiler, noll konsumenter nedströms. Noteras i fönstrets MANIFEST som
"regenerable, not preserved" (migreringsskriptets skip-bulk-rader ÄR den noteringen).

---

## 4. Vad Etapp A låser upp (och vad som fortfarande väntar)

- **Leverans 2 (kvitton per period):** datat ligger nu i `receipts/<suite>/<window>/` —
  appens läs-flip (karta 3) är sista biten. `blob.list_receipts(suite, window)` finns färdig.
- **BB.11 (MANIFEST.json):** BYGGD — skrivs av migreringen och av `upload_final`/`upload_receipts`.
  Uppdatera BACKLOG: BB.11 → MOGEN/FLYTTAD (byggd i FD.33-passet).
- **KPI-texterna/periodmedvetenhet (kö-punkt 3):** gated på Etapp B karta 3 — `story_config.py`
  rörs EN gång, i cutover-committen, inte nu.
- **Post-PUSH-verifiering (FD.38-noteringen från i morse):** BYGGD i `upload_final`/`upload_receipts`
  (`_verify_pushed` kastar vid tyst förlust). Aktiveras när run_after byter till `upload_final` i Etapp B.

---

## 5. ETAPP B — exakt vad jag behöver av dig (ladda upp dessa filer)

För cutover-committen (kartorna 1+3 + PULL-flip + beviset), i prioritetsordning:

1. `orchestration\runners\run_after.py`            (PULL/PUSH-flip: --window, download_outputs_v2, upload_final, upload_receipts)
2. `orchestration\runners\run_cluster_model.py`     (output-skrivning → output_family_blob)
3. `orchestration\runners\run_site_model.py`        (dito — horisontell regel BB.13: samma brist i alla tre)
4. `orchestration\runners\run_bundle_model.py`      (dito)
5. `verify_tool\dry_run_pipeline.py`                (de 19 kontrollerna → nya strukturen = BEVISET)
6. `orchestration\shared\run_status.py`             (window_run_id-kontraktet — läses, rörs sannolikt ej)
7. `tools\status_ops.py`                            (kö-punkt 1: v1.2 ren helfil levereras i samma väva)

Har jag redan (från denna session): `app.py`, `story_config.py`, `dashboard.html`, `blob.py`.
Etapp B-leveransen blir: patchade helfiler för 1–5 + app.py (5 kvittofunktioner per run_id via
`list_receipts`, lokal fallback) + story_config single-touch (BB.6b/BB.12/periodmedvetenhet)
+ status_ops v1.2 — allt i EN cutover-commit, dry_run grön som slutbevis.

---

## 6. Dokument-korrigeringar (klistra in, additivt)

**FUTURE_DEVELOPMENT.md — under FD.33-sektionen, överst:**
```
> **ERSATT DESIGN (2026-07-03):** BCG-prefix-målet nedan (2026-06-16) ersattes av den
> förenade designen i BLOB_MALSTRUKTUR.md (familj-yttre/fönster-innerst + receipts-container).
> Etapp A EXEKVERAD 2026-07-03: arkeologi + icke-destruktiv migrering + blob.py layout-lager
> + MANIFEST.json (BB.11 byggd) + post-PUSH-verifiering. Etapp B (cutover runners/app/PULL,
> dry_run som bevis) återstår. Verktyg: tools/blob_archaeology.py, tools/blob_migrate_fd33.py.
> Runbook: FD33_RUNBOOK.md.
```

**FUTURE_DEVELOPMENT.md — under FD.35:**
```
> **Mätning 2026-07-03:** status + output + facit skrivs/läses ALLA mot evbcgpricinginput
> (test) — blob.py-default omflippad sedan FD.28 steg 1. Ett hem de facto. Kvar för stängning:
> prod-svepet (tools/blob_archaeology.py --also-prod) bekräftar att evipricingmodelstprod är
> tomt på kvarlämnad runstatus/output. Grönt svep => FD.35 STÄNGD.
```

**BACKLOG.md — BB.11:** status → `MOGEN/FLYTTAD 2026-07-03 (byggd i FD.33: migreringen +
upload_final/upload_receipts skriver MANIFEST.json per prefix)`.

---

## 7. Rollback (om något känns fel)

1. `git revert <Etapp A-commit>` — blob.py tillbaka, verktygen borta ur trädet.
2. Nya prefixen i Blob kan lämnas (skadar inget — inget läser dem förrän Etapp B) eller
   raderas manuellt (`az storage blob delete-batch --pattern "cluster/2022-07-01*"` etc).
3. Karantänen är kopior — originalen orörda tills `--purge`, som inte körts.
Gamla flödet (dagens gröna kedja) påverkas INTE av Etapp A i något läge.
