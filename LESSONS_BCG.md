# LESSONS_BCG — Tekniska lärdomar, BCG Pricing-projektet

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde — replikering, validering, migrering)
**Lever i:** `C:\Projekt\BCG` (detta repo). Helt skild från Business_Analytics `PROJECT_LESSONS.md`.
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Senast uppdaterad:** 2026-06-12

---

## Vad detta dokument är (och inte är)

`LESSONS_BCG.md` håller **tekniska lärdomar** — fällor i miljö, infrastruktur, kod-mekanik, validerings-
plattform, replikeringsdetaljer. Varje lärdom har ett stabilt `LB.N`-ID och formatet:

```
**Symptom:** Vad som syntes.
**Rotorsak:** Varför det hände (om ej uppenbart).
**Regel:** Konkret åtgärd som förhindrar upprepning.
```

**Detta är inte:**
- **Affärs-/domäninsikter** (vad vi lärt oss om modellen/datan) → `INSIGHTS_BCG.md` (`IB.N`).
- **Beslut** (vad vi valde och varför) → `BCG_PRICING_PLAYBOOK.md` decision log (`D*`, `D-B*`, `D-F-*`).
- **Generella tekniska lärdomar** över alla projekt → `MASTER_PYTHON.md`, `MASTER_SQL.md`. Om en
  LB-lärdom blir generell, befordra den till MASTER och låt LB peka dit.

---

## Snabbindex

| ID | Lärdom | Aktiveras |
|---|---|---|
| LB.1 | DW-token-renewal var 4:e timme | DW-query kraschar med ClientAuthenticationError |
| LB.2 | DuckDB .exe blockerad av AppLocker | duckdb.exe får inte köra |
| LB.3 | Lokal OOM på Stage 2 | feature_selection.py OOM på full pipeline lokalt |
| LB.4 | Ray-memory fix i config.yml | Stage 2 kraschar med memory error |
| LB.5 | BCG:s rå-signifikans = 17.8% (cluster) | Bedöm aldrig vårt mot absolut "borde vara sig" |
| LB.6 | Verify-tool kräver global Python 3.11 | duckdb saknas i .venv |
| LB.7 | feature_selection driver Ray-workers | RayActorError vid OOM |
| LB.8 | Bundle.bundle_code = composite key | Bundle.bundle_code är komma-separerad lista |
| LB.9 | Prisstabila grupper ger absurda elasticiteter | Site har koefficienter ±200 |
| LB.10 | Encoding-mismatch BCG-input vs UTF-8 | Latin-1/CP1252 i BCG-filer |
| LB.11 | Verify_blend kräver per-rep-test, ej summa | 43 representanter, inte total |
| LB.12 | output_summary.xlsx KEY-format | Cluster-Granularity+'-'+ItemCode |
| LB.13 | Cluster-seed har 7 namnade kluster | Inte 0..6 numreriskt |
| LB.14 | FTE-XLSX-täckning slutar 2025-06 | Färska veckor får NULL |
| LB.15 | replicate_dataprep.py kräver --validate-only | Annars 12 min SQL-omkörning |
| LB.16 | output_summary innehåller bara signifikanta? Nej | Alla 3812 cluster-grupper finns |
| LB.17 | Site = department, inte clinic | ID_Department i pipelinens kontext |
| LB.18 | Bundle Hospital/Clinics rollup-grain | Bundle skär över kluster |
| LB.19 | Validera Spår A:s parquet, ej Spår B:s CSV | replicate_dataprep läser fel källa annars |
| LB.20 | data_prepration.py:s '2025-06-23' var hårdkodad | G7-fix nödvändig |
| LB.21 | PowerShell execution policy blockerar .ps1 | Använd kommandoblock, inte .ps1 |
| LB.22 | replicate_dataprep injicerar datum in-memory | SQL-filen på disk oförändrad |
| LB.23 | Verify_infra rapporterar STRAY-filer | .bak-g7 flaggas som STRAY |
| LB.24 | Validera mot fryst original, ej arbetskopia | Pipeline\data\ skrivs över av Spår B |
| LB.25 | corr 1.0 = misstänk cirkelbevis tills källoberoende | "Snälla siffror" är inte verifiering |
| LB.26 | py -3.11 för verify_tool, inte python | Windows Store-alias är en fälla |
| LB.27 | Aktiv venv ärver inte mellan PS-fönster | Aktivera i varje nytt fönster |
| LB.28 | Mät hash före fil-kopia mellan modeller | constants.py skiljer sig |
| **LB.29** | **verify_tool jämför fel CSV om sökvägar divergerar** | **Två script skriver samma filnamn i olika kataloger** |
| **LB.30** | **Två venv:er, olika paket — använd rätt för rätt jobb** | **ModuleNotFoundError trots installerad miljö** |
| **LB.31** | **Tee-Object i PS 5.1 fångar inte stderr även med `2>&1`** | **Pipeline-progress saknas i loggfilen, syns bara i terminal** |
| **LB.32** | **Ray-OOM plateau ≠ återhämtning, mät CPU-tidens tillväxttakt** | **Stabil RAM tolkas som "Ray jobbar" men är "Ray gav upp"** |
| **LB.33** | **Smoke-extrapolation underskattar Ray:s peak-RAM icke-linjärt** | **Smoke 50 KEY ok → full 1521 KEY OOM:ar** |
| **LB.34** | **`/tmp/ray_spill` försvinner vid VM-omstart, måste skapas vid varje session** | **Pipeline kraschar vid Ray-start på "ny" VM** |
| **LB.35** | **Imports propageras inte automatiskt vid str_replace-patch** | **NameError efter "lyckad" patch som la till funktion-anrop** |
| **LB.36** | **`data_prepration.py`:s "Shape"-print loggar input, inte output (~50% diff)** | **Loggrad 523k rader, faktisk fil 259k rader** |
| **LB.37** | **PowerShell multi-line-regex är opålitlig på Python-källkod, använd Python själv** | **`-replace` matchar inte över newlines utan `(?s)`-flagga** |
| **LB.38** | **"Biter inte på kärnelasticiteten" ≠ harmless** | **Datakvalitetsbrist minimerades, ledde till 73% bortfall vid yoy_seasonality** |
| **LB.39** | **Validering på producerade rader fångar inte populations-bortfall** | **verify_dataprep PASS dolde 834 droppade ItemCodes** |
| **LB.40** | **load_or_create_feature_control_file Gren B saknar return (BCG-bug)** | **feature_selection.py kraschar AttributeError NoneType, kringgås via körningsordning** |
| **LB.41** | **control_file.xlsx regenereras INTE av steg 2 (`data_prepration.py`)** | **Skapas först i steg 3, rensning före steg 2 skapar inte ny fil** |
| **LB.42** | **output_summary.xlsx ligger i `output/model/` (inte `output/`)** | **scp-kommandon med fel path får "No such file"** |
| **LB.43** | **`ls -la` mapp-datum kan misstolkas som fil-datum** | **Använd `find -newer` istället för att läsa ls-output** |

---

## Lärdomar

### LB.1 — DW-token-renewal var 4:e timme
**Symptom:** `ClientAuthenticationError: AADSTS70043: The refresh token has expired`.
**Rotorsak:** Evidensias Conditional Access tvingar refresh var 4:e timme.
**Regel:** Innan varje DW-query-pass: `az login --scope https://database.windows.net/.default`.
För längre sessioner — renew vid tecken på timeout, inte vänta på fel.

### LB.2 — DuckDB .exe blockerad av AppLocker
**Symptom:** `Access is denied` när duckdb.exe körs.
**Rotorsak:** IT-policy blockerar direkt .exe-körning.
**Regel:** Använd `duckdb` Python-paketet, inte .exe-binären. För `01_clean.sql`: importera duckdb
i Python-wrapper, kör SQL via API:t.

