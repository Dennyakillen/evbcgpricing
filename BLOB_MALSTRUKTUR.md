# BLOB_MALSTRUKTUR — design för migrering (Leverans 2 + struktur-omläggning)

*Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia). Författare: Claude-rådgivare.*
*Skapad 2026-06-23 under cluster-maj-körningen. Status: DESIGN — ej exekverad. Eget pass.*
***Förenad med FD.28 2026-07-02 — detta dokument är nu den ENDA målstrukturen (se §Designförening).***

---

## Varför detta dokument finns

Blob-strukturen är ett engångsbeslut som är dyrt att ändra när runners + app + data
alla pekar på den. Detta dokument fångar målstrukturen så att själva omläggningen senare
blir EXEKVERING AV EN PLAN, inte ett improviserat ingrepp. Designas parallellt med att
befintlig struktur bevisar flödet (de två spåren Jens enades om 2026-06-23).

## Nuvarande struktur (roll-baserad)

    input/      parquet/transaction_data.parquet
    output/     <run_id eller datum>/ ... (blandat schema, datum vs fönster)
    runstatus/  <run_id>.json  (städat 2026-06-23: facit/april/maj, fönster-baserat)
    pipeline/   00_frozen_facit/<family>/output_summary.xlsx

Problem: output blandar scheman; kvitton finns INTE på Blob alls (bor lokalt i
verify_tool/receipts/, datum-mappar). Appen läser "senaste kvitto" oavsett vald period
(Leverans 2-glappet, bekräftat i appen 2026-06-23).

## MÅLSTRUKTUR (familj-yttre, fönster-innerst — Jens design)

    input/
       parquet/transaction_data.parquet          (bränslekällan)
       data_prep/<window>/                        (de 5 CSV:erna per fönster — spårbart)
          Sweden_weekly_model_data_P_C.csv
          Sweden_weekly_model_data_site_level.csv
          ... (P_CH, masterdata, etc)
    output/
       cluster/<window>/                          (familje-yttre = stabil axel)
          output_summary.xlsx, model_summary.xlsx, ...
       site/<window>/
       bundle/<window>/
       final/<window>/                            (Step 6 Final_Fallback + R12 Model_Feed)
    receipts/                                      (NY container)
       cluster/<window>/  site/<window>/  bundle/<window>/
       proof_chain/<window>/                       (verify_receipt FR-1..7)
    runstatus/<window>.json                        (oförändrat — redan fönster-baserat)
    pipeline/00_frozen_facit/<family>/             (oförändrat — facit-ankaret)

