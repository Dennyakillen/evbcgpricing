# NEXT_SESSION — Phase Z / FAS A: run_data.py (lokala bränsleledet → Blob)

Du agerar som senior teknisk rådgivare för Jens Palmö (Senior Business Analyst).
Följ KÄRNPRINCIPER.md samt relevanta MASTER_*.md. Aktuellt nuläge i STATE.md.

> Läs FÖRE start: STATE.md (nuläge), KÄRNPRINCIPER.md (slå upp dagens mål i routern §0),
> samt: LESSONS_BCG.md tier-a (särskilt LB.58 DW-når-ej-VM, LB.65 data-prep-ej-VM, LB.66
> artefakt-i-Blob-överlevnad, LB.67 AAD-tyst-tomt, LB.68 ingen-auto-shutdown),
> blob.py (upload_inputs, byggd+verifierad denna session), run_status.py (extraction-fasen finns),
> tools/replicate_dataprep.py + Business_Analytics/regenerate_transaction_parquet_chunked.py (de
> två lokala stegen run_data.py ska kedja), FUTURE_DEVELOPMENT.md FD.26-29.

---

## VAR VI STÅR (efter session 2026-06-15 b — bränsleledets Blob-transport bevisad)

**Stort arkitekturbeslut låst denna session:** data prep körs LOKALT (DW nås ej från VM, LB.58; och
DuckDB-prep behöver inte VM:ens RAM, LB.65), men dess artefakter går till Blob FÖR ATT ÖVERLEVA den
icke-säkerhetskopierade lokala datorn (LB.66). VM:en är till för Ray-modellstegens RAM, inget annat.
"Allt till Azure" = input+output+motor i Azure som driftsäker miljö, INTE att all beräkning sker där.

**Byggt + verifierat denna session:**
- `upload_inputs(local_paths)` i blob.py — laddar input till ny `input`-container, platt namn,
  overwrite, LB.39-storlekskontroll. Importerar rent (`OK: input | upload_inputs: True`).
- `input`-containern skapad på evipricingmodelstprod (bredvid output/runstatus).
- `test_upload_parquet.py` — laddade upp transaction_data.parquet (1144,5 MB) → **storlek matchar,
  121s, ~9 MB/s.** Bränslet når Azure, bevisat.

**INTE byggt (medvetet uppskjutet):** run_data.py (kedjan), how_sv-webapptexten. Båda nästa session.

---

## Mål

### Primärt: `run_data.py` — ett kommando kör hela lokala bränsleledet (FD.26)
**Levererar:** en orkestrerande runner som (1) regenererar parqueten, (2) kör DuckDB-data-prep,
(3) laddar upp parqueten till Blob — körbar via terminal ELLER VS Code "Kör", med
`--skip-regen/--skip-prep/--skip-upload/--end`-flaggor. Anropar BEFINTLIGA bevisade skript (A.9),
återimplementerar inte. Bygg UTAN statusrapportering först (lager 1).
**Verifieras med:** `py -3.11 run_data.py --skip-regen --skip-prep` (bara upload, mot redan uppladdad
parquet — idempotent) → storlek matchar. Sedan full kedja på växande fönster.
**Berör:** Business_Analytics/regenerate_transaction_parquet_chunked.py, tools/replicate_dataprep.py,
orchestration/infrastructure/blob.py (upload_inputs).
**Designfakta (mätt):** upload 1 GB ≈ 2 min synkront → ingen detach behövs.

---

## Kö (efter primärt mål, lägst risk/högst värde först)

1. **Statusrapportering i run_data.py (lager 2)** — skriv extraction-fasen till statuskontraktet
   (run_status.py har redan `Phase("extraction", ..., LOCAL)`), så bränsleledet syns i webappen med
   samma fas-rendering som modell-runnersna. "Användarupplevelsen hänger ihop."

2. **how_sv-webapptext (FD.27)** — `how_sv`-fält på extraction-fasen i story_config.py + renderingsrad
   i dashboard.html (if(st.how_sv)-mönster, rad 228-231). Texten pekar på run_data.py. Beror på att
   run_data.py finns (annars beskriver texten ett icke-existerande flöde). dashboard.html är ren UTF-8.

3. **MASTER_AZURE-pass: LB.63 + LB.67 ihop** — objektlager-nyckel-entitet (LB.63) + AAD-tyst-tomt
   (LB.67). Båda korsar projektgräns, båda rör objektlager. Avgör med Jens om de lyfts. Hör ihop med
   container-per-familj (FD.28).

4. **Container-per-familj (FD.28)** — finåkning, eget städpass mot fungerande motor. EFTER att
   run_data.py + kedjan är grön.

---

## Snubbeltrådar denna session

- **Token dör var 4:e h (E.3):** dog TVÅ gånger 2026-06-15. `az login --scope
  https://management.core.windows.net//.default` före varje Blob/VM-arbetspass.
- **Subscription-fällan (LB.46):** `az account show` → `ev-lz3-ai (SE)` före VM/storage-kommandon.
- **Storage dataplane = nyckel-läge (LB.67):** `--auth-mode key` / PRICINGMODEL_AUTH=key. AAD ger
  TYST tomt utan dataroll — inte 403. Tomt ≠ saknas.
- **Ingen auto-shutdown (LB.68):** deallokera VM:en MANUELLT, alltid. Inget auto-skydd finns.
- **Kod-i-prompten:** PowerShell är för kommandon/output. Redigera filer via skript (backup + UTF-8
  utan BOM), inte genom att klistra Python i prompten.
- Resten: STATE §7 + LESSONS tier-a.

---

## Pre-flight
```powershell
cd "C:\Projekt\BCG"
git log --oneline -5
git status
```
Förväntat: working tree clean efter denna sessions commit (blob.py + test_upload_parquet.py).
```powershell
az login --scope https://management.core.windows.net//.default
az account show --query name -o tsv
```
Förväntat: `ev-lz3-ai (SE)`.

---

## Vid sessionsslut
- [ ] committat + pushat; git status clean
- [ ] lärdomar fångade brett → §6.6-prövning → rätt fil (eller avslag)
- [ ] eskaleringskontroll (mekanism + korsar projektgräns → flagga)
- [ ] STATE uppdaterad (SHA, VM-status, datum)
- [ ] NEXT_SESSION uppdaterad (nästa mål + kö)

---

*Skapad 2026-06-15 av Jens Palmö (utvecklare) med AI-rådgivaren. Ersätter föregående NEXT_SESSION
(data prep via Azure — vars premiss reviderades: data prep stannar lokalt, LB.65/66). Primärmålet
run_data.py vilar på den bevisade upload_inputs-transporten.*