### LB.3 — Lokal OOM på Stage 2
**Symptom:** Stage 2 (feature_selection) kraschar med MemoryError på Jens 31 GB-maskin på BCG:s
fulla fönster.
**Rotorsak:** Kombinatorisk feature-val × Ray-parallelisering × full population (19,344 koder)
spränger lokalt RAM.
**Regel:** För FAS V — kör Stage 2 på Azure VM (`Standard_E16s_v5`, 128 GB). För FAS F med facit-pairs
(1151 koder) — testa lokalt först, kan rymmas.

### LB.4 — Ray-memory fix i config.yml
**Symptom:** Stage 2 kraschar med "Ray cluster out of memory" tidigt i körningen.
**Regel:** `config.yml` → `ray: memory: 8` och `cpus: 12`. Detta är config-fix, ingen kodändring i
`feature_selection.py` behövs. Bekräftat 2026-05-22.

### LB.5 — BCG:s rå-signifikans = 17.8% på cluster-nivå
**Symptom:** Vår cluster-output verkade ha för låg rå-signifikans (18%) — såg ut som problem.
**Rotorsak:** BCG:s egen baslinje har **17.8%** rå signifikans. Vi matchade BCG, inte misslyckades.
**Regel:** Bedöm aldrig signifikans-nivåer mot en absolut norm. Mät mot BCG:s output på samma KEY.
Se IB.1 för full förklaring.

### LB.6 — Verify-tool kräver global Python 3.11
**Symptom:** `ModuleNotFoundError: No module named 'duckdb'` när verify_dataprep körs från venv.
**Rotorsak:** Pipeline-venvarna har inte duckdb i Python-form (de använde .exe-binären innan LB.2).
**Regel:** Verify_tool körs alltid med `py -3.11` (global). Global 3.11 har: duckdb, pandas, openpyxl,
numpy, pyyaml.

### LB.7 — feature_selection driver Ray-workers
**Symptom:** `RayActorError` när feature_selection kraschar.
**Rotorsak:** Ray-workers dör tyst på OOM, parent får RayActorError istället för MemoryError.
**Regel:** Vid RayActorError — kolla först `dmesg` (Linux) eller Task Manager (Windows) för OOM-killer.
Inte ett kodfel.

### LB.8 — Bundle.bundle_code är composite key
**Symptom:** Bundle-grupper har koder som `CDF114,EEX113,NIH` — inte enskilda ItemCodes.
**Regel:** Bundle aggregerar varukorgar. `Bundle_code` är komma-separerad lista av ItemCodes i
varukorgen. När du joinar — splittra inte; jämför hela strängen.

### LB.9 — Prisstabila grupper ger absurda elasticiteter
**Symptom:** Site-output har enskilda koefficienter på ±200 och uppåt.
**Rotorsak:** Grupper med få prisförändringar → OLS instabil → koefficient blir matematiskt giltig
men praktiskt meningslös.
**Regel:** Filtrera på signifikans-grindens fyra villkor (IB.2), inte på `is_signed_negative`. Tail-
värden < −10 och > 0 rensas automatiskt.

### LB.10 — Encoding-mismatch BCG-input vs UTF-8
**Symptom:** Svenska tecken kommer ut som `Sjukhus SÃ¶dran` när CSV läses.
**Rotorsak:** BCG-CSV är CP1252 (latin-1), pandas default UTF-8.
**Regel:** `pd.read_csv(path, encoding="cp1252", encoding_errors="ignore")` för alla BCG-input. Skriv
också med `encoding="cp1252", errors="replace"` för konsistens.

### LB.11 — Verify_blend kräver per-rep-test, ej summa
**Symptom:** Verify_blend implementerades först med "samma antal representanter = match". Stämde
men sa inte mycket.
**Regel:** Per-rep-test: verifiera att samma `(Service, big_cluster)`-nyckel väljer samma
ItemCode-representant. 43/43 är beviset.

### LB.12 — output_summary.xlsx KEY-format
**Symptom:** Försökte joina output_summary med facit på ItemCode — fel grain.
**Rotorsak:** KEY i output_summary = `Cluster_Granularity + '-' + ItemCode` (cluster) eller
`SiteCode + '-' + ItemCode` (site). Inte bara ItemCode.
**Regel:** Joina på KEY, inte på ItemCode. Parsa KEY när du behöver komponenterna separat.

### LB.13 — Cluster-seed har 7 namnade kluster
**Symptom:** Antog 0..6 numreriskt — fick KeyError på "Clinics 0".
**Regel:** BCG:s 7 kluster: `Clinics 0`, `Clinics 1`, `Clinics 2`, `Sjukhus A`, `Sjukhus B`,
`Sjukhus C`, `Sjukhus Södran`. Namnade strängar, inte siffror.

### LB.14 — FTE-XLSX-täckning slutar 2025-06
**Symptom:** Färska veckor (2025-07..2026-04) får `Sum_FTE_Interpolated = NULL`.
**Rotorsak:** BCG:s FTE-XLSX (`Sweden__Interpolated_Productivity_time_date_june25.xlsx`) är frusen
till deras leveransfönster.
**Regel:** Färska körningar utanför 2022-07..2025-06 kommer att ha NULL-FTE. På sikt: bygg FTE från
Quinyx-data (`Manual.Fact_Quinyx_DayClinic`), IB.3 Väg 2.

### LB.15 — replicate_dataprep.py kräver --validate-only
**Symptom:** Body-loop-körning tog 12 minuter när jag bara ville validera.
**Regel:** För validering: `python replicate_dataprep.py --validate-only`. Det laddar redan-skriven
parquet och validerar mot facit utan att köra om SQL.

### LB.16 — output_summary innehåller alla grupper, även icke-signifikanta
**Symptom:** Räknade rader i output_summary, fick 3812 (för cluster). Förväntade signifikanta.
**Regel:** output_summary har ALLA grupper. Signifikansflaggan är en kolumn (`significant_cluster`).
Filtrera på den om du vill se signifikanta.

### LB.17 — Site = department, inte clinic
**Symptom:** "Site" och "klinik" verkade utbytbara — men sökning på "Site = Bay Ridge" gav 0 rader.
**Rotorsak:** I pipelinens terminologi är Site = ID_Department-värdet. Klinik är affärsnamn.
**Regel:** `SiteCode` = `ID_Department`. Mappning till klinikenavn via `dbo.Dim_Department.ClinicName`.

### LB.18 — Bundle Hospital/Clinics rollup-grain
**Symptom:** Bundle:s `New_cluster` har bara Hospital/Clinics-värden, inte de 7 underklustrena.
**Regel:** Bundle aggregerar över de 7 till två huvudgrupper. När du jämför bundle-output med
cluster-output: olika grain, jämför inte direkt.

