# LESSONS_BCG — Tekniska lärdomar, BCG Pricing-projektet

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde — replikering, validering, migrering)
**Lever i:** `C:\Projekt\BCG` (detta repo). Helt skild från Business_Analytics `PROJECT_LESSONS.md`.
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Senast uppdaterad:** 2026-05-29

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
2026-05-29 efter session där verify_tool-fällan och venv-divergensen upptäcktes och dokumenterades.*