VARFÖR familj-yttre: familjen är FAST (alltid 3), fönstret VÄXER (nytt varje månad).
Fast ytterst + växande innerst = robust; containerstrukturen ändras aldrig, bara innehåll.
Period-väljaren funkar lika bra (glob: */<window>/ i stället för <window>/*).

## DESIGNFÖRENING med FD.28 (2026-07-02) — en målstruktur, inte två

Två konkurrerande designer fanns: denna fil (familj-yttre, fönster-innerst) och
`BLOB_STRUCTURE_DESIGN_FD28.md` (numrerade BCG-spegel-prefix: `02_cluster/`, `03_site/`,
`05_step6/` ... utan fönsterdimension). Halvmigrerad Blob är värre än dagens — så EN
design måste väljas FÖRE en enda blob flyttas. **Beslut: DENNA fil är kanonisk.
FD.28:s numrerade prefix-paths UTGÅR som struktur.**

**Skäl (i styrkeordning):**
1. **Fönstret är kontraktet.** run_id = datafönster (statusmodellen 2026-06-22,
   `window_run_id`). FD.28 saknar fönsterdimension helt och kan därför inte bära
   period-väljaren, Leverans 2 (kvitton per fönster) eller facit-vs-växande-jämförelsen
   per period — hela appens ärlighets-agenda.
2. **Familj-yttre är den stabila axeln.** FD.28:s nummer (`02_`, `03_`, `05_`) kodar
   BCG:s *lokala mappordning* in i molnstrukturen för alltid, utan funktionellt värde
   för glob-mönster, appens läsvägar eller behörigheter.
3. **En struktur.** Denna fils egen varning gäller designer lika mycket som data:
   fyra kartor ska peka samma väg — och det förutsätter att kartan är EN.

**Vad som ABSORBERAS från FD.28 (dess verkliga värden går inte förlorade):**
- **Pedagogiken "strukturen som karta"** — levereras som mappningstabellen nedan
  (+ valfritt: en liten `_STRUCTURE.md`-blob i containerroten). Dokumentation via
  dokument, inte via path-namn.
- **`validation/` per familj** — uppfylls STARKARE av `receipts/<family>/<window>/`
  (fönster-medveten i stället för tidlös).
- **Nollpunkten `pipeline/00_frozen_facit/`** — identisk i båda designerna, orörd.
- **Nyckelläge-exekverbarhet utan Kent** + FD.29-gating (AAD = en env-var senare) —
  gäller oförändrat för denna struktur.

**Mappningstabell BCG-mapp ↔ målstruktur** (FD.28:s spegel, som dokumentation):

| BCG-mapp (lokalt) | Blob-plats (mål) |
|---|---|
| Sweden_Elasticity_Data_Prep_SQL | `input/data_prep/<window>/` |
| 2. Product Cluster Level Models | `output/cluster/<window>/` + `receipts/cluster/<window>/` |
| 3. Product Site Level Models | `output/site/<window>/` + `receipts/site/<window>/` |
| 4+5. Bundle Clinic (prep + models) | `output/bundle/<window>/` + `receipts/bundle/<window>/` |
| 6. Fall Back Logic + R12/Excel_Outputs | `output/final/<window>/` |
| (BCG:s frysta 2025-facit) | `pipeline/00_frozen_facit/<family>/` |
| (körningsstatus) | `runstatus/<window>.json` |

**Åtgärder ur föreningen:**
- [ ] Märk `BLOB_STRUCTURE_DESIGN_FD28.md`-huvudet: `SUPERSEDED 2026-07-02 →
      BLOB_MALSTRUKTUR.md` (additivt — dokumentet raderas ej, §4.7).
- [ ] BB.11 (`MANIFEST.json` per körning) byggs mot DENNA struktur, efter migrering.

## Vad Azure kräver: INGENTING djupare

Blob har inga riktiga mappar — "cluster/2026-05-31/fil.xlsx" är bara ett blobnamn med
snedstreck som tecken. Mappstrukturen är EMERGENT ur namngivningen. Nya fönster skapar
inga "mappar" — de uppstår i samma sekund en blob laddas upp med det prefixet.
ENDA undantaget: en ny container (receipts/) måste skapas EN gång (containrar är riktiga).

## De fyra kartorna som måste peka om SAMTIDIGT (migrerings-risken)

1. RUNNERS skriver output -> ny path (run_{cluster,site,bundle}_model.py)
2. blob.py bygger paths -> upload_outputs/download/upload_receipts (NY)
3. APPEN läser status + output + kvitton -> app.py (5 kvitto-funktioner, output-vägar)
4. BEFINTLIG DATA migreras till nya facken -> migrerings-skript

Risken är INTE storleken (path-strängar) utan SYNKEN: gör 3 av 4 rätt, missa appens
kvitto-väg -> appen läser tomt för en familj, ser ut som data saknas (R7-klass, samma
som FD.35-kontoröran). Därför: gör HELT, på en gång, mot denna plan. Halvmigrerad Blob
(hälften gammal path, hälften ny) är värre än dagens.

## Validering: uppdaterad dry_run_pipeline som BEVIS

dry_run_pipeline.py (19 rör-kontroller) uppdateras till nya strukturen. När den är grön
ÄR det beviset att alla fyra kartor pekar likadant. Migreringen är klar när dry_run grön.
(Jens insikt: "fyra kartor"-synken är i sig en validering + dokumentation.)

## Leverans 2 (kvitton per fönster) = del av detta

Kvittona per fönster (receipts/<family>/<window>/) ÄR den nya receipts-containern.
Appens 5 kvitto-funktioner (_validator_receipt, _latest_receipt, api_receipts_list,
_parse_master_receipt, /api/receipt/) ändras: ta run_id som parameter, läs DET fönstrets
mapp, inte "senaste". Arkeologi krävs: avgör vilket fönster varje befintligt kvitto
validerade (mätbart: population i kvittot — 6624=april-site, 6604=maj-site).

## Migrerings-checklista (för exekverings-passet)

[ ] Skapa receipts-container (engångs)
[ ] blob.py: nya path-byggare (output/<family>/<window>/, receipts/<family>/<window>/)
[ ] blob.py: upload_receipts() (ny — laddar upp verify_tool/receipts/ -> Blob per fönster)
[ ] Arkeologi: mappa varje befintligt kvitto -> rätt fönster (population-mätning)
[ ] Migrera befintlig output + kvitton till nya facken
[ ] 3 runners: peka om output-skrivning
[ ] app.py: 5 kvitto-funktioner läser per run_id; output-vägar uppdaterade
[ ] dry_run_pipeline.py: uppdatera 19 kontroller till nya strukturen
[ ] Kör dry_run -> grön = migrering komplett + validerad
[ ] Verifiera appen: välj fönster -> rätt status OCH rätt kvitton per period

---
*Eget fokuserat pass. Bygg INTE under en leveranskväll. Designen växte fram parallellt
med cluster-maj-körningen 2026-06-23 — exekvering när Jens har ett dedikerat pass.
Designförening med FD.28 tillagd 2026-07-02 (denna fil kanonisk, FD.28 superseded).*