### LB.19 — Validera Spår A:s parquet, ej Spår B:s CSV
**Symptom:** `replicate_dataprep.py --validate-only` läser Spår A:s output, inte Spår B:s.
**Rotorsak:** replicate_dataprep läser `Sweden_Elasticity_Data_Prep_SQL\output\` (Spår A:s mapp).
Spår B:s CSV ligger i `Pipeline\02. Elasticity\2. Product Cluster Level Models\data\`.
**Regel:** Innan validering — verifiera att rätt fil läses. Se LB.29 för fullständig generalisering.

### LB.20 — data_prepration.py:s '2025-06-23' var hårdkodad
**Symptom:** G7-arbetet på constants.py var inte tillräckligt — pipelinen körde fortfarande på
2025-06-23 som slutdatum.
**Rotorsak:** En enskild rad (565) i data_prepration.py hade hårdkodat datum.
**Regel:** Vid G7-style parametrisering: grep efter ALLA datum-strängar i pipelinen, inte bara
constants.py. Ersätt med konstanten överallt.

### LB.21 — PowerShell execution policy blockerar .ps1
**Symptom:** `cannot be loaded because running scripts is disabled on this system`.
**Rotorsak:** Default execution policy är Restricted/AllSigned.
**Regel:** Leverera aldrig `.ps1`-scripts för Jens att köra. Använd kommandoblock i chat som han
copy-pastear in i PowerShell-fönster. KÄRNPRINCIPER §5.

### LB.22 — replicate_dataprep injicerar datum in-memory
**Symptom:** Trodde G7 krävde redigering av `01_process.sql` på disk — det gjorde det inte.
**Regel:** `replicate_dataprep.py._inject_dates()` rewriter SQL-strängen i minnet före exekvering.
SQL-filen på disk är oförändrad. Renare än att ha env-var i SQL-syntax.

### LB.23 — Verify_infra rapporterar STRAY-filer
**Symptom:** `.bak-g7`-filer flaggade som STRAY i verify_infra-output.
**Regel:** Lämna kvar tills G7-vägen körts färskt end-to-end (rollback-skydd). Städa efteråt med
`Remove-Item *.bak-g7 -Force`.

### LB.24 — Validera mot fryst original, ej arbetskopia
**Symptom:** verify_dataprep:s facit-fil var överskriven av en export_b4b-körning (P_CH-facit blev
header-only på 179 bytes 2026-05-25).
**Rotorsak:** Facit och export-output delade katalog → senare körning skrev över.
**Regel:** Validera ALLTID mot OneDrive-originalet (`BCG_orginal_V2_New`), aldrig mot
`Pipeline\...\data`-arbetskopian. Defaults i verify_dataprep pekar nu på originalet.

### LB.25 — corr 1.0 = misstänk cirkelbevis tills källoberoende
**Symptom:** verify_dataprep gav corr 1.000000 PASS — men jämförde inte rätt fil (LB.29).
**Rotorsak:** En "perfekt" siffra utan källoberoende kan vara: (a) genuint korrekt, (b) cirkelbevis
(jämför kopia mot sig själv), (c) fel fil jämförd som tystar diffen.
**Regel:** corr 1.0 → fråga "är källorna oberoende?" innan PASS godkänns. Verifiera sökvägar,
filstorlekar, encoding, kolumnantal — om någon skiljer sig är de inte kopior.

### LB.26 — py -3.11 för verify_tool, inte python
**Symptom:** `python verify_dataprep.py` startade Windows Store-alias som öppnade installations-
sida istället för att köra.
**Regel:** Använd alltid `py -3.11` för verify_tool. `python` är opålitlig på Windows pga Store-
alias. Pipelinens venv aktiveras med `.\.venv\Scripts\Activate.ps1` och då fungerar `python`.

### LB.27 — Aktiv venv ärver inte mellan PS-fönster
**Symptom:** En aktiverad venv i ett fönster syntes inte i ett annat.
**Regel:** Venv-aktivering är fönster-lokal. Aktivera i varje nytt PowerShell-fönster med
`.\.venv\Scripts\Activate.ps1`.

### LB.28 — Mät hash före fil-kopia mellan modeller
**Symptom:** Kopierade `constants.py` från cluster till site under G7-arbetet — site fungerade inte.
**Rotorsak:** Filerna ser lika ut men skiljer i `Bundle_code` / `Clusters`-granulärt kod längre ner.
Lika titel ≠ lika innehåll.
**Regel:** Före fil-kopia mellan modellfamiljer: `Get-FileHash <fil1> <fil2>` — verifiera identitet
INNAN du antar att en sak räcker för alla. Eller jämför med `diff` / `Compare-Object`.

### LB.29 — verify_tool jämför fel CSV om sökvägar divergerar
**Symptom:** `verify_dataprep.py` PASS:ade 100% (corr 1.000000, diff 0.000%) efter `export_b4b`-
körning — men jämförde inte `export_b4b`:s output, utan `replicate_dataprep.py`:s output i en helt
annan katalog med samma filnamn.
**Rotorsak:** Två oberoende vägar (Spår A: `replicate_dataprep`, Spår B: `export_b4b`) skriver filer
med samma namn (`0828_..._P_C.csv`) i olika kataloger. Verify-verktyget är hårdkodat för Spår A:s
sökväg. När man kör Spår B blir Spår A:s gamla fil (oförändrad sedan tidigare) jämförd istället —
PASS utan att Spår B faktiskt validerats.
**Regel:** Innan en validator körs på output från ett nytt script — verifiera att validatorn läser
från den katalog scriptet skriver till. Skriv ut full sökväg i validator-output ("loaded from
<path>"). Sökväg-divergens mellan output-skribent och validator är tyst (inga fel, bara fel
siffror jämförda). Generell version: MASTER_PYTHON L.43.

### LB.30 — Två venv:er, olika paket — använd rätt för rätt jobb
**Symptom:** `export_b4b_for_model.py` kraschade med `ModuleNotFoundError: No module named 'pyodbc'`
under `py -3.11` (global Python).
**Rotorsak:** verify_tool och pipelinen kräver olika Python-miljöer. Global 3.11 har duckdb (för
verify_tool); Business_Analytics venv har pyodbc (för DW-access). Inte ett paket-installations-fel —
fel interpreter för jobbet.
**Regel:** Innan körning, bekräfta vilken venv som har vilka paket. `pip show <paket>` mot varje
kandidat-interpreter är billigt. Installera aldrig "bara för säkerhets skull" — använd den venv som
redan har paketet. Konkret mappning:
- `export_b4b_for_model.py` / `compare_to_0828_facit.py` → `C:\Projekt\Business_Analytics\.venv`
- `verify_tool/*.py` → global Python 3.11 via `py -3.11`
- Pipelinens steg → `C:\Projekt\BCG\Pipeline\02. Elasticity\.venv`

### LB.31 — Tee-Object i PS 5.1 fångar inte stderr även med `2>&1`
**Symptom:** Pipeline-logg `step3_FULL_*.log` innehöll bara PowerShell:s eget felmeddelande om
Ray:s startup, inte Ray:s faktiska progress-rader (`(process_model_group pid=...) 762`) trots
`python feature_selection.py 2>&1 | Tee-Object -FilePath $log`. Progress-raderna syntes live i
terminalen men hamnade aldrig i loggfilen.
**Rotorsak:** `Tee-Object` i PowerShell 5.1 fångar bara stdout, inte stderr — även när stderr
omdirigerats till stdout med `2>&1`. Kvarvarande bug/begränsning i PS-versionen Jens kör.
**Regel:** För Python-körning där stderr-output måste loggas:
- På VM (bash): använd `python ... 2>&1 | tee logfile.txt` (fungerar korrekt).
- Lokalt PS 5.1: använd `Start-Transcript` eller `*>&1`-omdirigering, INTE `2>&1 | Tee-Object`.
  Eller skicka stderr separat: `python ... 2> stderr.log`.
Generell version (PS-vs-Python pipe-mekanik): `MASTER_PYTHON L.45`.

### LB.32 — Ray-OOM plateau ≠ återhämtning
**Symptom:** Efter `dlmalloc.cc:129 GetLastError=1450` följt av `Attempting to recover 25 lost
objects` såg dashboarden ut friskt: stabil RAM (9 GB ledigt), 16/16 python-processer kvar,
ingen ny OOM-event på 47 minuter. Tolkades som "Ray återhämtade sig långsamt, kör vidare".
Faktiskt: processen hängde — CPU-tid över alla workers växte med <10% av väntat per minut.
**Rotorsak:** Ray:s recovery-flöde kan låsa workers i väntan på resurser som aldrig blir
tillgängliga om systemet är på minneskanten. Stabil RAM + döda workers = "Ray gav upp", inte
"Ray jobbar långsamt". Snapshot-mätningar (RAM/process-count) ljuger; det är *förändringen* över
tid som avslöjar status.
**Regel:** Vid Ray-OOM med "Attempting to recover" — mät **CPU-tidens tillväxttakt** över workers.
Förväntat under faktisk körning: ~50-100% av en CPU-kärna per worker per minut. Om <10% i 5+
minuter = avbryt körningen, processen hänger. Snapshot av RAM/process-count räcker inte.

### LB.33 — Smoke-extrapolation underskattar Ray:s peak-RAM icke-linjärt
**Symptom:** Smoke 50 KEY av `feature_selection.py` lyckades lokalt med 13 GB RAM-headroom kvar.
Linjär extrapolation till full 1521 KEY antog ~3,4× större RAM-behov, vilket gav bedömningen
"85% sannolikhet att lyckas". Full körning OOM:ade i praktiken vid ~50%.
**Rotorsak:** Ray:s peak-RAM beror på antal **samtidigt aktiva workers med datakopia**, vilket
växer icke-linjärt med batch-volym. Smoke 50 KEY körde få samtidiga workers (datat fick plats i
worker-kvoten); 1521 KEY körde många workers parallellt → varje med en datakopia → peak-RAM
exploderar.
**Regel:** Pre-flight smoke är bra för "fungerar logiken?" men opålitlig för "klarar systemet
skalan?". För Ray-pipelines på vertikalt begränsad hårdvara: testa med 30-50% av målmängd, inte
3%. Eller acceptera att lokal körning är för riskabel och gå direkt till VM. Smoke-success bevisar
INTE skalans framgång — bara logikens.

### LB.34 — `/tmp/ray_spill` försvinner vid VM-omstart
**Symptom:** Skapade `/tmp/ray_spill` manuellt på `bcg-poc-vm`. Stoppade VM över natten via
`az vm deallocate`. Nästa morgon efter `az vm start`: mappen saknades. Pipeline skulle krascha
omedelbart vid Ray-start eftersom `feature_selection.py` config pekar på `/tmp/ray_spill`.
**Rotorsak:** Ubuntu Azure VM:s `/tmp` är inte persistent över deallocate→start-cykler — det är
en `tmpfs` (RAM-backad) eller städas vid omstart. `CZ.5`-fixen i koden (byte från `C:\ray_spill`
till `/tmp/ray_spill`) är path-byte, inte mkdir-fix; mappen måste finnas innan Ray startar.
**Regel:** Vid varje VM-session (efter `az vm start` från deallocated tillstånd): kör
`ssh azureuser@<ip> "mkdir -p /tmp/ray_spill"` innan pipeline startas. `check_env.ps1 -VmInner`
auto-fixar detta. Generell VM-version: `MASTER_AZURE_COMPUTE CZ.9`.

### LB.35 — Imports propageras inte automatiskt vid str_replace-patch
**Symptom:** Patchade `constants.py` på VM med `END_DATE2 = (datetime.strptime(END_DATE,
'%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')` via str_replace. Test-import kraschade
omedelbart: `NameError: name 'datetime' is not defined`.
**Rotorsak:** Ursprungsfilen hade inte `from datetime import datetime, timedelta`. Patchen lade
till **användning** av `datetime` utan att lägga till **importen**. Ren str_replace ser inte
sammanhanget och kan inte själv inferera att en ny modul behöver importeras.
**Regel:** Patches som introducerar nya beroenden måste **explicit lägga till imports** — eller
verifieras via `python -c "import <modul>"` direkt efter applikation. Pre-flight test-import är
5 sek arbete som sparar 50 min av "pipeline kraschar 50 min in i körningen p.g.a. saknad import".

### LB.36 — `data_prepration.py`:s "Shape"-print loggar input, inte output
**Symptom:** Loggraden `Data for model Shape: (523172, 33)` i steg 2:s utdata. Faktisk fil
`data_for_model.csv` skriven efter steg 2: **258,905 rader** (50% av loggat värde). Trodde först
att en CSV var trasig.
**Rotorsak:** Print-statementet i `data_prepration.py` är placerat **före** YOY-merge som droppar
L4-NULL-grupper. Loggar `df_raw.shape` (input till merge), inte `df_for_model.shape` (output efter
merge). Verkligt output är ~50% av loggat värde p.g.a. L4-NULL-dropp som BCG:s konsulter byggde
in i mergen.
**Regel:** Verifiera output-storlek mot **fil**, inte mot **loggrad**. `Get-Item file.csv | %{
$_.Length }` eller `pd.read_csv(file).shape` är sanning. Loggrader kan referera till mellansteg
även om det ser ut som slutsteg. R7-principen (utfall mot fil, inte loggrad) i pipeline-form.

### LB.37 — PowerShell multi-line-regex är opålitlig på Python-källkod
**Symptom:** Försökte patcha `check_env.py` via PowerShell `-replace` med multi-line regex för
att ändra `subprocess.run`-anrop i `check_azure`-funktionen. Två patches misslyckades med
"hittades inte exakt" trots verifierat korrekt sträng.
**Rotorsak:** PowerShell `-replace` använder .NET regex som default behandlar `.` som "vilken
char som helst utom newline". Multi-line strängar (Python-funktioner spänner flera rader)
matchar inte utan `(?s)`-flagga eller `[regex]::Singleline`. PowerShell-strängar dessutom
sköra på citat-escaping genom 3 lager (PS → ssh → bash → python).
**Regel:** För patches på Python-källkod — använd ett **Python-skript** kört från PowerShell,
inte direkt-PowerShell-regex. Python `str.replace()` är exakt strängmatchning, ingen
regex-tolkning. Eller `re.DOTALL`-flagga vid behov. Generell version: `MASTER_PYTHON L.44`.

---
### LB.38 — "Biter inte på kärnelasticiteten" ≠ harmless
**Symptom:** Vid FAS 3 och FAS 10 dokumenterades `Master_Underkategori3` som halv-NULL (IB.8 sade
"relevant för gruppering, inte för kärnelasticitet"). Detta minimerade konsekvensen. Resultatet
2026-06-05: 73 % av ItemCodes droppades faktiskt ur modellen — inklusive hela tjänstesidan.
**Rotorsak:** Pipeline-stegen *efter* regressionen (yoy_seasonality inner merge på `service`) droppar
hela KEY för rader med NULL pg4. Påståendet "påverkar inte regressionen" stämmer för de KEY:n som
överlever till regressionen — men förutsätter att de inte droppas av en upstream merge. Vi tittade
på regressionssteget isolerat och drog en allmän slutsats om hela pipelinen.
**Regel:** När en datakvalitetsbrist flaggas — fråga **"vid vilket pipeline-steg används denna
kolumn, med vilken merge-typ?"** innan slutsatsen "harmless". `pandas.merge(how="inner")` på
NULL-värden = total dropout (NaN matchar inte NaN). Spåra varje kolumns liv från källa till
regressionsinput. *(Princip: "mät, gissa inte", KÄRNPRINCIPER.)*

### LB.39 — Validering på producerade rader fångar inte populations-bortfall
**Symptom:** `verify_dataprep.py` rapporterade FR-1 PASS med corr=1.0 mot BCG:s 0828-facit i flera
sessioner före 2026-06-05. Detta dolde att 834 av 1151 ItemCodes droppades senare i pipelinen.
Verify-suiten var "grön" medan modellen exkluderade veterinärtjänster (huvudintäktskällan).
**Rotorsak:** Verify mäter "matchar de rader vi har" — inte "matchar vi alla rader vi *borde* ha".
Korrelation på en delmängd kan vara 1.0 medan delmängden själv är ofullständig. Klassisk
selektion-bias: vi validerar det vi producerade, inte det vi missade.
**Regel:** Varje pipeline-steg ska logga **ItemCode-count in vs ut**. Avvikelse > 1 % kräver
explicit förklaring. Verify-suiten bör inkludera **täckningsgrad-KPI**:
`vår_codes ∩ facit_codes / facit_codes`. Detta är komplement till befintliga
likhetsvalideringar — inte ersättning. Lade till `validate_extraction_coverage.py` 2026-06-07
som åtgärd: jämför vår ItemCode-count mot BCG-facitets, flaggar avvikelse > 0.5 %.

### LB.40 — `load_or_create_feature_control_file()` Gren B saknar `return`
**Symptom:** `feature_selection.py` (steg 3) kraschar med `AttributeError: 'NoneType' object has
no attribute 'melt'` på rad 504 (i `check_nulls()` rad 630). Inträffar bara på **första körningen**
efter att `control_file.xlsx` raderats.
**Rotorsak:** Funktionen `load_or_create_feature_control_file()` (rad 114-158 i BCG:s kod) har
två grenar: Gren A (rad 134-135) — filen finns → `return control_file` ✅; Gren B (rad 138-158) —
filen saknas → skapa, spara till disk → **glömmer `return`** ❌. Gren B faller igenom till
funktionens slut och returnerar `None` (Python-default). Den nyss skapade filen finns på disk men
returneras aldrig till anropssidan. Nästa rad 630 (`check_nulls(df_raw, control_file)`) tar emot
`None` och kraschar på första `df_control.melt(...)`.
**Regel:** Använd **Lösning A** vid problem: pipeline-skriptet körs om. Andra gången tas Gren A
(filen finns från första körningen) och funktionen returnerar korrekt. **Patcha inte BCG-koden**
(LF.3: BCG-original skrivskyddad). Workaround: om du behöver "rensa state" inför ny körning,
radera ALDRIG `control_file.xlsx` direkt — istället låt steg 2 köra normalt först (det skapar
inte filen), kör steg 3 första gången (Gren B skapar filen + kraschar — accepterat), kör steg 3
andra gången (Gren A returnerar — fungerar). Detta är `crash-recovery-mönster` — inte en bug-fix.
**Bekräftat på Site (2026-06-09):** Samma tvåpass-mönster gäller varje modellfamilj på nytt KEY-set — Site (6624 KEY) kraschade pass 1, kördes om, Gren A laddade control_file pass 2 och fortsatte. Regeln är familje-oberoende.

### LB.41 — `control_file.xlsx` regenereras INTE av steg 2 (`data_prepration.py`)
**Symptom:** Förväntade att rensa stale `control_file.xlsx` före VM-körning skulle automatiskt
regenerera den med ny KEY-population från steg 2. Den skapas istället först i steg 3.
**Rotorsak:** BCG:s pipeline har `control_file.xlsx` som **input till steg 3**, inte output från
steg 2. Steg 2 (`data_prepration.py`) producerar `data_for_model.csv` med 4180 KEY men skriver
ingen control-fil. Steg 3 (`feature_selection.py`) rad 158 är där control_file skapas (om den inte
finns) baserat på `data_for_model.csv`s `model_group`-kolumn.
**Regel:** Rensning av `control_file.xlsx` är säker före steg 3, inte före steg 2. Schema:
steg 1, 2: kör utan att röra control_file; steg 3 första körning: skapar `control_file.xlsx`
baserat på steg 2:s output (kombinerat med LB.40: kraschar på Gren B → kör om → Gren A fungerar);
steg 4: läser den färdiga control_file.

### LB.42 — Output_summary.xlsx ligger i `output/model/` (inte `output/`)
**Symptom:** `find ~/bcg/cluster -name 'output_summary.xlsx'` returnerar fil i fel mapp första
gången du letar. scp-kommandon som antar `output/output_summary.xlsx` får "No such file".
**Rotorsak:** BCG-pipelinens output-struktur är hierarkisk: `output/data/` (input om bearbetad),
`output/data_preparation/` (steg 2-artefakter), `output/regular_price/` med mellanslag på vissa
system (steg 1-output), `output/feature_selection/` (steg 3-artefakter), **`output/model/`** (steg
4 producerar `output_summary.xlsx`, `model_summary.xlsx`, `model_results.csv`), `output/model/automl/`
(feature-selection-mellanresultat), `output/model/model objects/` (sparade modellobjekt, mellanslag).
**Regel:** `output_summary.xlsx` ligger alltid i `~/bcg/<modellfamilj>/output/model/`. För scp:
`scp azureuser@vm:~/bcg/cluster/output/model/output_summary.xlsx $archive`. Verifiera med
`find ~/bcg/cluster -name 'output_summary*' -newer <referensfil>` om datum är osäkert (LB.43).

### LB.43 — `ls -la` mapp-datum kan misstolkas som fil-datum
**Symptom:** `ls -la output/model/` 2026-06-08 visade mapp `Jun 5 08:23` och fil `Jun 8 08:41`.
Vid snabb avläsning trodde jag att `output_summary.xlsx` var från 5 juni (gammal) tills jag läste
om — den var faktiskt 8 juni (ny).
**Rotorsak:** Första kolumnen efter rättigheter i `ls -la` är mapp-/fil-datum. När en mapp och
en fil listas tillsammans är det lätt att läsa fel rad. Mapp-datum är när **mappen senast
modifierades** (= ny fil skapades i den), inte när **innehåll modifierades senast**.
**Regel:** Använd `find -newer` för att hitta filer modifierade efter en referenspunkt:
`find ~/bcg -name 'output_summary*' -newer ~/bcg/cluster/code/control_files/control_file.xlsx`.
Detta filtrerar bort allt äldre och visar bara dagens. Säkrare än manuell datum-tolkning av
`ls -la`-output.

### LB.44 — Excel-efterbearbetningssteg (steg 5 + Step 6) körs LOKALT på Windows, aldrig på Linux-VM
**Symptom:** `data_prep_after_model_output.py` (steg 5) kraschar på VM med
`ModuleNotFoundError: No module named 'xlwings'` direkt vid `import xlwings` (rad 8), innan någon
logik körts. Samma fil i Cluster har identisk import.
**Rotorsak:** Steg 5 och `Fall_Back_Logic.py` (Step 6) använder xlwings med äkta Excel-COM-anrop
(`xw.App`, `wb.api.SaveAs(FileFormat=XLSB)`, `wb.api.RefreshAll()`). Detta kräver Windows +
installerad Excel — xlwings styr en faktisk Excel-instans via COM och **kan inte köras på Linux**,
oavsett om paketet installeras. Modellberäkningen (steg 1-4, Ray) hör hemma på VM:en; Excel-
efterbearbetningen hör hemma lokalt. Detta är en arkitektonisk gräns som gäller ALLA modellfamiljer.
**Regel:** Kör steg 1-4 på Azure-VM (tung Ray-beräkning), steg 5 + Step 6 lokalt på Windows.
För lokal steg 5-körning: `py -3.11` (har xlwings 0.33.20 + Excel finns). **Kör från modellfamiljens
ROT, inte från `code/`** — lokala `constants.py` har CWD-relativ config-sökväg (`.\code\src\config.yml`),
så `cd` till roten och kör `py -3.11 code\data_prep_after_model_output.py`. Sätt `BCG_START_DATE`/
`BCG_END_DATE` så datumfönstret matchar växande data. **Lokal raw-data-CSV (`data/0902_..._site_level.csv`)
MÅSTE vara den växande (180 MB), inte frusen (130 MB)** — annars blir joinen mot växande modelloutput
fel (R7-fälla, tyst). launcher.py inkluderar steg 5 i sekvensen — på VM kraschar det steget alltid,
vilket är väntat; modelloutputen (steg 4) är klar innan dess och hämtas hem för lokal steg 5-körning.

### LB.45 — `write_df_preserve_named_range` fångar `KeyError` men xlwings kastar `com_error`
**Symptom:** Steg 5 (`data_prep_after_model_output.py`) kraschar på rad 252/237 med
`pywintypes.com_error: (-2147352567, 'Undantag inträffade', ...)` när målmallen
(`Sweden_Sitecode_level_elasticity_summary.xlsx`) är tom/ny och saknar förväntade ark/namngivna områden.
**Rotorsak:** Funktionen `write_df_preserve_named_range` har en fallback: `try: wb.sheets[name]` /
`except KeyError: wb.sheets.add(...)` (och samma mönster för `wb.names[range]`). Avsikten är "använd
om finns, skapa annars". Men när arket/området saknas kastar xlwings ett `pywintypes.com_error` —
**inte** `KeyError` — så fallbacken (skapa) nås aldrig och felet bubblar upp. På BCG:s förformaterade
mall (där ark/områden redan finns) tas if-grenen och buggen syns aldrig; den triggas bara på en
tom/ny mall (t.ex. första körning på ny maskin).
**Regel:** Byt `except KeyError:` mot `except Exception:` (3 ställen i funktionen). Då fångas
COM-felet och fallbacken bygger ark/område från grunden → steg 5 blir självförsörjande, oberoende av
en förformaterad mall. Backup togs som `.bak-before-comfix`. *(Detta är en faktisk kod-fix i en
lokal arbetskopia, inte BCG-original — LF.3 gäller inte lokala körkopior.)*

### LB.46 — Azure CLI cachar aktiv subscription mellan sessioner (subscription-fällan)
**Symptom:** Ny dag, `az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm` ger
`AuthorizationFailed ... does not have authorization to perform action ... over scope`. Ser ut som
behörighetsförlust eller utgången token.
**Rotorsak:** `az` minns senast satta subscription mellan sessioner. Hade man jobbat i en annan
subscription emellan (t.ex. `ev-lz1-hybrid` för ProvetDiscount) sitter man kvar där. VM:en finns inte
i den subscriptionen → AuthorizationFailed. Det är INTE en utgången token och INTE behörighetsförlust
— bara fel aktiv subscription. (`MASTER_AZURE.md` anger `ev-lz1-hybrid` som default, vilket förvärrar
det för BCG-arbetet som bor i `ev-lz3-ai`.)
**Regel:** Kör alltid `az account show` FÖRE VM-kommandon (mät, gissa inte). VM:en bor i
subscription `ev-lz3-ai (SE)` (id `42f726f8-91ee-44d4-832f-9d9ec412ef8f`), RG
`ev-openai-swce-rg-test`. Sätt rätt subscription först: `az account set --subscription "ev-lz3-ai (SE)"`.

### LB.47 — scp av fjärrfil med mellanslag i sökväg: `cp` till ren sökväg på VM först
**Symptom:** `scp azureuser@vm:"'~/bcg/site/output/regular price/ivc_sweden_price.csv'" "$dest"`
ger `No such file or directory` trots att filen finns — mellanslaget i mappnamnet (`regular price`)
överlever inte genom PowerShell→scp→bash-citatlagren. Dessutom: `~` expanderas INTE inom enkla citat
i bash.
**Rotorsak:** Tre citat-tolkar (PowerShell, scp-argumentparser, fjärr-bash) ska enas om var
mellanslaget hör hemma, och `~` inom `'...'` förblir literal. Kombinationen är praktiskt taget
omöjlig att få rätt inline.
**Regel:** `cp` filen till en mellanslagsfri sökväg på VM:en först (med full sökväg, inte `~`), hämta
sedan därifrån:
```powershell
ssh azureuser@vm "cp '/home/azureuser/bcg/site/output/regular price/fil.csv' /home/azureuser/fil.csv"
scp azureuser@vm:/home/azureuser/fil.csv "C:\full\lokal\sökväg\fil.csv"
```
Samma kärnprincip som §10b/§11 i UBUNTU_AZURE_VM: undvik att tvinga komplexa sökvägar genom flera
citat-lager — bygg/flytta till en enkel sökväg först.

---

### LB.48 — läs *runnern* som producerade artefakten innan du deklarerar "datakedjan kräver patch X"
**Symptom:** F.9-inventeringen slog fast att Bundle-masterdatan behövde en G7-datumpatch i SQL för att bli
växande. Fel — `replicate_dataprep.py` (runnern som faktiskt producerar masterdatan) hade redan en komplett
G7-datuminjektor (`_inject_dates`/`_fiscal_year_flags`) som skriver om `YearFlag IN(...)` in-memory när
`BCG_END_DATE` är satt. Patchen vi planerade var redan löst en nivå upp.
**Rotorsak:** Antagandet byggde på att läsa SQL-filen isolerat, inte scriptet som kör SQL:en. SQL:en såg
hårdkodad ut, men runnern muterade den vid körning. Att läsa halva kedjan gav en falsk slutsats.
**Regel:** Innan du planerar en patch mot en datakedja — spåra artefakten bakåt till scriptet som
*faktiskt skapar* den och läs det helt. Patcha aldrig mot en mellanfil utan att veta vad som skriver den.
*(Drev hela F.9-omkalibreringen 2026-06-10; jfr KÄRNPRINCIPER search-before-build.)*

---

### LB.49 — masterdata CSV→parquet: läs med `all_varchar=true`, typning hör hemma hos konsumenten
**Symptom:** `read_csv_auto` kraschade vid CSV→parquet-konvertering — DuckDB:s sample-baserade typgissning
satte `ItemType` till BIGINT, men ett missformat citerat produktnamn (rad 654262) innehöll text → cast-fel
mitt i en 7 GB-fil.
**Rotorsak:** DuckDB samplar de första N raderna för typinferens och ser inte hela filen. En enda avvikande
rad långt ner spränger en typgissning som "såg rätt ut" i samplet.
**Regel:** Läs rå masterdata-CSV med `all_varchar=true` vid parquet-konvertering. Konsumenten (`00_read.sql`)
CASTar ändå allt till rätt typer — typning är dess ansvar, inte konverterarens. Noll radförlust, ingen
sample-krasch. Bekräftat: `diagnose_masterdata_csv.py` läste alla 27,4M rader med `all_varchar` utan bortfall.

---

### LB.50 — dubbel fönsterdefinition är en tyst-fel-fälla; ersätt med konstant-ankare utan övre gräns
**Symptom:** Bundle-SQL-output kapades tyst vid Jun 2025 trots att masterdatan var växande t.o.m. Jun 2026.
`verify_bundle_growing.py` → CAPPED, max_week 2025-06-30.
**Rotorsak:** Två oberoende steg filtrerade *samma* tidsfönster — masterdatans G7-injektor (växande) OCH
`01_process.sql` rad 20 med hårdkodad `YearFlag IN('...23','...24','...25')`. När bara det ena uppdaterades
divergerade de, och det snävare (SQL:ens whitelist) vann tyst utan fel eller varning.
**Regel:** När två steg filtrerar samma fönster är det ena redundant och en framtida tyst-fel-källa. Ta bort
det redundanta filtret; ersätt med konstant-ankare utan övre gräns: `CAST(week_starting_monday AS DATE) >=
DATE '2022-07-01'`. Då ärvs fönstret från källan, kan aldrig kapa tyst, och kräver ingen årlig redigering.
*(Patchad via `patch_bundle_yearflag.py`; jfr LF.2 konstant-ankare. Detta är en DRIFT-fälla: konfiguration
på två ställen som tyst glider isär.)*

---

### LB.51 — BCG-kod har UK-rester, tomma config-nycklar och aldrig-körda steg; verifiera config mot scriptets faktiska anrop före körning
**Symptom:** Bundle-Ray-varukorgsbygget (`2.Sweden_Bundle_Clinic_Model_Data_Creation.py`) skulle krascha med
KeyError: scriptet läser `config['model_data_creation']['sweden_bundles']`, men `config_data_prep.yml` har
nyckeln `uk_bundles`. Config pekade dessutom på frusna BCG-filnamn (`0826_*`/`0825_*`) som inte finns; `data/`
var tom; `build_bundle_for_type` förväntade en exploderad Bundle×ProductCode-input, inte den komma-separerade
`sweden_bundle_analysis.csv`; FTE-formatet var XLSX i kod men CSV i vår dataprep.
**Rotorsak:** Koden är UK-arv (variabler heter `uk_bundles`, `D:\IVC E Phase 1`-sökvägar i kommentarer),
aldrig körd på svenska sidan, config aldrig synkad med scriptets faktiska anrop. Den "ser körbar ut" men har
aldrig exekverats i vår kontext.
**Regel:** Innan du kör ett aldrig-testat BCG-steg: (1) `grep` scriptets `config[...]`-anrop och matcha varje
nyckel mot config-filen; (2) verifiera att varje input-sökväg pekar på en faktisk fil, inte ett fruset
BCG-original; (3) kontrollera format-antaganden (`read_excel` vs `read_csv`) och kolumnnamn mot vad uppströms
faktiskt producerar. Anta aldrig att BCG-kod är körklar — den är ofta UK-rester med död config.

---

### LB.52 — Step 6 förväntar pre-splittad KEY (ItemCode-kolumn); vår växande output har bara KEY
**Symptom:** `Fall_Back_Logic.py` rad 252 (`read_blended_model_data`) kraschade med `KeyError: 'ProductKey'`
på `dfcluster.merge(service_map, on=ProductKey)`. Cluster-läsaren renamar `{'ItemCode':'ProductKey'}` men
vår växande `output_summary.xlsx` har ingen `ItemCode`-kolumn — bara `KEY` (`Clinics 0-AAP115`).
**Rotorsak:** BCG:s facit-blended_model hade kolumnerna pre-splittade (`ItemCode` + `Cluster` separat),
medan vår rå modell-output bär `KEY` (samma format som Site/Bundle). `read_blended_model_data` saknar den
KEY-extraktion som `reading_site_level_data` och `reading_bundle_cluster_level_data` redan har — för facit
behövde den inte den. En strukturskillnad mellan facit och växande output, inte ett datafel.
**Regel:** När du matar växande modell-output till ett BCG-steg som förväntar facit-struktur: splitta `KEY`
→ `Cluster` + `ItemCode` i runnern (`rsplit('-', n=1)` — klusternamn har mellanslag men inga bindestreck,
ItemCode har inga bindestreck, så sista bindestrecket är rätt separator; matchar `extract_cluster_from_key`).
Lägg anpassningen i runnern, inte i BCG-koden — då förblir `Fall_Back_Logic.py` orörd och facit-jämförbar.

---

### LB.53 — xlwings `wb.names[range]` kraschar (com_error) om mallens namnområde saknas; datan är redan sparad
**Symptom:** Step 6 kraschade på sista raden (rad 691, `write_df_preserve_named_range`) med
`pywintypes.com_error` på `wb.names[named_range].refers_to = ...`. Mallen `Excel_Outputs\Sweden_Fallback.xlsx`
saknar det namngivna området `raw` som koden försöker resiza.
**Rotorsak:** `wb.names[named_range]` antar att namnområdet finns; gör det inte kastar Excel-COM ett generiskt
undantag. Detta är sista steget (uppdaterar BCG:s pivot-dashboard), EFTER att `Final_Fallback_Data.xlsx` +
den timestampade kopian redan skrivits (rad 671/686). Datan går alltså inte förlorad — bara dashboard-
kosmetiken fallerar. (Samma COM-klass som LB.45.)
**Regel:** (1) Behandla mall-/named-range-skrivning som kosmetiskt sista steg — verifiera output via den
fristående `Final_Fallback_Data*.xlsx` (R7: lita på filen, inte på att hela scriptet exitar 0). (2) Gör
namnområdes-skrivning defensiv: `try: wb.names[nr] except KeyError/com_error: wb.names.add(nr, ...)` — skapa
om det saknas istället för att krascha. (3) En icke-noll exit betyder inte att datan saknas; kontrollera
vad som skrevs före kraschpunkten.

---

### LB.54 — SSH-detach: ett efterföljande `&` räcker inte; processen måste äga sina egna fd:er (launcher.sh + setsid)
**Symptom:** Orchestratorn startade modellkörningen på VM:en med
`setsid bash -c '<cmd> > log 2>&1' </dev/null >/dev/null 2>&1 &` via `ssh`. SSH-anropet **hängde 30 s
och timeoutade** trots att jobbet de facto startade. Andra försöket (samma session) timeoutade på
samma sätt.
**Rotorsak:** SSH väntar inte på att kommandot ska *bli klart* — det väntar på att **kanalen** ska
stängas. Ett efterföljande `&` backgrundar jobbet i bash, men de subprocesser `setsid` startar (Python,
och i synnerhet Rays många workers) ärver/håller filhandtag knutna till SSH-kanalen öppna. Så länge
någon descendant håller kanalen öppen returnerar inte SSH — även om det yttre kommandot omdirigerats.
**Regel:** Frikoppla i två led, så att den körande processen aldrig håller ett fd på SSH-kanalen:
(1) skriv ett litet launcher-skript **på VM:en** som äger sin egen `> log 2>&1`-omdirigering;
(2) starta det med `setsid <script> </dev/null >/dev/null 2>&1 &` och låt SSH-kommandot returnera via
ett omedelbart `echo started`. Verifiera mekaniken **isolerat** (`sleep 90`-test: mät att SSH släpper
<15 s och att processen lever via `pgrep`) innan en lång körning litar på den. Bevisat: släpptiden gick
från 30 s timeout → 1,4 s. (Implementerat i `azure_vm.py::ssh_launch_detached` + `ssh_launch_selftest`.)

### LB.55 — VPN-tunneln till VM:en är intermittent; en missad observation får ALDRIG döda en frikopplad körning
**Symptom:** ~2 h in i en site-körning hängde en trivial `tail`-poll i 90 s och orchestratorn behandlade
det som pipelinefel → deallokerade VM:en → dödade en helt frisk körning på mållinjen. (Samma
tunnel-egenhet dokumenterad interaktivt i FAS 13: `hostname` gav tomt svar, `cp` hängde, medan
`az` bekräftade `VM running`.)
**Rotorsak:** Två sammanblandade begrepp: *observation* (kan vi se körningen?) och *körningens hälsa*
(lever jobbet?). Jobbet är `setsid`-frikopplat och självförsörjande — det påverkas inte av om vår
SSH-observation blinkar. VPN-tunneln till privata IP:n (`172.18.148.4`) är känd flaky; en hängd poll =
observationsförlust, inte pipelinefel.
**Regel:** (1) `ssh_run` sätter `ServerAliveInterval=10 ServerAliveCountMax=3` (död tunnel
självavslutar ~30 s i stället för att hänga till subprocess-timeout) och har retry; en upprepad
timeout/`ssh exit 255` kastas som egen `SshUnreachable`, ej generiskt fel. (2) Pollen klassar utfall i
tre lägen: `success` (färsk output), `pipeline_dead` (process borta OCH ingen färsk output OCH
`az`-power-state bekräftar VM nere), `lost` (kunde inte observera). (3) **Deallokera bara vid
bekräftat utfall.** Vid observationsförlust: lämna VM:en körande, skriv återhämtningsväg i statusfilen,
låt jobbet gå klart. (4) `az` är sanningsvittnet out-of-band — det går utanför tunneln (bekräftat live:
retryn svalde en skarp tunnelglapp 17:17 utan att döda körningen). (Implementerat i
`azure_vm.py` + `run_site_model.py::poll_until_done`/`_leave_running`/`--attach`.)

### LB.56 — Deallokera utfallsstyrt, inte i blint `finally`; och fånga Ctrl+C så det inte dödar VM-jobbet
**Symptom:** Ett `finally: deallocate_vm()` deallokerade VM:en oavsett varför funktionen lämnades —
inklusive vid observationsförlust (LB.55) och vid ett reflexmässigt lokalt Ctrl+C. En frisk,
frikopplad körning kan då dödas av en lokal händelse som inte har med jobbet att göra.
**Rotorsak:** `finally` skiljer inte på *hur* vi lämnade. Det frikopplade jobbet på VM:en överlever
att den lokala runnern dör — men inte att VM:en deallokeras.
**Regel:** Deallokera endast vid bekräftade utfall (`success` / `pipeline_dead`). Fånga
`KeyboardInterrupt` och `SshUnreachable` separat → `_leave_running` (lämna VM:en, skriv re-attach-väg).
Tillhandahåll ett `--attach`-läge som återansluter till en pågående körning: hitta nyaste run-loggen på
VM:en, återskapa starttiden från launcher-skriptets mtime, polla klart, hämta, deallokera. Detta är
priset värt: ett värsta-fall lämnar VM:en igång (~9 kr/h) tills manuell deallokering — men alternativet
(döda en frisk körning) kostade en hel körning. Runnern skriker tydligt om valet när det sker.
> **Skyddsnät (FD.16):** en VM-sidig auto-shutdown (t.ex. `shutdown -h +240` vid launch, eller
> Azure auto-shutdown-policy) ska deallokera även om allt lokalt dör. Tas in som FD-post.

### LB.57 — `az` är `az.cmd` på Windows → `subprocess` måste köra det via `shell=True`-sträng, inte list-args
**Symptom:** `subprocess.run(["az", "vm", ...])` gav `FileNotFoundError: [WinError 2]` trots att `az`
fungerar i PowerShell.
**Rotorsak:** `az` är inte en `.exe` utan en batch-wrapper (`az.cmd`). `subprocess` med list-args söker
en körbar med exakt namnet `az` och hittar ingen. `ssh`/`scp` är däremot riktiga `.exe` → list-args
fungerar för dem.
**Regel:** Kör `az` som `subprocess.run(f"az {cmd}", shell=True, ...)` (argumenten är våra egna
konstanter, ingen otrustad input → injektionsrisk ej relevant). Kör `ssh`/`scp` med list-args (undviker
PowerShell-quoting helt eftersom vi aldrig går via PS). (Implementerat i `azure_vm.py::_az` vs
`ssh_run`/`scp_from_vm`.)

### LB.58 — DW når inte från Azure-VM:en (IP-vitlistning); extraktionen förblir ett lokalt försteg → Blob → VM
**Symptom:** Frågan "kan hela kedjan inkl. DW-extraktion köras via Azure?" Mätt med ett ofarligt
TCP-test från VM:en: `/dev/tcp/se-az-we-bi-sql-01.../1433` → **`BLOCKED`**, medan
`/dev/tcp/github.com/443` → **`OUT_OK`**.
**Rotorsak:** DW-brandväggen är IP-vitlistad till kontorsnät + VPN-poolen (därför behöver Jens VPN
hemifrån men inte på kontoret). VM:en sitter i Azure-VNet:et `ev-lz3-ai` — varken kontorsnät eller
VPN — så dess IP avvisas. `OUT_OK` bekräftar att det är DW-brandväggen specifikt, inte en bredare
egress-spärr. Detta är ett medvetet säkerhetsbeslut av Evidensia, inte ett hinder att kringgå.
**Regel:** DW-extraktionen + parquet-regenereringen körs **lokalt** (på behörig maskin på
kontorsnät/VPN, där `export_b4b_for_model.py` redan fungerar). "End-to-end via Azure" betyder därför:
extraktion lokalt → leverera data till VM via **Blob** (som VM:en når, `OUT_OK`) → tunga modellsteg på
VM → Excel-steg lokalt (xlwings, LB.44). Att flytta DW till Azure skulle kräva att IT öppnar
DW-brandväggen för VM:ens VNet eller VNet-peering — IT-beslut, sista utväg. Alternativen 3+4 (lokal
extraktion → Blob → VM) uttömmer icke-IT-vägarna. (Mätt 2026-06-12; arkitektur i NEXT_SESSION + FD.17.)

---

## Hur listan växer

Ny lärdom läggs till när vi snubblar över en teknisk fälla — miljö, infrastruktur, kod-mekanik,
sökväg-divergens. En befintlig lärdom **uppdateras** med "ändrad 2026-XX-XX" om regeln behöver
revideras (men vi tar inte bort den för att inte tappa historik).

Vid sessionsstart: läs lärdomarna som täcker dagens arbete (inte alla). Vid sessionsslut: överväg
om sessionen gav en ny LB. Om lärdomen är generell över projekt — befordra till MASTER_PYTHON eller
MASTER_SQL och låt LB peka dit.

---

*Skapad 2026-05-23 vid dokumentstruktur-omtaget; extraherad ur SESSION_*-filer. LB.29-30 tillagda
2026-05-29 efter session där verify_tool-fällan och venv-divergensen upptäcktes och dokumenterades.
LB.31-37 tillagda 2026-06-02 efter sessionen där full lokal cluster-körning OOM:ade, VM
förbereddes, och check_env-verktyget byggdes (commits `74f1ab0` + `ef258e5`). LB.38-43 tillagda 2026-06-08 efter VM-körning av cluster pipeline med pg4-fix. LB.44-47 tillagda 2026-06-10 efter F.8 Site körd end-to-end på växande data (steg 1-4 VM, steg 5 lokalt): Excel-stegen körs lokalt (LB.44), write_df_preserve_named_range com_error-fix (LB.45), Azure subscription-fällan (LB.46), scp mellanslags-sökväg (LB.47). LB.40 bekräftad familje-oberoende på Site — 4180 KEY producerade inklusive AAP130 med elasticitet -0.52 p=0.001 (end-to-end-bevis kommiterad i `7e0f11f`..`89b9467`). LB.48-51 tillagda 2026-06-11 efter F.9 Bundle-dataprep körd växande + Bundle-modellen datadrivet parkerad (FD.11): läs runnern före patch-deklaration (LB.48), all_varchar vid masterdata-parquet-konvertering (LB.49), dubbel-fönster-fällan/konstant-ankare (LB.50, DRIFT), BCG-kod UK-rester + config-verifiering före körning (LB.51). Bundle-dataprep committad i `1daf093`. LB.52-53 tillagda 2026-06-11 efter F.10 Step 6 körd första gången på växande data (Alternativ A): KEY-split-fällan i blended_model (LB.52), xlwings named-range com_error på mall-skrivning (LB.53). Step 6 producerade 108 979 rader / 15 128 ProductKeys, median final_elasticity -0.497, 100% negativa.* LB.54-58 tillagda 2026-06-12 (Phase Z, FAS A-start) efter att site-modellsteget körts end-to-end via en Azure-orchestrator och validerats bit-för-bit mot 2026-06-09-facit (6624 KEY, korr 1.000000, max_abs_diff 0): SSH-detach via launcher.sh+setsid (LB.54), VPN-tunneltolerans/observationsförlust≠pipelinefel (LB.55), utfallsstyrd deallokering + --attach + Ctrl+C-skydd (LB.56), az.cmd kräver shell=True (LB.57), DW når ej från VM → extraktion lokal→Blob→VM (LB.58, mätt). Orchestratorn (`orchestration/`) tål tre felmoder bevisat live: seg kallstart (CZ.6-retry), detach-bugg (LB.54), skarp tunnelglapp (LB.55).*
