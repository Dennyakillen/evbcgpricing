# DOC_UPPDATERINGAR_2026-07-03 — klistringspaket för de växande registren

**Varför additivt och inte kompletta filer:** mina baser för FUTURE_DEVELOPMENT och LESSONS
är äldre än repots (slutar vid FD.35/LB.85; repot har FD.38–39 och LB t.o.m. 90 från senare
sessioner). En "komplett fil" från stale bas hade tyst raderat de nyaste sektionerna —
levererad≠committad-klassen tillämpad på dokument. Därför: klistra blocken nedan i respektive
fil (kodning: CP1252 för LESSONS enligt filens huvud, annars som filen redan är).

═══════════════════════════════════════════════════════════════════════════
## DESTINATION 1 — FUTURE_DEVELOPMENT.md (C:\Projekt\BCG)
═══════════════════════════════════════════════════════════════════════════

### Klistra ÖVERST i FD.33-sektionen:
> **ERSATT DESIGN + ETAPP A EXEKVERAD (2026-07-03):** BCG-prefix-målet nedan (2026-06-16)
> ersattes av den förenade designen i BLOB_MALSTRUKTUR.md (familj-yttre/fönster-innerst +
> receipts-container). Etapp A KÖRD: arkeologi (14 858 objekt klassade), icke-destruktiv
> migrering (31 kopior storleksverifierade, 230 kvitton per fönster, 9 i karantän),
> MANIFEST.json per prefix (BB.11 byggd), post-PUSH-verifiering i blob.py:s nya upload-vägar.
> Dashboarden fönster-medveten (B1/B2-passen samma dag). Verktyg: tools/blob_archaeology.py,
> tools/blob_migrate_fd33.py. Runbook: FD33_RUNBOOK.md. ÅTERSTÅR: Etapp B (runners + app +
> _AFTER_INPUTS-flip i EN commit, dry_run grön = stängningsbevis) — se NEXT_SESSION.

### Klistra under FD.35:
> **Mätning 2026-07-03:** status + output + facit + receipts skrivs/läses ALLA mot
> evbcgpricinginput (test) — ett hem de facto. Kvar för stängning: prod-svepet
> (`tools\blob_archaeology.py --also-prod`) bekräftar att prod-kontot är tomt på kvarlämnad
> runstatus/output. Grönt svep => FD.35 STÄNGD.

### Klistra under FD.38 (robusthetspasset):
> **Delvis byggd 2026-07-03:** post-PUSH-verifiering (`_verify_pushed` i blob.py, kastar vid
> tyst förlust) + `PRICINGMODEL_KEY`-env-vägen (eliminerar az-CLI/4h-token-beroendet för
> nyckelläsning). Kvarvarande FD.38-delar (BB.9 tar-fetch, BB.10 selftest, io_safe) oförändrade.

### NY sektion (sätt nästa lediga FD-nummer om 40 är taget):
### FD.40 — Revenue-coverage-talet till dashboardens coverage-lins
Andel av total omsättning som de 1 151 modellerade koderna fångar — TROVÄRDIGHETSTALET
(en modell på 1 % av omsättningen saknar beslutskraft oavsett valideringar). Mäts ur
extraction coverage-kvittot (aldrig gissas), läggs sedan i story_config
`FUNNEL["extraction"]["coverage"]` med facit- och nu-värde. UI-platsen finns redan;
beslut 2026-07-03: ovisade värden renderas ALDRIG som "[fill in]" i åskådarytan —
saknas mätning visas inget, och mätuppgiften bor här.

═══════════════════════════════════════════════════════════════════════════
## DESTINATION 2 — LESSONS_BCG.md (C:\Projekt\BCG) · KODNING: CP1252
═══════════════════════════════════════════════════════════════════════════
> Sätt nästa lediga LB-nummer (91/92 om lediga). Bevisrader läggs under befintliga LB.

### Bevisrad under LB.85-klassen (härled, deklarera inte):
**Belägg 2026-07-03:** blob.py:s självtest FAILade i tre varv — det muterade fasen
'step1_dataprep' som bytt namn i default_pipeline långt tidigare (7 faser, ingen med det
namnet). Både index- och innehålls-assert föll på ett grannkontrakt som driftat under testet.
Fix: självtestet testar nu bara det modulen ÄGER (transporten: skriv→läs→parsea→re-serialisera).
En lampa som alltid lyser rött är värre än ingen — ögat lär sig ignorera den.

