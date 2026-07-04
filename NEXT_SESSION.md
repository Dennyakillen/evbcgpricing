# NEXT_SESSION — FD.33 Etapp B: cutover-committen (fyra kartor flippar tillsammans)

Du agerar som senior teknisk rådgivare för Jens Palmö (Senior Business Analyst).
Följ KÄRNPRINCIPER.md samt relevanta MASTER_*.md. Aktuellt nuläge i STATE.md.

> Läs FÖRE start: STATE.md, KÄRNPRINCIPER.md (router: cutover/pipeline-ändring),
> BLOB_MALSTRUKTUR.md (målbilden), FD33_RUNBOOK.md §5 (Etapp B-planen), DEPLOY_DASHBOARD.md.

## Mål

### Primärt: FD.33 Etapp B — skriv-sidans cutover i EN commit
**Levererar:** run_after (--window, download_outputs_v2, upload_final, upload_receipts),
tre familje-runners → output_family_blob-vägar, dry_run_pipeline uppdaterad mot nya
strukturen, status_ops v1.2 (--require-file-gate, ren helfil), app-KPI:ernas maj-backfill
mätt ur maj-kvittona.
**Verifieras med:** `py -3.11 verify_tool\dry_run_pipeline.py` → alla kontroller gröna mot
familj/fönster-strukturen = FD.33 formellt STÄNGD.
**Berör/kräver uppladdning:** `run_after.py`, `run_cluster_model.py`, `run_site_model.py`,
`run_bundle_model.py`, `dry_run_pipeline.py`, `run_status.py`, `status_ops.py` (7 filer).

## Kö (efter primärt mål)
1. **Molnpublicering exekveras** — DEPLOY_DASHBOARD.md B2–B5 (defaults klara; EasyAuth FÖRE
   nyckel-setting). Risk: storage-brandvägg mot App Service → log tail avslöjar.
2. **FD.40** — revenue-coverage-talet mäts ur extraction coverage-kvittot → story_config
   FUNNEL extraction["coverage"]. Ovisade värden renderas aldrig.
3. **Facit-fönstret i run-väljaren** — saknas facit-runstatus i Blob: skapa via status_ops
   (en rad). Ger tredje fönstret i appen.
4. **Kvarvarande dokumentklistringar** — DOC_UPPDATERINGAR_2026-07-03.md om ej redan gjort.
5. **FD.35-domen** — `tools\blob_archaeology.py --also-prod` när prod-läsrätt finns.

## Snubbeltrådar denna session
- **Fyra-kartors-regeln:** runners + app + `_AFTER_INPUTS`-flip landar i SAMMA commit,
  aldrig delvis (BLOB_MALSTRUKTUR §varning). Etapp A:s gamla vägar är orörda = rollback.
- **Bundle-källan i dry_run = frozen facit** (pipeline/00_frozen_facit/bundle/), INTE
  output/bundle/<fönster>/ (den bär en ofullständig 06-24-körnings artefakter).
- **Token 4h (LB.88):** `az login` OMEDELBART före varje Blob-tungt block — post-PUSH-
  grinden (`_verify_pushed`) kastar numera i stället för att tappa tyst, men testa inte.
- `--purge` (karantänen) körs först EFTER grön Etapp B + mänsklig granskning.

## Pre-flight
```powershell
cd "C:\Projekt\BCG"
git log --oneline -5
git status
```
Förväntat: senaste commit 47e0553 (eller nyare, se STATE), working tree clean.
```powershell
az login --scope https://management.core.windows.net//.default
az account show --query name -o tsv     # ev-lz3-ai (SE)
$env:PRICINGMODEL_AUTH = "key"
```

## Vid sessionsslut
- [ ] committat + pushat; git status clean
- [ ] lärdomar fångade brett → §6.6-prövning → rätt fil (eller avslag)
- [ ] eskaleringskontroll (mekanism + korsar projektgräns → flagga)
- [ ] ny term → ordlist-prövning
- [ ] STATE uppdaterad (SHA, VM-status, Blob-struktur-rader, datum)
- [ ] NEXT_SESSION uppdaterad (nästa mål + kö + router-triggers)