### LB.91 — Periodisk omritning nollställer UI-state (webapp)
Dashboardens 10-sekunders-refresh rev och byggde om hela DOM:en → varje öppnad panel
("All reviews", BCG FACIT-blocket) stängde sig "av sig själv" efter ~3 s (nästa tick).
Två strukturella fixar (2026-07-03): (1) rendera BARA när status-payloaden faktiskt ändrats
(rå-textjämförelse före JSON.parse), (2) panel-öppenläge i globala objekt (openD3/openFN/
openPP/openMore + d3cache) som återappliceras vid omritning. **Gäller om:** någon vy får
auto-refresh — state som bor i DOM:en dör med DOM:en. **Förkroppsligas i:** dashboard.html
(lastRaw-vakt + wireExtras).

### LB.92 — Dörren låses FÖRE nyckeln bärs in (publicering med secrets)
Vid App Service-publicering aktiveras Entra-inloggningen (EasyAuth) INNAN kontonyckeln
läggs som app setting — appen är aldrig ett ögonblick publikt nåbar med företagsdata
bakom sig. Generellt mönster: auth-lagret först, secrets sist, i alla deploy-sekvenser.
**Gäller om:** något publiceras utanför 127.0.0.1. **Förkroppsligas i:** DEPLOY_DASHBOARD.md
§B3 (ordningen är poängen). *Kandidat för MASTER_AZURE §3 (mekanism, korsar projektgräns) —
eskaleringsprövning vid nästa master-underhåll.*

### Bevisrad under "levererad ≠ committad"-klassen:
**Belägg 2026-07-03 (dokumentvarianten):** uppladdade FUTURE_DEV/LESSONS-baser var äldre än
repots (saknade FD.38–39, LB.86–90). En "komplett fil" regenererad från stale bas hade tyst
raderat nyare sektioner. Regel: växande register uppdateras ADDITIVT om basens färskhet inte
är bevisad; kompletta filer bara där leverantören äger sanningen.

═══════════════════════════════════════════════════════════════════════════
## DESTINATION 3 — BACKLOG.md (C:\Projekt\BCG)
═══════════════════════════════════════════════════════════════════════════

**BB.11 (Blob MANIFEST.json):** ändra statusraden till:
`**Status:** BYGGD 2026-07-03 (FD.33: migreringen + blob.upload_final/upload_receipts skriver MANIFEST.json per prefix; _append_manifest är enda skrivaren)`

**BB.12 (hjälte-KPI-regeln):** ändra statusraden till:
`**Status:** LEVD 2026-07-03 (en hero-flagga per fas i story_config STORY+FUNNEL; renderas med grön accent, samma kortstorlek; implementerad i FD.33-B2-passet)`

═══════════════════════════════════════════════════════════════════════════
## DESTINATION 4 — STATE.md (C:\Projekt\BCG) — uppdatera dessa rader
═══════════════════════════════════════════════════════════════════════════
- **Senaste commit/SHA:** 47e0553 (main, pushad) — FD.33-B2d.
- **Blob-struktur (NY sektion/rad):** kanonisk layout per BLOB_MALSTRUKTUR:
  output/<familj>/<fönster>/ · output/final/<fönster>/ · receipts/<svit>/<fönster>/ ·
  input/parquet/ + input/data_prep/<fönster>/ · pipeline/00_frozen_facit (orörd) ·
  quarantine (9 ogiltiga generationer, purge EJ körd). MANIFEST.json per prefix.
  Gamla datum-vägar ORÖRDA tills Etapp B-cutover.
- **Webapp:** v2 fönster-medveten (Blob-kvitton per svit/fönster, lokal fallback), About-flik,
  hero-pill+3-KPI-layout, render-skip+panelminne. Publicering: DEPLOY_DASHBOARD.md
  (Schemaläggaren lokalt / App Service: ACR evbcgpricingacr · plan bcg-dashboard-plan ·
  app evbcg-dashboard — fylls i med faktiska värden efter B-deployen).
- **blob.py:** layout-lager v2 (additivt), _verify_pushed post-PUSH-grind,
  PRICINGMODEL_KEY-env-väg (container/schemaläggare), självtest = rent transport-test.
- **VM-status:** deallokerad (hela 2026-07-03 utan compute).
- **Öppna beslut:** beslut 1 (model_results 505 MB) STÄNGT — fanns i Blob, migrerad;
  beslut 2 (automl) STÄNGT — dokumenterad regenererbar, ej bevarad.
