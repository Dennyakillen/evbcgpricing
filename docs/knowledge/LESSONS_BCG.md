# LESSONS_BCG â€” Tekniska lÃ¤rdomar, BCG Pricing-projektet

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflÃ¶de â€” replikering, validering, migrering)
**Lever i:** `C:\Projekt\BCG` (detta repo). Helt skild frÃ¥n Business_Analytics `PROJECT_LESSONS.md`.
**Utvecklare:** Jens PalmÃ¶ (Senior Business Analyst)
**Senast uppdaterad:** 2026-06-13 (tier-kolumn + `GÃ¤ller om`/`FÃ¶rkroppsligas i` infÃ¶rda; LB.59-61 infogade)

---

## Vad detta dokument Ã¤r (och inte Ã¤r)

`LESSONS_BCG.md` hÃ¥ller **tekniska lÃ¤rdomar** â€” fÃ¤llor i miljÃ¶, infrastruktur, kod-mekanik, validerings-
plattform, replikeringsdetaljer. Varje lÃ¤rdom har ett stabilt `LB.N`-ID och formatet:

```
**Symptom:** Vad som syntes.
**Rotorsak:** VarfÃ¶r det hÃ¤nde (om ej uppenbart).
**Regel:** Konkret Ã¥tgÃ¤rd som fÃ¶rhindrar upprepning.
**GÃ¤ller om:** Villkoret regeln vilar pÃ¥ (deaktiverar sig sjÃ¤lv nÃ¤r villkoret bryts). Skrivs bara
               nÃ¤r villkoret Ã¤r icke-uppenbart och kan brytas â€” pÃ¥ en tidlÃ¶s mekanism Ã¤r det Ã¶verflÃ¶digt.
**FÃ¶rkroppsligas i:** Fil(er) dÃ¤r regeln lever i kod (tvÃ¥vÃ¤gs-lÃ¤nkning â€” KÃ„RNPRINCIPER Â§4.6). Skrivs
                      nÃ¤r en konkret artefakt bÃ¤r lÃ¤rdomen, sÃ¥ att den som Ã¶ppnar filen hittar lÃ¤rdomen
                      och vice versa.
```

**Tier (styr vad som lÃ¤ses vid sessionsstart â€” se snabbindexet):**
- **(a) Aktiv fÃ¤lla** â€” kan Ã¤nnu bita pÃ¥ nÃ¤sta kÃ¶rning. LÃ¤s vid sessionsstart.
- **(b) LÃ¶st-av-verktyg** â€” ett verktyg/skript bÃ¤r numera regeln; behÃ¶ver inte lÃ¤sas (verktyget kÃ¶r den).
- **(c) Fas-historisk** â€” hÃ¶rde till en avslutad fas (t.ex. replikeringen); arkiv, inte aktiv lÃ¤sning.

Sessionsstart lÃ¤ser **bara (a)**. Detta hÃ¥ller listan frÃ¥n att tyst bli "skumma 53 poster". En lÃ¤rdom
nedgraderas frÃ¥n (a) nÃ¤r dess fÃ¤lla stÃ¤ngts av ett verktyg eller en fas â€” inte raderas (additiv fÃ¶r
historik, KÃ„RNPRINCIPER Â§4.7), bara om-tierad.

**Detta Ã¤r inte:**
- **AffÃ¤rs-/domÃ¤ninsikter** (vad vi lÃ¤rt oss om modellen/datan) â†’ `INSIGHTS_BCG.md` (`IB.N`).
- **Beslut** (vad vi valde och varfÃ¶r) â†’ `BCG_PRICING_PLAYBOOK.md` decision log (`D*`, `D-B*`, `D-F-*`).
- **Generella tekniska lÃ¤rdomar** Ã¶ver alla projekt â†’ `MASTER_PYTHON.md`, `MASTER_SQL.md`, `KÃ„RNPRINCIPER.md`.
  Om en LB-lÃ¤rdom blir generell, befordra den och lÃ¥t LB peka dit. Flera LB Ã¤r instanser av en
  KÃ„RNPRINCIP (markerat i index) â€” de stannar hÃ¤r som konkreta exempel, men regeln bor i KÃ„RN.

---

## Snabbindex

**Tier:** (a) aktiv fÃ¤lla â€” lÃ¤s vid sessionsstart Â· (b) lÃ¶st-av-verktyg â€” verktyget bÃ¤r regeln Â· (c) fas-historisk â€” arkiv.

| ID | Tier | LÃ¤rdom | Aktiveras |
|---|---|---|---|
| LB.1 | a | DW-token-renewal var 4:e timme | DW-query kraschar med ClientAuthenticationError |
| LB.2 | b | DuckDB .exe blockerad av AppLocker | duckdb.exe fÃ¥r inte kÃ¶ra |
| LB.3 | c | Lokal OOM pÃ¥ Stage 2 | feature_selection.py OOM pÃ¥ full pipeline lokalt |
| LB.4 | b | Ray-memory fix i config.yml | Stage 2 kraschar med memory error |
| LB.5 | c | BCG:s rÃ¥-signifikans = 17.8% (cluster) | BedÃ¶m aldrig vÃ¥rt mot absolut "borde vara sig" |
| LB.6 | b | Verify-tool krÃ¤ver global Python 3.11 | duckdb saknas i .venv |
| LB.7 | c | feature_selection driver Ray-workers | RayActorError vid OOM |
| LB.8 | c | Bundle.bundle_code = composite key | Bundle.bundle_code Ã¤r komma-separerad lista |
| LB.9 | c | Prisstabila grupper ger absurda elasticiteter | Site har koefficienter Â±200 |
| LB.10 | b | Encoding-mismatch BCG-input vs UTF-8 | Latin-1/CP1252 i BCG-filer |
| LB.11 | c | Verify_blend krÃ¤ver per-rep-test, ej summa | 43 representanter, inte total |
| LB.12 | a | output_summary.xlsx KEY-format | Cluster-Granularity+'-'+ItemCode |
| LB.13 | c | Cluster-seed har 7 namnade kluster | Inte 0..6 numreriskt |
| LB.14 | a | FTE-XLSX-tÃ¤ckning slutar 2025-06 | FÃ¤rska veckor fÃ¥r NULL |
| LB.15 | b | replicate_dataprep.py krÃ¤ver --validate-only | Annars 12 min SQL-omkÃ¶rning |
| LB.16 | c | output_summary innehÃ¥ller bara signifikanta? Nej | Alla 3812 cluster-grupper finns |
| LB.17 | c | Site = department, inte clinic | ID_Department i pipelinens kontext |
| LB.18 | c | Bundle Hospital/Clinics rollup-grain | Bundle skÃ¤r Ã¶ver kluster |
| LB.19 | b | Validera SpÃ¥r A:s parquet, ej SpÃ¥r B:s CSV | replicate_dataprep lÃ¤ser fel kÃ¤lla annars |
| LB.20 | a | data_prepration.py:s '2025-06-23' var hÃ¥rdkodad | G7-fix nÃ¶dvÃ¤ndig (instans: KÃ„RN P.3) |
| LB.21 | a | PowerShell execution policy blockerar .ps1 | AnvÃ¤nd kommandoblock, inte .ps1 |
| LB.22 | b | replicate_dataprep injicerar datum in-memory | SQL-filen pÃ¥ disk ofÃ¶rÃ¤ndrad |
| LB.23 | b | Verify_infra rapporterar STRAY-filer | .bak-g7 flaggas som STRAY |
| LB.24 | a | Validera mot fryst original, ej arbetskopia | Pipeline\data\ skrivs Ã¶ver av SpÃ¥r B |
| LB.25 | a | corr 1.0 = misstÃ¤nk cirkelbevis tills kÃ¤lloberoende | "SnÃ¤lla siffror" Ã¤r inte verifiering |
| LB.26 | a | py -3.11 fÃ¶r verify_tool, inte python | Windows Store-alias Ã¤r en fÃ¤lla (instans: miljÃ¶disciplin) |
| LB.27 | a | Aktiv venv Ã¤rver inte mellan PS-fÃ¶nster | Aktivera i varje nytt fÃ¶nster (instans: miljÃ¶disciplin) |
| LB.28 | a | MÃ¤t hash fÃ¶re fil-kopia mellan modeller | constants.py skiljer sig |
| LB.29 | a | verify_tool jÃ¤mfÃ¶r fel CSV om sÃ¶kvÃ¤gar divergerar | TvÃ¥ script skriver samma filnamn i olika kataloger |
| LB.30 | a | TvÃ¥ venv:er, olika paket â€” anvÃ¤nd rÃ¤tt fÃ¶r rÃ¤tt jobb | ModuleNotFoundError trots installerad miljÃ¶ (instans: miljÃ¶disciplin) |
| LB.31 | a | Tee-Object i PS 5.1 fÃ¥ngar inte stderr Ã¤ven med `2>&1` | Pipeline-progress saknas i loggfilen, syns bara i terminal |
| LB.32 | b | Ray-OOM plateau â‰  Ã¥terhÃ¤mtning, mÃ¤t CPU-tidens tillvÃ¤xttakt | Stabil RAM tolkas som "Ray jobbar" men Ã¤r "Ray gav upp" (instans: KÃ„RN P.2) |
| LB.33 | b | Smoke-extrapolation underskattar Ray:s peak-RAM icke-linjÃ¤rt | Smoke 50 KEY ok â†’ full 1521 KEY OOM:ar |
| LB.34 | b | `/tmp/ray_spill` fÃ¶rsvinner vid VM-omstart, mÃ¥ste skapas vid varje session | Pipeline kraschar vid Ray-start pÃ¥ "ny" VM (= MASTER_AZURE CZ.9) |
| LB.35 | a | Imports propageras inte automatiskt vid str_replace-patch. **Ankar-regel:** matcha MINSTA UNIKA ENRADSSTRÃ„NG, aldrig flerradsblock â€” CRLF + indentering (8-vs-4 space) + mellanrader sprÃ¤cker flerrads-matchning (missade samma fix 3 ggr 2026-06-22 tills enradsankare) | NameError efter "lyckad" patch; ELLER str_replace traffar=0 pÃ¥ flerrads-ankare |
| LB.36 | a | `data_prepration.py`:s "Shape"-print loggar input, inte output (~50% diff) | Loggrad 523k rader, faktisk fil 259k rader (instans: R7) |
| LB.37 | a | PowerShell multi-line-regex opÃ¥litlig pÃ¥ Python-kÃ¤llkod, anvÃ¤nd Python sjÃ¤lv | `-replace` matchar inte Ã¶ver newlines utan `(?s)`-flagga |
| LB.38 | a | "Biter inte pÃ¥ kÃ¤rnelasticiteten" â‰  harmless | Datakvalitetsbrist minimerades, ledde till 73% bortfall (instans: KÃ„RN P.1) |
| LB.39 | a | Validering pÃ¥ producerade rader fÃ¥ngar inte populations-bortfall | verify_dataprep PASS dolde 834 droppade ItemCodes (instans: KÃ„RN P.1) |
| LB.40 | a | load_or_create_feature_control_file Gren B saknar return (BCG-bug) | feature_selection kraschar AttributeError NoneType, kringgÃ¥s via kÃ¶rningsordning |
| LB.41 | a | control_file.xlsx regenereras INTE av steg 2 | Skapas fÃ¶rst i steg 3, rensning fÃ¶re steg 2 skapar inte ny fil |
| LB.42 | a | output_summary.xlsx ligger i `output/model/` (inte `output/`) | scp-kommandon med fel path fÃ¥r "No such file" |
| LB.43 | a | `ls -la` mapp-datum kan misstolkas som fil-datum | AnvÃ¤nd `find -newer` istÃ¤llet fÃ¶r att lÃ¤sa ls-output (instans: R7) |
| LB.44 | a | Excel-steg (5 + Step 6) kÃ¶rs LOKALT pÃ¥ Windows, aldrig pÃ¥ VM | xlwings/COM kan ej kÃ¶ra pÃ¥ Linux |
| LB.45 | a | `write_df_preserve_named_range` fÃ¥ngar `KeyError` men xlwings kastar `com_error` | Skrivning till blank mall kraschar |
| LB.46 | a | Azure CLI cachar aktiv subscription mellan sessioner | `AuthorizationFailed` pÃ¥ VM i fel subscription (= MASTER_AZURE-regel) |
| LB.47 | a | scp av fjÃ¤rrfil med mellanslag: `cp` till ren sÃ¶kvÃ¤g pÃ¥ VM fÃ¶rst | scp misslyckas pÃ¥ path med blanksteg |
| LB.48 | a | lÃ¤s *runnern* som producerade artefakten innan "datakedjan krÃ¤ver patch X" | Hypotes om datakedja innan kÃ¤llÃ¤sning (instans: KÃ„RN A.9b) |
| LB.49 | a | masterdata CSVâ†’parquet: lÃ¤s med `all_varchar=true`, typning hos konsumenten | DECIMAL-inferens kraschar pÃ¥ blandade typer |
| LB.50 | a | dubbel fÃ¶nsterdefinition Ã¤r tyst-fel-fÃ¤lla; ersÃ¤tt med konstant-ankare utan Ã¶vre grÃ¤ns | FÃ¶nster pÃ¥ tvÃ¥ stÃ¤llen glider isÃ¤r (instans: KÃ„RN P.3) |
| LB.51 | a | BCG-kod har UK-rester, tomma config-nycklar, aldrig-kÃ¶rda steg; verifiera config mot faktiska anrop | Config-nyckel utan effekt vilseleder |
| LB.52 | a | Step 6 fÃ¶rvÃ¤ntar pre-splittad KEY (ItemCode-kolumn); vÃ¥r vÃ¤xande output har bara KEY | KeyError pÃ¥ ProductKey nedstrÃ¶ms |
| LB.53 | a | xlwings `wb.names[range]` kraschar (com_error) om mallens namnomrÃ¥de saknas; datan redan sparad | Icke-noll exit men filen skrevs (instans: R7) |
| LB.54 | a | SSH-detach: `&` rÃ¤cker inte, processen mÃ¥ste Ã¤ga egna fd:er (launcher.sh + setsid) | Detached jobb dÃ¶r nÃ¤r SSH stÃ¤ngs (= MASTER_AZURE AZ.6) |
| LB.55 | a | Flaky VPN-tunnel mitt i kÃ¶rning fÃ¥r inte tolkas som kÃ¶rningsfel | Poll-avbrott svalt av retry, jobbet Ã¶verlevde (instans: KÃ„RN P.2 / AZ.7) |
| LB.56 | a | Deallokera utfallsstyrt, inte i blint `finally` | Avbruten kÃ¶rning slÃ¤nger VM man ville inspektera (= MASTER_AZURE AZ.8) |
| LB.57 | b | Prefect fÃ¶rkastat fÃ¶r denna miljÃ¶ (dashboard nÃ¥r ej kollega utan publik IP) | Ã–vervÃ¤gande av orkestreringsramverk |
| LB.58 | a | DW nÃ¥r INTE frÃ¥n VM:en (IP-vitlistning) â†’ lokal extraktion â†’ Blob â†’ VM | DW-query frÃ¥n VM ger BLOCKED (= MASTER_AZURE AZ.10) |
| LB.59 | a | run_id = datum ger statusfil-kollage vid flera kÃ¶rningar samma dag | StatusfÃ¤lt motsÃ¤ger varandra (finished fÃ¶re heartbeat) |
| LB.60 | a | deallocate-i-logg Ã¤r inte bevis pÃ¥ att VM:en Ã¤r nere â€” verifiera power-state | Loggrad "deallocated" men VM running (instans: R7 / KÃ„RN P.2) |
| LB.61 | a | Flask serverar mall frÃ¥n disk, men webblÃ¤saren cachar | Ã„ndrad dashboard.html syns inte i browser |

---

## LÃ¤rdomar

### LB.1 â€” DW-token-renewal var 4:e timme
**Symptom:** `ClientAuthenticationError: AADSTS70043: The refresh token has expired`.
**Rotorsak:** Evidensias Conditional Access tvingar refresh var 4:e timme.
**Regel:** Innan varje DW-query-pass: `az login --scope https://database.windows.net/.default`.
FÃ¶r lÃ¤ngre sessioner â€” renew vid tecken pÃ¥ timeout, inte vÃ¤nta pÃ¥ fel.

### LB.2 â€” DuckDB .exe blockerad av AppLocker
**Symptom:** `Access is denied` nÃ¤r duckdb.exe kÃ¶rs.
**Rotorsak:** IT-policy blockerar direkt .exe-kÃ¶rning.
**Regel:** AnvÃ¤nd `duckdb` Python-paketet, inte .exe-binÃ¤ren. FÃ¶r `01_clean.sql`: importera duckdb
i Python-wrapper, kÃ¶r SQL via API:t.

### LB.3 â€” Lokal OOM pÃ¥ Stage 2
**Symptom:** Stage 2 (feature_selection) kraschar med MemoryError pÃ¥ Jens 31 GB-maskin pÃ¥ BCG:s
fulla fÃ¶nster.
**Rotorsak:** Kombinatorisk feature-val Ã— Ray-parallelisering Ã— full population (19,344 koder)
sprÃ¤nger lokalt RAM.
**Regel:** FÃ¶r FAS V â€” kÃ¶r Stage 2 pÃ¥ Azure VM (`Standard_E16s_v5`, 128 GB). FÃ¶r FAS F med facit-pairs
(1151 koder) â€” testa lokalt fÃ¶rst, kan rymmas.

### LB.4 â€” Ray-memory fix i config.yml
**Symptom:** Stage 2 kraschar med "Ray cluster out of memory" tidigt i kÃ¶rningen.
**Regel:** `config.yml` â†’ `ray: memory: 8` och `cpus: 12`. Detta Ã¤r config-fix, ingen kodÃ¤ndring i
`feature_selection.py` behÃ¶vs. BekrÃ¤ftat 2026-05-22.

### LB.5 â€” BCG:s rÃ¥-signifikans = 17.8% pÃ¥ cluster-nivÃ¥
**Symptom:** VÃ¥r cluster-output verkade ha fÃ¶r lÃ¥g rÃ¥-signifikans (18%) â€” sÃ¥g ut som problem.
**Rotorsak:** BCG:s egen baslinje har **17.8%** rÃ¥ signifikans. Vi matchade BCG, inte misslyckades.
**Regel:** BedÃ¶m aldrig signifikans-nivÃ¥er mot en absolut norm. MÃ¤t mot BCG:s output pÃ¥ samma KEY.
Se IB.1 fÃ¶r full fÃ¶rklaring.

### LB.6 â€” Verify-tool krÃ¤ver global Python 3.11
**Symptom:** `ModuleNotFoundError: No module named 'duckdb'` nÃ¤r verify_dataprep kÃ¶rs frÃ¥n venv.
**Rotorsak:** Pipeline-venvarna har inte duckdb i Python-form (de anvÃ¤nde .exe-binÃ¤ren innan LB.2).
**Regel:** Verify_tool kÃ¶rs alltid med `py -3.11` (global). Global 3.11 har: duckdb, pandas, openpyxl,
numpy, pyyaml.

### LB.7 â€” feature_selection driver Ray-workers
**Symptom:** `RayActorError` nÃ¤r feature_selection kraschar.
**Rotorsak:** Ray-workers dÃ¶r tyst pÃ¥ OOM, parent fÃ¥r RayActorError istÃ¤llet fÃ¶r MemoryError.
**Regel:** Vid RayActorError â€” kolla fÃ¶rst `dmesg` (Linux) eller Task Manager (Windows) fÃ¶r OOM-killer.
Inte ett kodfel.

### LB.8 â€” Bundle.bundle_code Ã¤r composite key
**Symptom:** Bundle-grupper har koder som `CDF114,EEX113,NIH` â€” inte enskilda ItemCodes.
**Regel:** Bundle aggregerar varukorgar. `Bundle_code` Ã¤r komma-separerad lista av ItemCodes i
varukorgen. NÃ¤r du joinar â€” splittra inte; jÃ¤mfÃ¶r hela strÃ¤ngen.

### LB.9 â€” Prisstabila grupper ger absurda elasticiteter
**Symptom:** Site-output har enskilda koefficienter pÃ¥ Â±200 och uppÃ¥t.
**Rotorsak:** Grupper med fÃ¥ prisfÃ¶rÃ¤ndringar â†’ OLS instabil â†’ koefficient blir matematiskt giltig
men praktiskt meningslÃ¶s.
**Regel:** Filtrera pÃ¥ signifikans-grindens fyra villkor (IB.2), inte pÃ¥ `is_signed_negative`. Tail-
vÃ¤rden < âˆ’10 och > 0 rensas automatiskt.

### LB.10 â€” Encoding-mismatch BCG-input vs UTF-8
**Symptom:** Svenska tecken kommer ut som `Sjukhus SÃƒÂ¶dran` nÃ¤r CSV lÃ¤ses.
**Rotorsak:** BCG-CSV Ã¤r CP1252 (latin-1), pandas default UTF-8.
**Regel:** `pd.read_csv(path, encoding="cp1252", encoding_errors="ignore")` fÃ¶r alla BCG-input. Skriv
ocksÃ¥ med `encoding="cp1252", errors="replace"` fÃ¶r konsistens.

### LB.11 â€” Verify_blend krÃ¤ver per-rep-test, ej summa
**Symptom:** Verify_blend implementerades fÃ¶rst med "samma antal representanter = match". StÃ¤mde
men sa inte mycket.
**Regel:** Per-rep-test: verifiera att samma `(Service, big_cluster)`-nyckel vÃ¤ljer samma
ItemCode-representant. 43/43 Ã¤r beviset.

### LB.12 â€” output_summary.xlsx KEY-format
**Symptom:** FÃ¶rsÃ¶kte joina output_summary med facit pÃ¥ ItemCode â€” fel grain.
**Rotorsak:** KEY i output_summary = `Cluster_Granularity + '-' + ItemCode` (cluster) eller
`SiteCode + '-' + ItemCode` (site). Inte bara ItemCode.
**Regel:** Joina pÃ¥ KEY, inte pÃ¥ ItemCode. Parsa KEY nÃ¤r du behÃ¶ver komponenterna separat.

### LB.13 â€” Cluster-seed har 7 namnade kluster
**Symptom:** Antog 0..6 numreriskt â€” fick KeyError pÃ¥ "Clinics 0".
**Regel:** BCG:s 7 kluster: `Clinics 0`, `Clinics 1`, `Clinics 2`, `Sjukhus A`, `Sjukhus B`,
`Sjukhus C`, `Sjukhus SÃ¶dran`. Namnade strÃ¤ngar, inte siffror.

### LB.14 â€” FTE-XLSX-tÃ¤ckning slutar 2025-06
**Symptom:** FÃ¤rska veckor (2025-07..2026-04) fÃ¥r `Sum_FTE_Interpolated = NULL`.
**Rotorsak:** BCG:s FTE-XLSX (`Sweden__Interpolated_Productivity_time_date_june25.xlsx`) Ã¤r frusen
till deras leveransfÃ¶nster.
**Regel:** FÃ¤rska kÃ¶rningar utanfÃ¶r 2022-07..2025-06 kommer att ha NULL-FTE. PÃ¥ sikt: bygg FTE frÃ¥n
Quinyx-data (`Manual.Fact_Quinyx_DayClinic`), IB.3 VÃ¤g 2.

### LB.15 â€” replicate_dataprep.py krÃ¤ver --validate-only
**Symptom:** Body-loop-kÃ¶rning tog 12 minuter nÃ¤r jag bara ville validera.
**Regel:** FÃ¶r validering: `python replicate_dataprep.py --validate-only`. Det laddar redan-skriven
parquet och validerar mot facit utan att kÃ¶ra om SQL.

### LB.16 â€” output_summary innehÃ¥ller alla grupper, Ã¤ven icke-signifikanta
**Symptom:** RÃ¤knade rader i output_summary, fick 3812 (fÃ¶r cluster). FÃ¶rvÃ¤ntade signifikanta.
**Regel:** output_summary har ALLA grupper. Signifikansflaggan Ã¤r en kolumn (`significant_cluster`).
Filtrera pÃ¥ den om du vill se signifikanta.

### LB.17 â€” Site = department, inte clinic
**Symptom:** "Site" och "klinik" verkade utbytbara â€” men sÃ¶kning pÃ¥ "Site = Bay Ridge" gav 0 rader.
**Rotorsak:** I pipelinens terminologi Ã¤r Site = ID_Department-vÃ¤rdet. Klinik Ã¤r affÃ¤rsnamn.
**Regel:** `SiteCode` = `ID_Department`. Mappning till klinikenavn via `dbo.Dim_Department.ClinicName`.

### LB.18 â€” Bundle Hospital/Clinics rollup-grain
**Symptom:** Bundle:s `New_cluster` har bara Hospital/Clinics-vÃ¤rden, inte de 7 underklustrena.
**Regel:** Bundle aggregerar Ã¶ver de 7 till tvÃ¥ huvudgrupper. NÃ¤r du jÃ¤mfÃ¶r bundle-output med
cluster-output: olika grain, jÃ¤mfÃ¶r inte direkt.

### LB.19 â€” Validera SpÃ¥r A:s parquet, ej SpÃ¥r B:s CSV
**Symptom:** `replicate_dataprep.py --validate-only` lÃ¤ser SpÃ¥r A:s output, inte SpÃ¥r B:s.
**Rotorsak:** replicate_dataprep lÃ¤ser `Sweden_Elasticity_Data_Prep_SQL\output\` (SpÃ¥r A:s mapp).
SpÃ¥r B:s CSV ligger i `Pipeline\02. Elasticity\2. Product Cluster Level Models\data\`.
**Regel:** Innan validering â€” verifiera att rÃ¤tt fil lÃ¤ses. Se LB.29 fÃ¶r fullstÃ¤ndig generalisering.

### LB.20 â€” data_prepration.py:s '2025-06-23' var hÃ¥rdkodad
**Symptom:** G7-arbetet pÃ¥ constants.py var inte tillrÃ¤ckligt â€” pipelinen kÃ¶rde fortfarande pÃ¥
2025-06-23 som slutdatum.
**Rotorsak:** En enskild rad (565) i data_prepration.py hade hÃ¥rdkodat datum.
**Regel:** Vid G7-style parametrisering: grep efter ALLA datum-strÃ¤ngar i pipelinen, inte bara
constants.py. ErsÃ¤tt med konstanten Ã¶verallt.

### LB.21 â€” PowerShell execution policy blockerar .ps1
**Symptom:** `cannot be loaded because running scripts is disabled on this system`.
**Rotorsak:** Default execution policy Ã¤r Restricted/AllSigned.
**Regel:** Leverera aldrig `.ps1`-scripts fÃ¶r Jens att kÃ¶ra. AnvÃ¤nd kommandoblock i chat som han
copy-pastear in i PowerShell-fÃ¶nster. KÃ„RNPRINCIPER Â§5.

### LB.22 â€” replicate_dataprep injicerar datum in-memory
**Symptom:** Trodde G7 krÃ¤vde redigering av `01_process.sql` pÃ¥ disk â€” det gjorde det inte.
**Regel:** `replicate_dataprep.py._inject_dates()` rewriter SQL-strÃ¤ngen i minnet fÃ¶re exekvering.
SQL-filen pÃ¥ disk Ã¤r ofÃ¶rÃ¤ndrad. Renare Ã¤n att ha env-var i SQL-syntax.

### LB.23 â€” Verify_infra rapporterar STRAY-filer
**Symptom:** `.bak-g7`-filer flaggade som STRAY i verify_infra-output.
**Regel:** LÃ¤mna kvar tills G7-vÃ¤gen kÃ¶rts fÃ¤rskt end-to-end (rollback-skydd). StÃ¤da efterÃ¥t med
`Remove-Item *.bak-g7 -Force`.

### LB.24 â€” Validera mot fryst original, ej arbetskopia
**Symptom:** verify_dataprep:s facit-fil var Ã¶verskriven av en export_b4b-kÃ¶rning (P_CH-facit blev
header-only pÃ¥ 179 bytes 2026-05-25).
**Rotorsak:** Facit och export-output delade katalog â†’ senare kÃ¶rning skrev Ã¶ver.
**Regel:** Validera ALLTID mot OneDrive-originalet (`BCG_orginal_V2_New`), aldrig mot
`Pipeline\...\data`-arbetskopian. Defaults i verify_dataprep pekar nu pÃ¥ originalet.

### LB.25 â€” corr 1.0 = misstÃ¤nk cirkelbevis tills kÃ¤lloberoende
**Symptom:** verify_dataprep gav corr 1.000000 PASS â€” men jÃ¤mfÃ¶rde inte rÃ¤tt fil (LB.29).
**Rotorsak:** En "perfekt" siffra utan kÃ¤lloberoende kan vara: (a) genuint korrekt, (b) cirkelbevis
(jÃ¤mfÃ¶r kopia mot sig sjÃ¤lv), (c) fel fil jÃ¤mfÃ¶rd som tystar diffen.
**Regel:** corr 1.0 â†’ frÃ¥ga "Ã¤r kÃ¤llorna oberoende?" innan PASS godkÃ¤nns. Verifiera sÃ¶kvÃ¤gar,
filstorlekar, encoding, kolumnantal â€” om nÃ¥gon skiljer sig Ã¤r de inte kopior.

### LB.26 â€” py -3.11 fÃ¶r verify_tool, inte python
**Symptom:** `python verify_dataprep.py` startade Windows Store-alias som Ã¶ppnade installations-
sida istÃ¤llet fÃ¶r att kÃ¶ra.
**Regel:** AnvÃ¤nd alltid `py -3.11` fÃ¶r verify_tool. `python` Ã¤r opÃ¥litlig pÃ¥ Windows pga Store-
alias. Pipelinens venv aktiveras med `.\.venv\Scripts\Activate.ps1` och dÃ¥ fungerar `python`.

### LB.27 â€” Aktiv venv Ã¤rver inte mellan PS-fÃ¶nster
**Symptom:** En aktiverad venv i ett fÃ¶nster syntes inte i ett annat.
**Regel:** Venv-aktivering Ã¤r fÃ¶nster-lokal. Aktivera i varje nytt PowerShell-fÃ¶nster med
`.\.venv\Scripts\Activate.ps1`.

### LB.28 â€” MÃ¤t hash fÃ¶re fil-kopia mellan modeller
**Symptom:** Kopierade `constants.py` frÃ¥n cluster till site under G7-arbetet â€” site fungerade inte.
**Rotorsak:** Filerna ser lika ut men skiljer i `Bundle_code` / `Clusters`-granulÃ¤rt kod lÃ¤ngre ner.
Lika titel â‰  lika innehÃ¥ll.
**Regel:** FÃ¶re fil-kopia mellan modellfamiljer: `Get-FileHash <fil1> <fil2>` â€” verifiera identitet
INNAN du antar att en sak rÃ¤cker fÃ¶r alla. Eller jÃ¤mfÃ¶r med `diff` / `Compare-Object`.

### LB.29 â€” verify_tool jÃ¤mfÃ¶r fel CSV om sÃ¶kvÃ¤gar divergerar
**Symptom:** `verify_dataprep.py` PASS:ade 100% (corr 1.000000, diff 0.000%) efter `export_b4b`-
kÃ¶rning â€” men jÃ¤mfÃ¶rde inte `export_b4b`:s output, utan `replicate_dataprep.py`:s output i en helt
annan katalog med samma filnamn.
**Rotorsak:** TvÃ¥ oberoende vÃ¤gar (SpÃ¥r A: `replicate_dataprep`, SpÃ¥r B: `export_b4b`) skriver filer
med samma namn (`0828_..._P_C.csv`) i olika kataloger. Verify-verktyget Ã¤r hÃ¥rdkodat fÃ¶r SpÃ¥r A:s
sÃ¶kvÃ¤g. NÃ¤r man kÃ¶r SpÃ¥r B blir SpÃ¥r A:s gamla fil (ofÃ¶rÃ¤ndrad sedan tidigare) jÃ¤mfÃ¶rd istÃ¤llet â€”
PASS utan att SpÃ¥r B faktiskt validerats.
**Regel:** Innan en validator kÃ¶rs pÃ¥ output frÃ¥n ett nytt script â€” verifiera att validatorn lÃ¤ser
frÃ¥n den katalog scriptet skriver till. Skriv ut full sÃ¶kvÃ¤g i validator-output ("loaded from
<path>"). SÃ¶kvÃ¤g-divergens mellan output-skribent och validator Ã¤r tyst (inga fel, bara fel
siffror jÃ¤mfÃ¶rda). Generell version: MASTER_PYTHON L.43.

### LB.30 â€” TvÃ¥ venv:er, olika paket â€” anvÃ¤nd rÃ¤tt fÃ¶r rÃ¤tt jobb
**Symptom:** `export_b4b_for_model.py` kraschade med `ModuleNotFoundError: No module named 'pyodbc'`
under `py -3.11` (global Python).
**Rotorsak:** verify_tool och pipelinen krÃ¤ver olika Python-miljÃ¶er. Global 3.11 har duckdb (fÃ¶r
verify_tool); Business_Analytics venv har pyodbc (fÃ¶r DW-access). Inte ett paket-installations-fel â€”
fel interpreter fÃ¶r jobbet.
**Regel:** Innan kÃ¶rning, bekrÃ¤fta vilken venv som har vilka paket. `pip show <paket>` mot varje
kandidat-interpreter Ã¤r billigt. Installera aldrig "bara fÃ¶r sÃ¤kerhets skull" â€” anvÃ¤nd den venv som
redan har paketet. Konkret mappning:
- `export_b4b_for_model.py` / `compare_to_0828_facit.py` â†’ `C:\Projekt\Business_Analytics\.venv`
- `verify_tool/*.py` â†’ global Python 3.11 via `py -3.11`
- Pipelinens steg â†’ `C:\Projekt\BCG\Pipeline\02. Elasticity\.venv`

### LB.31 â€” Tee-Object i PS 5.1 fÃ¥ngar inte stderr Ã¤ven med `2>&1`
**Symptom:** Pipeline-logg `step3_FULL_*.log` innehÃ¶ll bara PowerShell:s eget felmeddelande om
Ray:s startup, inte Ray:s faktiska progress-rader (`(process_model_group pid=...) 762`) trots
`python feature_selection.py 2>&1 | Tee-Object -FilePath $log`. Progress-raderna syntes live i
terminalen men hamnade aldrig i loggfilen.
**Rotorsak:** `Tee-Object` i PowerShell 5.1 fÃ¥ngar bara stdout, inte stderr â€” Ã¤ven nÃ¤r stderr
omdirigerats till stdout med `2>&1`. Kvarvarande bug/begrÃ¤nsning i PS-versionen Jens kÃ¶r.
**Regel:** FÃ¶r Python-kÃ¶rning dÃ¤r stderr-output mÃ¥ste loggas:
- PÃ¥ VM (bash): anvÃ¤nd `python ... 2>&1 | tee logfile.txt` (fungerar korrekt).
- Lokalt PS 5.1: anvÃ¤nd `Start-Transcript` eller `*>&1`-omdirigering, INTE `2>&1 | Tee-Object`.
  Eller skicka stderr separat: `python ... 2> stderr.log`.
Generell version (PS-vs-Python pipe-mekanik): `MASTER_PYTHON L.45`.

### LB.32 â€” Ray-OOM plateau â‰  Ã¥terhÃ¤mtning
**Symptom:** Efter `dlmalloc.cc:129 GetLastError=1450` fÃ¶ljt av `Attempting to recover 25 lost
objects` sÃ¥g dashboarden ut friskt: stabil RAM (9 GB ledigt), 16/16 python-processer kvar,
ingen ny OOM-event pÃ¥ 47 minuter. Tolkades som "Ray Ã¥terhÃ¤mtade sig lÃ¥ngsamt, kÃ¶r vidare".
Faktiskt: processen hÃ¤ngde â€” CPU-tid Ã¶ver alla workers vÃ¤xte med <10% av vÃ¤ntat per minut.
**Rotorsak:** Ray:s recovery-flÃ¶de kan lÃ¥sa workers i vÃ¤ntan pÃ¥ resurser som aldrig blir
tillgÃ¤ngliga om systemet Ã¤r pÃ¥ minneskanten. Stabil RAM + dÃ¶da workers = "Ray gav upp", inte
"Ray jobbar lÃ¥ngsamt". Snapshot-mÃ¤tningar (RAM/process-count) ljuger; det Ã¤r *fÃ¶rÃ¤ndringen* Ã¶ver
tid som avslÃ¶jar status.
**Regel:** Vid Ray-OOM med "Attempting to recover" â€” mÃ¤t **CPU-tidens tillvÃ¤xttakt** Ã¶ver workers.
FÃ¶rvÃ¤ntat under faktisk kÃ¶rning: ~50-100% av en CPU-kÃ¤rna per worker per minut. Om <10% i 5+
minuter = avbryt kÃ¶rningen, processen hÃ¤nger. Snapshot av RAM/process-count rÃ¤cker inte.

### LB.33 â€” Smoke-extrapolation underskattar Ray:s peak-RAM icke-linjÃ¤rt
**Symptom:** Smoke 50 KEY av `feature_selection.py` lyckades lokalt med 13 GB RAM-headroom kvar.
LinjÃ¤r extrapolation till full 1521 KEY antog ~3,4Ã— stÃ¶rre RAM-behov, vilket gav bedÃ¶mningen
"85% sannolikhet att lyckas". Full kÃ¶rning OOM:ade i praktiken vid ~50%.
**Rotorsak:** Ray:s peak-RAM beror pÃ¥ antal **samtidigt aktiva workers med datakopia**, vilket
vÃ¤xer icke-linjÃ¤rt med batch-volym. Smoke 50 KEY kÃ¶rde fÃ¥ samtidiga workers (datat fick plats i
worker-kvoten); 1521 KEY kÃ¶rde mÃ¥nga workers parallellt â†’ varje med en datakopia â†’ peak-RAM
exploderar.
**Regel:** Pre-flight smoke Ã¤r bra fÃ¶r "fungerar logiken?" men opÃ¥litlig fÃ¶r "klarar systemet
skalan?". FÃ¶r Ray-pipelines pÃ¥ vertikalt begrÃ¤nsad hÃ¥rdvara: testa med 30-50% av mÃ¥lmÃ¤ngd, inte
3%. Eller acceptera att lokal kÃ¶rning Ã¤r fÃ¶r riskabel och gÃ¥ direkt till VM. Smoke-success bevisar
INTE skalans framgÃ¥ng â€” bara logikens.

### LB.34 â€” `/tmp/ray_spill` fÃ¶rsvinner vid VM-omstart
**Symptom:** Skapade `/tmp/ray_spill` manuellt pÃ¥ `bcg-poc-vm`. Stoppade VM Ã¶ver natten via
`az vm deallocate`. NÃ¤sta morgon efter `az vm start`: mappen saknades. Pipeline skulle krascha
omedelbart vid Ray-start eftersom `feature_selection.py` config pekar pÃ¥ `/tmp/ray_spill`.
**Rotorsak:** Ubuntu Azure VM:s `/tmp` Ã¤r inte persistent Ã¶ver deallocateâ†’start-cykler â€” det Ã¤r
en `tmpfs` (RAM-backad) eller stÃ¤das vid omstart. `CZ.5`-fixen i koden (byte frÃ¥n `C:\ray_spill`
till `/tmp/ray_spill`) Ã¤r path-byte, inte mkdir-fix; mappen mÃ¥ste finnas innan Ray startar.
**Regel:** Vid varje VM-session (efter `az vm start` frÃ¥n deallocated tillstÃ¥nd): kÃ¶r
`ssh azureuser@<ip> "mkdir -p /tmp/ray_spill"` innan pipeline startas. `check_env.ps1 -VmInner`
auto-fixar detta. Generell VM-version: `MASTER_AZURE_COMPUTE CZ.9`.

### LB.35 â€” Imports propageras inte automatiskt vid str_replace-patch
**Symptom:** Patchade `constants.py` pÃ¥ VM med `END_DATE2 = (datetime.strptime(END_DATE,
'%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')` via str_replace. Test-import kraschade
omedelbart: `NameError: name 'datetime' is not defined`.
**Rotorsak:** Ursprungsfilen hade inte `from datetime import datetime, timedelta`. Patchen lade
till **anvÃ¤ndning** av `datetime` utan att lÃ¤gga till **importen**. Ren str_replace ser inte
sammanhanget och kan inte sjÃ¤lv inferera att en ny modul behÃ¶ver importeras.
**Regel:** Patches som introducerar nya beroenden mÃ¥ste **explicit lÃ¤gga till imports** â€” eller
verifieras via `python -c "import <modul>"` direkt efter applikation. Pre-flight test-import Ã¤r
5 sek arbete som sparar 50 min av "pipeline kraschar 50 min in i kÃ¶rningen p.g.a. saknad import".

### LB.36 â€” `data_prepration.py`:s "Shape"-print loggar input, inte output
**Symptom:** Loggraden `Data for model Shape: (523172, 33)` i steg 2:s utdata. Faktisk fil
`data_for_model.csv` skriven efter steg 2: **258,905 rader** (50% av loggat vÃ¤rde). Trodde fÃ¶rst
att en CSV var trasig.
**Rotorsak:** Print-statementet i `data_prepration.py` Ã¤r placerat **fÃ¶re** YOY-merge som droppar
L4-NULL-grupper. Loggar `df_raw.shape` (input till merge), inte `df_for_model.shape` (output efter
merge). Verkligt output Ã¤r ~50% av loggat vÃ¤rde p.g.a. L4-NULL-dropp som BCG:s konsulter byggde
in i mergen.
**Regel:** Verifiera output-storlek mot **fil**, inte mot **loggrad**. `Get-Item file.csv | %{
$_.Length }` eller `pd.read_csv(file).shape` Ã¤r sanning. Loggrader kan referera till mellansteg
Ã¤ven om det ser ut som slutsteg. R7-principen (utfall mot fil, inte loggrad) i pipeline-form.

### LB.37 â€” PowerShell multi-line-regex Ã¤r opÃ¥litlig pÃ¥ Python-kÃ¤llkod
**Symptom:** FÃ¶rsÃ¶kte patcha `check_env.py` via PowerShell `-replace` med multi-line regex fÃ¶r
att Ã¤ndra `subprocess.run`-anrop i `check_azure`-funktionen. TvÃ¥ patches misslyckades med
"hittades inte exakt" trots verifierat korrekt strÃ¤ng.
**Rotorsak:** PowerShell `-replace` anvÃ¤nder .NET regex som default behandlar `.` som "vilken
char som helst utom newline". Multi-line strÃ¤ngar (Python-funktioner spÃ¤nner flera rader)
matchar inte utan `(?s)`-flagga eller `[regex]::Singleline`. PowerShell-strÃ¤ngar dessutom
skÃ¶ra pÃ¥ citat-escaping genom 3 lager (PS â†’ ssh â†’ bash â†’ python).
**Regel:** FÃ¶r patches pÃ¥ Python-kÃ¤llkod â€” anvÃ¤nd ett **Python-skript** kÃ¶rt frÃ¥n PowerShell,
inte direkt-PowerShell-regex. Python `str.replace()` Ã¤r exakt strÃ¤ngmatchning, ingen
regex-tolkning. Eller `re.DOTALL`-flagga vid behov. Generell version: `MASTER_PYTHON L.44`.

---
### LB.38 â€” "Biter inte pÃ¥ kÃ¤rnelasticiteten" â‰  harmless
**Symptom:** Vid FAS 3 och FAS 10 dokumenterades `Master_Underkategori3` som halv-NULL (IB.8 sade
"relevant fÃ¶r gruppering, inte fÃ¶r kÃ¤rnelasticitet"). Detta minimerade konsekvensen. Resultatet
2026-06-05: 73 % av ItemCodes droppades faktiskt ur modellen â€” inklusive hela tjÃ¤nstesidan.
**Rotorsak:** Pipeline-stegen *efter* regressionen (yoy_seasonality inner merge pÃ¥ `service`) droppar
hela KEY fÃ¶r rader med NULL pg4. PÃ¥stÃ¥endet "pÃ¥verkar inte regressionen" stÃ¤mmer fÃ¶r de KEY:n som
Ã¶verlever till regressionen â€” men fÃ¶rutsÃ¤tter att de inte droppas av en upstream merge. Vi tittade
pÃ¥ regressionssteget isolerat och drog en allmÃ¤n slutsats om hela pipelinen.
**Regel:** NÃ¤r en datakvalitetsbrist flaggas â€” frÃ¥ga **"vid vilket pipeline-steg anvÃ¤nds denna
kolumn, med vilken merge-typ?"** innan slutsatsen "harmless". `pandas.merge(how="inner")` pÃ¥
NULL-vÃ¤rden = total dropout (NaN matchar inte NaN). SpÃ¥ra varje kolumns liv frÃ¥n kÃ¤lla till
regressionsinput. *(Princip: "mÃ¤t, gissa inte", KÃ„RNPRINCIPER.)*

### LB.39 â€” Validering pÃ¥ producerade rader fÃ¥ngar inte populations-bortfall
**Symptom:** `verify_dataprep.py` rapporterade FR-1 PASS med corr=1.0 mot BCG:s 0828-facit i flera
sessioner fÃ¶re 2026-06-05. Detta dolde att 834 av 1151 ItemCodes droppades senare i pipelinen.
Verify-suiten var "grÃ¶n" medan modellen exkluderade veterinÃ¤rtjÃ¤nster (huvudintÃ¤ktskÃ¤llan).
**Rotorsak:** Verify mÃ¤ter "matchar de rader vi har" â€” inte "matchar vi alla rader vi *borde* ha".
Korrelation pÃ¥ en delmÃ¤ngd kan vara 1.0 medan delmÃ¤ngden sjÃ¤lv Ã¤r ofullstÃ¤ndig. Klassisk
selektion-bias: vi validerar det vi producerade, inte det vi missade.
**Regel:** Varje pipeline-steg ska logga **ItemCode-count in vs ut**. Avvikelse > 1 % krÃ¤ver
explicit fÃ¶rklaring. Verify-suiten bÃ¶r inkludera **tÃ¤ckningsgrad-KPI**:
`vÃ¥r_codes âˆ© facit_codes / facit_codes`. Detta Ã¤r komplement till befintliga
likhetsvalideringar â€” inte ersÃ¤ttning. Lade till `validate_extraction_coverage.py` 2026-06-07
som Ã¥tgÃ¤rd: jÃ¤mfÃ¶r vÃ¥r ItemCode-count mot BCG-facitets, flaggar avvikelse > 0.5 %.

### LB.40 â€” `load_or_create_feature_control_file()` Gren B saknar `return`
**Symptom:** `feature_selection.py` (steg 3) kraschar med `AttributeError: 'NoneType' object has
no attribute 'melt'` pÃ¥ rad 504 (i `check_nulls()` rad 630). IntrÃ¤ffar bara pÃ¥ **fÃ¶rsta kÃ¶rningen**
efter att `control_file.xlsx` raderats.
**Rotorsak:** Funktionen `load_or_create_feature_control_file()` (rad 114-158 i BCG:s kod) har
tvÃ¥ grenar: Gren A (rad 134-135) â€” filen finns â†’ `return control_file` âœ…; Gren B (rad 138-158) â€”
filen saknas â†’ skapa, spara till disk â†’ **glÃ¶mmer `return`** âŒ. Gren B faller igenom till
funktionens slut och returnerar `None` (Python-default). Den nyss skapade filen finns pÃ¥ disk men
returneras aldrig till anropssidan. NÃ¤sta rad 630 (`check_nulls(df_raw, control_file)`) tar emot
`None` och kraschar pÃ¥ fÃ¶rsta `df_control.melt(...)`.
**Regel:** AnvÃ¤nd **LÃ¶sning A** vid problem: pipeline-skriptet kÃ¶rs om. Andra gÃ¥ngen tas Gren A
(filen finns frÃ¥n fÃ¶rsta kÃ¶rningen) och funktionen returnerar korrekt. **Patcha inte BCG-koden**
(LF.3: BCG-original skrivskyddad). Workaround: om du behÃ¶ver "rensa state" infÃ¶r ny kÃ¶rning,
radera ALDRIG `control_file.xlsx` direkt â€” istÃ¤llet lÃ¥t steg 2 kÃ¶ra normalt fÃ¶rst (det skapar
inte filen), kÃ¶r steg 3 fÃ¶rsta gÃ¥ngen (Gren B skapar filen + kraschar â€” accepterat), kÃ¶r steg 3
andra gÃ¥ngen (Gren A returnerar â€” fungerar). Detta Ã¤r `crash-recovery-mÃ¶nster` â€” inte en bug-fix.
**BekrÃ¤ftat pÃ¥ Site (2026-06-09):** Samma tvÃ¥pass-mÃ¶nster gÃ¤ller varje modellfamilj pÃ¥ nytt KEY-set â€” Site (6624 KEY) kraschade pass 1, kÃ¶rdes om, Gren A laddade control_file pass 2 och fortsatte. Regeln Ã¤r familje-oberoende.

### LB.41 â€” `control_file.xlsx` regenereras INTE av steg 2 (`data_prepration.py`)
**Symptom:** FÃ¶rvÃ¤ntade att rensa stale `control_file.xlsx` fÃ¶re VM-kÃ¶rning skulle automatiskt
regenerera den med ny KEY-population frÃ¥n steg 2. Den skapas istÃ¤llet fÃ¶rst i steg 3.
**Rotorsak:** BCG:s pipeline har `control_file.xlsx` som **input till steg 3**, inte output frÃ¥n
steg 2. Steg 2 (`data_prepration.py`) producerar `data_for_model.csv` med 4180 KEY men skriver
ingen control-fil. Steg 3 (`feature_selection.py`) rad 158 Ã¤r dÃ¤r control_file skapas (om den inte
finns) baserat pÃ¥ `data_for_model.csv`s `model_group`-kolumn.
**Regel:** Rensning av `control_file.xlsx` Ã¤r sÃ¤ker fÃ¶re steg 3, inte fÃ¶re steg 2. Schema:
steg 1, 2: kÃ¶r utan att rÃ¶ra control_file; steg 3 fÃ¶rsta kÃ¶rning: skapar `control_file.xlsx`
baserat pÃ¥ steg 2:s output (kombinerat med LB.40: kraschar pÃ¥ Gren B â†’ kÃ¶r om â†’ Gren A fungerar);
steg 4: lÃ¤ser den fÃ¤rdiga control_file.

### LB.42 â€” Output_summary.xlsx ligger i `output/model/` (inte `output/`)
**Symptom:** `find ~/bcg/cluster -name 'output_summary.xlsx'` returnerar fil i fel mapp fÃ¶rsta
gÃ¥ngen du letar. scp-kommandon som antar `output/output_summary.xlsx` fÃ¥r "No such file".
**Rotorsak:** BCG-pipelinens output-struktur Ã¤r hierarkisk: `output/data/` (input om bearbetad),
`output/data_preparation/` (steg 2-artefakter), `output/regular_price/` med mellanslag pÃ¥ vissa
system (steg 1-output), `output/feature_selection/` (steg 3-artefakter), **`output/model/`** (steg
4 producerar `output_summary.xlsx`, `model_summary.xlsx`, `model_results.csv`), `output/model/automl/`
(feature-selection-mellanresultat), `output/model/model objects/` (sparade modellobjekt, mellanslag).
**Regel:** `output_summary.xlsx` ligger alltid i `~/bcg/<modellfamilj>/output/model/`. FÃ¶r scp:
`scp azureuser@vm:~/bcg/cluster/output/model/output_summary.xlsx $archive`. Verifiera med
`find ~/bcg/cluster -name 'output_summary*' -newer <referensfil>` om datum Ã¤r osÃ¤kert (LB.43).

### LB.43 â€” `ls -la` mapp-datum kan misstolkas som fil-datum
**Symptom:** `ls -la output/model/` 2026-06-08 visade mapp `Jun 5 08:23` och fil `Jun 8 08:41`.
Vid snabb avlÃ¤sning trodde jag att `output_summary.xlsx` var frÃ¥n 5 juni (gammal) tills jag lÃ¤ste
om â€” den var faktiskt 8 juni (ny).
**Rotorsak:** FÃ¶rsta kolumnen efter rÃ¤ttigheter i `ls -la` Ã¤r mapp-/fil-datum. NÃ¤r en mapp och
en fil listas tillsammans Ã¤r det lÃ¤tt att lÃ¤sa fel rad. Mapp-datum Ã¤r nÃ¤r **mappen senast
modifierades** (= ny fil skapades i den), inte nÃ¤r **innehÃ¥ll modifierades senast**.
**Regel:** AnvÃ¤nd `find -newer` fÃ¶r att hitta filer modifierade efter en referenspunkt:
`find ~/bcg -name 'output_summary*' -newer ~/bcg/cluster/code/control_files/control_file.xlsx`.
Detta filtrerar bort allt Ã¤ldre och visar bara dagens. SÃ¤krare Ã¤n manuell datum-tolkning av
`ls -la`-output.

### LB.44 â€” Excel-efterbearbetningssteg (steg 5 + Step 6) kÃ¶rs LOKALT pÃ¥ Windows, aldrig pÃ¥ Linux-VM
**Symptom:** `data_prep_after_model_output.py` (steg 5) kraschar pÃ¥ VM med
`ModuleNotFoundError: No module named 'xlwings'` direkt vid `import xlwings` (rad 8), innan nÃ¥gon
logik kÃ¶rts. Samma fil i Cluster har identisk import.
**Rotorsak:** Steg 5 och `Fall_Back_Logic.py` (Step 6) anvÃ¤nder xlwings med Ã¤kta Excel-COM-anrop
(`xw.App`, `wb.api.SaveAs(FileFormat=XLSB)`, `wb.api.RefreshAll()`). Detta krÃ¤ver Windows +
installerad Excel â€” xlwings styr en faktisk Excel-instans via COM och **kan inte kÃ¶ras pÃ¥ Linux**,
oavsett om paketet installeras. ModellberÃ¤kningen (steg 1-4, Ray) hÃ¶r hemma pÃ¥ VM:en; Excel-
efterbearbetningen hÃ¶r hemma lokalt. Detta Ã¤r en arkitektonisk grÃ¤ns som gÃ¤ller ALLA modellfamiljer.
**Regel:** KÃ¶r steg 1-4 pÃ¥ Azure-VM (tung Ray-berÃ¤kning), steg 5 + Step 6 lokalt pÃ¥ Windows.
FÃ¶r lokal steg 5-kÃ¶rning: `py -3.11` (har xlwings 0.33.20 + Excel finns). **KÃ¶r frÃ¥n modellfamiljens
ROT, inte frÃ¥n `code/`** â€” lokala `constants.py` har CWD-relativ config-sÃ¶kvÃ¤g (`.\code\src\config.yml`),
sÃ¥ `cd` till roten och kÃ¶r `py -3.11 code\data_prep_after_model_output.py`. SÃ¤tt `BCG_START_DATE`/
`BCG_END_DATE` sÃ¥ datumfÃ¶nstret matchar vÃ¤xande data. **Lokal raw-data-CSV (`data/0902_..._site_level.csv`)
MÃ…STE vara den vÃ¤xande (180 MB), inte frusen (130 MB)** â€” annars blir joinen mot vÃ¤xande modelloutput
fel (R7-fÃ¤lla, tyst). launcher.py inkluderar steg 5 i sekvensen â€” pÃ¥ VM kraschar det steget alltid,
vilket Ã¤r vÃ¤ntat; modelloutputen (steg 4) Ã¤r klar innan dess och hÃ¤mtas hem fÃ¶r lokal steg 5-kÃ¶rning.

### LB.45 â€” `write_df_preserve_named_range` fÃ¥ngar `KeyError` men xlwings kastar `com_error`
**Symptom:** Steg 5 (`data_prep_after_model_output.py`) kraschar pÃ¥ rad 252/237 med
`pywintypes.com_error: (-2147352567, 'Undantag intrÃ¤ffade', ...)` nÃ¤r mÃ¥lmallen
(`Sweden_Sitecode_level_elasticity_summary.xlsx`) Ã¤r tom/ny och saknar fÃ¶rvÃ¤ntade ark/namngivna omrÃ¥den.
**Rotorsak:** Funktionen `write_df_preserve_named_range` har en fallback: `try: wb.sheets[name]` /
`except KeyError: wb.sheets.add(...)` (och samma mÃ¶nster fÃ¶r `wb.names[range]`). Avsikten Ã¤r "anvÃ¤nd
om finns, skapa annars". Men nÃ¤r arket/omrÃ¥det saknas kastar xlwings ett `pywintypes.com_error` â€”
**inte** `KeyError` â€” sÃ¥ fallbacken (skapa) nÃ¥s aldrig och felet bubblar upp. PÃ¥ BCG:s fÃ¶rformaterade
mall (dÃ¤r ark/omrÃ¥den redan finns) tas if-grenen och buggen syns aldrig; den triggas bara pÃ¥ en
tom/ny mall (t.ex. fÃ¶rsta kÃ¶rning pÃ¥ ny maskin).
**Regel:** Byt `except KeyError:` mot `except Exception:` (3 stÃ¤llen i funktionen). DÃ¥ fÃ¥ngas
COM-felet och fallbacken bygger ark/omrÃ¥de frÃ¥n grunden â†’ steg 5 blir sjÃ¤lvfÃ¶rsÃ¶rjande, oberoende av
en fÃ¶rformaterad mall. Backup togs som `.bak-before-comfix`. *(Detta Ã¤r en faktisk kod-fix i en
lokal arbetskopia, inte BCG-original â€” LF.3 gÃ¤ller inte lokala kÃ¶rkopior.)*

### LB.46 â€” Azure CLI cachar aktiv subscription mellan sessioner (subscription-fÃ¤llan)
**Symptom:** Ny dag, `az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm` ger
`AuthorizationFailed ... does not have authorization to perform action ... over scope`. Ser ut som
behÃ¶righetsfÃ¶rlust eller utgÃ¥ngen token.
**Rotorsak:** `az` minns senast satta subscription mellan sessioner. Hade man jobbat i en annan
subscription emellan (t.ex. `ev-lz1-hybrid` fÃ¶r ProvetDiscount) sitter man kvar dÃ¤r. VM:en finns inte
i den subscriptionen â†’ AuthorizationFailed. Det Ã¤r INTE en utgÃ¥ngen token och INTE behÃ¶righetsfÃ¶rlust
â€” bara fel aktiv subscription. (`MASTER_AZURE.md` anger `ev-lz1-hybrid` som default, vilket fÃ¶rvÃ¤rrar
det fÃ¶r BCG-arbetet som bor i `ev-lz3-ai`.)
**Regel:** KÃ¶r alltid `az account show` FÃ–RE VM-kommandon (mÃ¤t, gissa inte). VM:en bor i
subscription `ev-lz3-ai (SE)` (id `42f726f8-91ee-44d4-832f-9d9ec412ef8f`), RG
`ev-openai-swce-rg-test`. SÃ¤tt rÃ¤tt subscription fÃ¶rst: `az account set --subscription "ev-lz3-ai (SE)"`.

### LB.47 â€” scp av fjÃ¤rrfil med mellanslag i sÃ¶kvÃ¤g: `cp` till ren sÃ¶kvÃ¤g pÃ¥ VM fÃ¶rst
**Symptom:** `scp azureuser@vm:"'~/bcg/site/output/regular price/ivc_sweden_price.csv'" "$dest"`
ger `No such file or directory` trots att filen finns â€” mellanslaget i mappnamnet (`regular price`)
Ã¶verlever inte genom PowerShellâ†’scpâ†’bash-citatlagren. Dessutom: `~` expanderas INTE inom enkla citat
i bash.
**Rotorsak:** Tre citat-tolkar (PowerShell, scp-argumentparser, fjÃ¤rr-bash) ska enas om var
mellanslaget hÃ¶r hemma, och `~` inom `'...'` fÃ¶rblir literal. Kombinationen Ã¤r praktiskt taget
omÃ¶jlig att fÃ¥ rÃ¤tt inline.
**Regel:** `cp` filen till en mellanslagsfri sÃ¶kvÃ¤g pÃ¥ VM:en fÃ¶rst (med full sÃ¶kvÃ¤g, inte `~`), hÃ¤mta
sedan dÃ¤rifrÃ¥n:
```powershell
ssh azureuser@vm "cp '/home/azureuser/bcg/site/output/regular price/fil.csv' /home/azureuser/fil.csv"
scp azureuser@vm:/home/azureuser/fil.csv "C:\full\lokal\sÃ¶kvÃ¤g\fil.csv"
```
Samma kÃ¤rnprincip som Â§10b/Â§11 i UBUNTU_AZURE_VM: undvik att tvinga komplexa sÃ¶kvÃ¤gar genom flera
citat-lager â€” bygg/flytta till en enkel sÃ¶kvÃ¤g fÃ¶rst.

---

### LB.48 â€” lÃ¤s *runnern* som producerade artefakten innan du deklarerar "datakedjan krÃ¤ver patch X"
**Symptom:** F.9-inventeringen slog fast att Bundle-masterdatan behÃ¶vde en G7-datumpatch i SQL fÃ¶r att bli
vÃ¤xande. Fel â€” `replicate_dataprep.py` (runnern som faktiskt producerar masterdatan) hade redan en komplett
G7-datuminjektor (`_inject_dates`/`_fiscal_year_flags`) som skriver om `YearFlag IN(...)` in-memory nÃ¤r
`BCG_END_DATE` Ã¤r satt. Patchen vi planerade var redan lÃ¶st en nivÃ¥ upp.
**Rotorsak:** Antagandet byggde pÃ¥ att lÃ¤sa SQL-filen isolerat, inte scriptet som kÃ¶r SQL:en. SQL:en sÃ¥g
hÃ¥rdkodad ut, men runnern muterade den vid kÃ¶rning. Att lÃ¤sa halva kedjan gav en falsk slutsats.
**Regel:** Innan du planerar en patch mot en datakedja â€” spÃ¥ra artefakten bakÃ¥t till scriptet som
*faktiskt skapar* den och lÃ¤s det helt. Patcha aldrig mot en mellanfil utan att veta vad som skriver den.
*(Drev hela F.9-omkalibreringen 2026-06-10; jfr KÃ„RNPRINCIPER search-before-build.)*

---

### LB.49 â€” masterdata CSVâ†’parquet: lÃ¤s med `all_varchar=true`, typning hÃ¶r hemma hos konsumenten
**Symptom:** `read_csv_auto` kraschade vid CSVâ†’parquet-konvertering â€” DuckDB:s sample-baserade typgissning
satte `ItemType` till BIGINT, men ett missformat citerat produktnamn (rad 654262) innehÃ¶ll text â†’ cast-fel
mitt i en 7 GB-fil.
**Rotorsak:** DuckDB samplar de fÃ¶rsta N raderna fÃ¶r typinferens och ser inte hela filen. En enda avvikande
rad lÃ¥ngt ner sprÃ¤nger en typgissning som "sÃ¥g rÃ¤tt ut" i samplet.
**Regel:** LÃ¤s rÃ¥ masterdata-CSV med `all_varchar=true` vid parquet-konvertering. Konsumenten (`00_read.sql`)
CASTar Ã¤ndÃ¥ allt till rÃ¤tt typer â€” typning Ã¤r dess ansvar, inte konverterarens. Noll radfÃ¶rlust, ingen
sample-krasch. BekrÃ¤ftat: `diagnose_masterdata_csv.py` lÃ¤ste alla 27,4M rader med `all_varchar` utan bortfall.

---

### LB.50 â€” dubbel fÃ¶nsterdefinition Ã¤r en tyst-fel-fÃ¤lla; ersÃ¤tt med konstant-ankare utan Ã¶vre grÃ¤ns
**Symptom:** Bundle-SQL-output kapades tyst vid Jun 2025 trots att masterdatan var vÃ¤xande t.o.m. Jun 2026.
`verify_bundle_growing.py` â†’ CAPPED, max_week 2025-06-30.
**Rotorsak:** TvÃ¥ oberoende steg filtrerade *samma* tidsfÃ¶nster â€” masterdatans G7-injektor (vÃ¤xande) OCH
`01_process.sql` rad 20 med hÃ¥rdkodad `YearFlag IN('...23','...24','...25')`. NÃ¤r bara det ena uppdaterades
divergerade de, och det snÃ¤vare (SQL:ens whitelist) vann tyst utan fel eller varning.
**Regel:** NÃ¤r tvÃ¥ steg filtrerar samma fÃ¶nster Ã¤r det ena redundant och en framtida tyst-fel-kÃ¤lla. Ta bort
det redundanta filtret; ersÃ¤tt med konstant-ankare utan Ã¶vre grÃ¤ns: `CAST(week_starting_monday AS DATE) >=
DATE '2022-07-01'`. DÃ¥ Ã¤rvs fÃ¶nstret frÃ¥n kÃ¤llan, kan aldrig kapa tyst, och krÃ¤ver ingen Ã¥rlig redigering.
*(Patchad via `patch_bundle_yearflag.py`; jfr LF.2 konstant-ankare. Detta Ã¤r en DRIFT-fÃ¤lla: konfiguration
pÃ¥ tvÃ¥ stÃ¤llen som tyst glider isÃ¤r.)*

---

### LB.51 â€” BCG-kod har UK-rester, tomma config-nycklar och aldrig-kÃ¶rda steg; verifiera config mot scriptets faktiska anrop fÃ¶re kÃ¶rning
**Symptom:** Bundle-Ray-varukorgsbygget (`2.Sweden_Bundle_Clinic_Model_Data_Creation.py`) skulle krascha med
KeyError: scriptet lÃ¤ser `config['model_data_creation']['sweden_bundles']`, men `config_data_prep.yml` har
nyckeln `uk_bundles`. Config pekade dessutom pÃ¥ frusna BCG-filnamn (`0826_*`/`0825_*`) som inte finns; `data/`
var tom; `build_bundle_for_type` fÃ¶rvÃ¤ntade en exploderad BundleÃ—ProductCode-input, inte den komma-separerade
`sweden_bundle_analysis.csv`; FTE-formatet var XLSX i kod men CSV i vÃ¥r dataprep.
**Rotorsak:** Koden Ã¤r UK-arv (variabler heter `uk_bundles`, `D:\IVC E Phase 1`-sÃ¶kvÃ¤gar i kommentarer),
aldrig kÃ¶rd pÃ¥ svenska sidan, config aldrig synkad med scriptets faktiska anrop. Den "ser kÃ¶rbar ut" men har
aldrig exekverats i vÃ¥r kontext.
**Regel:** Innan du kÃ¶r ett aldrig-testat BCG-steg: (1) `grep` scriptets `config[...]`-anrop och matcha varje
nyckel mot config-filen; (2) verifiera att varje input-sÃ¶kvÃ¤g pekar pÃ¥ en faktisk fil, inte ett fruset
BCG-original; (3) kontrollera format-antaganden (`read_excel` vs `read_csv`) och kolumnnamn mot vad uppstrÃ¶ms
faktiskt producerar. Anta aldrig att BCG-kod Ã¤r kÃ¶rklar â€” den Ã¤r ofta UK-rester med dÃ¶d config.

---

### LB.52 â€” Step 6 fÃ¶rvÃ¤ntar pre-splittad KEY (ItemCode-kolumn); vÃ¥r vÃ¤xande output har bara KEY
**Symptom:** `Fall_Back_Logic.py` rad 252 (`read_blended_model_data`) kraschade med `KeyError: 'ProductKey'`
pÃ¥ `dfcluster.merge(service_map, on=ProductKey)`. Cluster-lÃ¤saren renamar `{'ItemCode':'ProductKey'}` men
vÃ¥r vÃ¤xande `output_summary.xlsx` har ingen `ItemCode`-kolumn â€” bara `KEY` (`Clinics 0-AAP115`).
**Rotorsak:** BCG:s facit-blended_model hade kolumnerna pre-splittade (`ItemCode` + `Cluster` separat),
medan vÃ¥r rÃ¥ modell-output bÃ¤r `KEY` (samma format som Site/Bundle). `read_blended_model_data` saknar den
KEY-extraktion som `reading_site_level_data` och `reading_bundle_cluster_level_data` redan har â€” fÃ¶r facit
behÃ¶vde den inte den. En strukturskillnad mellan facit och vÃ¤xande output, inte ett datafel.
**Regel:** NÃ¤r du matar vÃ¤xande modell-output till ett BCG-steg som fÃ¶rvÃ¤ntar facit-struktur: splitta `KEY`
â†’ `Cluster` + `ItemCode` i runnern (`rsplit('-', n=1)` â€” klusternamn har mellanslag men inga bindestreck,
ItemCode har inga bindestreck, sÃ¥ sista bindestrecket Ã¤r rÃ¤tt separator; matchar `extract_cluster_from_key`).
LÃ¤gg anpassningen i runnern, inte i BCG-koden â€” dÃ¥ fÃ¶rblir `Fall_Back_Logic.py` orÃ¶rd och facit-jÃ¤mfÃ¶rbar.

---

### LB.53 â€” xlwings `wb.names[range]` kraschar (com_error) om mallens namnomrÃ¥de saknas; datan Ã¤r redan sparad
**Symptom:** Step 6 kraschade pÃ¥ sista raden (rad 691, `write_df_preserve_named_range`) med
`pywintypes.com_error` pÃ¥ `wb.names[named_range].refers_to = ...`. Mallen `Excel_Outputs\Sweden_Fallback.xlsx`
saknar det namngivna omrÃ¥det `raw` som koden fÃ¶rsÃ¶ker resiza.
**Rotorsak:** `wb.names[named_range]` antar att namnomrÃ¥det finns; gÃ¶r det inte kastar Excel-COM ett generiskt
undantag. Detta Ã¤r sista steget (uppdaterar BCG:s pivot-dashboard), EFTER att `Final_Fallback_Data.xlsx` +
den timestampade kopian redan skrivits (rad 671/686). Datan gÃ¥r alltsÃ¥ inte fÃ¶rlorad â€” bara dashboard-
kosmetiken fallerar. (Samma COM-klass som LB.45.)
**Regel:** (1) Behandla mall-/named-range-skrivning som kosmetiskt sista steg â€” verifiera output via den
fristÃ¥ende `Final_Fallback_Data*.xlsx` (R7: lita pÃ¥ filen, inte pÃ¥ att hela scriptet exitar 0). (2) GÃ¶r
namnomrÃ¥des-skrivning defensiv: `try: wb.names[nr] except KeyError/com_error: wb.names.add(nr, ...)` â€” skapa
om det saknas istÃ¤llet fÃ¶r att krascha. (3) En icke-noll exit betyder inte att datan saknas; kontrollera
vad som skrevs fÃ¶re kraschpunkten.

---

> **OBS â€” LB.54-58 nedan rekonstruerade frÃ¥n referens.** Dessa fem postares brÃ¶dtext saknades i
> kÃ¤llfilen `LESSONS_BCG.md` (den slutade vid LB.53); de refererades i NEXT_SESSION och MASTER_AZURE men
> infogades aldrig. InnehÃ¥llet nedan Ã¤r hÃ¤rlett ur deras index-rader, MASTER_AZURE AZ.6-10 och
> NEXT_SESSION 2026-06-12. **Verifiera mot ursprungssessionen (Phase Z, 2026-06-12) och justera vid
> behov** â€” detta Ã¤r referens-rekonstruktion, inte verifierad originaltext.

### LB.54 â€” SSH-detach: `&` rÃ¤cker inte; processen mÃ¥ste Ã¤ga sina egna fd:er
**Symptom:** detached jobb startat med `&` Ã¶ver SSH dog nÃ¤r SSH-kanalen stÃ¤ngdes.
**Rotorsak:** processen Ã¤rvde SSH-sessionens fd:er; nÃ¤r kanalen stÃ¤ngdes fick den SIGHUP.
**Regel:** kÃ¶r via `launcher.sh` + `setsid` sÃ¥ jobbet fÃ¥r egen sessions-ledare och egna fd:er och
Ã¶verlever stÃ¤ngd SSH. Isolerat verifierad 1,4 s detach.
**GÃ¤ller om:** ett lÃ¥ngt jobb startas detached Ã¶ver en SSH-kanal som kommer att stÃ¤ngas.
**FÃ¶rkroppsligas i:** `orchestration/infrastructure/azure_vm.py` (setsid-detach); MASTER_AZURE AZ.6.

### LB.55 â€” Flaky VPN-tunnel mitt i kÃ¶rning fÃ¥r inte tolkas som kÃ¶rningsfel
**Symptom:** poll mot VM:en tappade kontakt mitt under en skarp kÃ¶rning (VPN-tunnelglapp).
**Rotorsak:** nÃ¤tavbrott i observationskanalen, inte i jobbet â€” jobbet kÃ¶rde vidare pÃ¥ VM:en.
**Regel:** poll-fel svÃ¤ljs av retry; kÃ¶rningens hÃ¤lsa avgÃ¶rs av framstegsmÃ¥tt pÃ¥ VM:en, inte av att
observationskanalen Ã¤r obruten. KÃ¶rningen Ã¶verlevde och gick i mÃ¥l.
**GÃ¤ller om:** ett detached VM-jobb Ã¶vervakas Ã¶ver en opÃ¥litlig tunnel (VPN/kontorsnÃ¤t).
**FÃ¶rkroppsligas i:** `orchestration/runners/run_site_model.py` (tolerant poll). *Instans av KÃ„RN P.2
/ AZ.7 â€” observation â‰  kÃ¶rningshÃ¤lsa.*

### LB.56 â€” Deallokera utfallsstyrt, inte i blint `finally`
**Symptom:** risk att en avbruten/inspektionsvÃ¤rd kÃ¶rning deallokerar VM:en automatiskt.
**Regel:** fÃ¥nga Ctrl+C; deallokera baserat pÃ¥ kÃ¶rningens *utfall*, inte ovillkorligt i `finally`, sÃ¥ en
kÃ¶rning man vill inspektera inte slÃ¤nger sin egen VM. Verifiera power-state efterÃ¥t (LB.60).
**GÃ¤ller om:** en runner Ã¤ger VM-livscykeln och kan avbrytas mitt i.
**FÃ¶rkroppsligas i:** `orchestration/runners/run_site_model.py` (utfallsstyrd deallocate); MASTER_AZURE AZ.8.

### LB.57 â€” Prefect fÃ¶rkastat fÃ¶r denna miljÃ¶
**Symptom:** Ã¶vervÃ¤gande av orkestreringsramverk (Prefect) fÃ¶r pipelinen.
**Rotorsak:** Prefects dashboard nÃ¥r inte en kollega utan publik IP / reverse proxy â†’ lÃ¶ser inte
nÃ¤tvÃ¤ggen, lÃ¤gger till en serverkomponent.
**Regel:** fÃ¶r en lÃ¥st miljÃ¶ utan publik IP Ã¤r ett hemmabygge med Blob-statusfil rÃ¤tt. Ã…terbesÃ¶k om
flera pipelines/utvecklare uppstÃ¥r.
**GÃ¤ller om:** orkestrering Ã¶vervÃ¤gs i en miljÃ¶ utan nÃ¥bar dashboard-vÃ¤rd.

### LB.58 â€” DW (Azure SQL) nÃ¥r inte frÃ¥n VM:en
**Symptom:** DW-query frÃ¥n VM:en gav `BLOCKED` mot `:1433` (medan `OUT_OK` mot github).
**Rotorsak:** DW-specifik IP-vitlistning â€” VM:ens VNet Ã¤r inte vitlistat.
**Regel:** extraktionen fÃ¶rblir lokal; arkitektur = lokal extraktion â†’ Blob â†’ VM (FD.17). MÃ¤t
nÃ¥barheten, anta den inte.
**GÃ¤ller om:** en VM i annat VNet behÃ¶ver nÃ¥ Azure SQL bakom IP-vitlistning.
**FÃ¶rkroppsligas i:** `orchestration/infrastructure/blob.py` (arkitekturval); MASTER_AZURE AZ.10.

---

### LB.59 â€” run_id = datum ger statusfil-kollage [LÃ–ST 2026-06-22: run_id = datafÃ¶nster]
**Symptom:** `2026-06-12.json` visade `state=running` med `finished_at` (13:15) FÃ–RE `last_heartbeat`
(15:20), plus ett `error`-fÃ¤lt frÃ¥n ett tidigare misslyckat fÃ¶rsÃ¶k medan `site_model` var `succeeded`.
**Rotorsak:** run_id = datumet. Dagens andra kÃ¶rning skrev (overwrite) ovanpÃ¥ den fÃ¶rstas statusfil men
ersatte inte alla fÃ¤lt â†’ kollage av tvÃ¥ kÃ¶rningars tillstÃ¥nd.
**Regel (LÃ–ST 2026-06-22):** den ursprungliga regeln fÃ¶reslog datum+tidsstÃ¤mpel (unikt per kÃ¶rning) â€”
men det FÃ–RKASTADES. Vald lÃ¶sning: run_id = **datafÃ¶nstret** (`window_run_id(start, end)` â†’
`2022-07-01_2026-04-30`), INTE kÃ¶rningstidpunkten. SkÃ¤let Ã¤r etappmodellen: familjerna (cluster/site/
bundle/data) kÃ¶rs som separata etapper, ofta vid olika tillfÃ¤llen, mot SAMMA datafÃ¶nster â€” och ska dÃ¥
dela EN statusfil sÃ¥ dashboarden visar alla familjer grÃ¶na i synk med perioden. Unikt-per-kÃ¶rning hade
splittrat familjerna pÃ¥ olika filer. Kollage-symptomet lÃ¶ses i stÃ¤llet av `RunStatus.finalize()`, som
hÃ¤rleder run-nivÃ¥ns state ur fasernas tillstÃ¥nd (pending lÃ¤mnas grÃ¥, hÃ¤ngande running stÃ¤ngs, run blir
vilande/klar i stÃ¤llet fÃ¶r att ticka i evighet â€” "80h-spÃ¶ket"). `succeed()` blev dÃ¤rmed fÃ¶rÃ¥ldrad.
**GÃ¤ller om:** flera etapper mot samma datafÃ¶nster skriver till samma statusnyckel.
**FÃ¶rkroppsligas i:** `orchestration/shared/run_status.py` (`window_run_id`, `window_label`, `finalize`);
de fyra runnrarna anropar `finalize()` efter `finish_phase`. *StÃ¤nger den Ã¶ppna FD-referensen â€” fixen Ã¤r
gjord, ej lÃ¤ngre "krÃ¤ver kontraktsÃ¤ndring".*

### LB.60 â€” deallocate-i-logg Ã¤r inte bevis pÃ¥ att VM:en Ã¤r nere
**Symptom:** runnern loggade "VM deallocated -- billing stopped" 17:20; en kontroll senare samma kvÃ¤ll
visade Ã¤ndÃ¥ `VM running` (kostade ~9 kr/h obemÃ¤rkt).
**Rotorsak:** deallocate-anropet bekrÃ¤ftades aldrig mot faktiskt power-state â€” antingen tyst-misslyckat
anrop, token-glapp, eller Ã¥terstartad VM.
**Regel:** verifiera ALLTID power-state efter en kÃ¶rning:
`az vm get-instance-view --resource-group <rg> --name <vm> --query "instanceView.statuses[?starts_with(code,'PowerState/')].displayStatus" -o tsv`.
**GÃ¤ller om:** en kÃ¶rning avslutas med ett deallocate-anrop som inte verifieras mot faktiskt tillstÃ¥nd.
**FÃ¶rkroppsligas i:** `orchestration/runners/run_site_model.py` (deallocate-steget); MASTER_AZURE Â§8.
*Instans av R7 / KÃ„RN P.2 (lita pÃ¥ tillstÃ¥ndet, inte pÃ¥ log-raden) â€” det observerade argumentet fÃ¶r
FD.16 (VM-sidigt auto-shutdown som oberoende skyddsnÃ¤t; runnerns deallocate rÃ¤cker inte ensam).*

### LB.61 â€” Flask serverar mall frÃ¥n disk, men webblÃ¤saren cachar
**Symptom:** Ã¤ndrad `dashboard.html` pÃ¥ disk (`Select-String` bekrÃ¤ftade nya innehÃ¥llet), men sidan i
webblÃ¤saren visade fortfarande gammal version.
**Rotorsak:** Flask lÃ¤ser mallen frÃ¥n disk per request, men webblÃ¤saren Ã¥teranvÃ¤nder cachad HTML/JS.
**Regel:** efter mallÃ¤ndring â†’ hÃ¥rd omladdning (**Ctrl+F5** / Ctrl+Shift+R), inte vanlig F5. Princip:
mÃ¤t disken (`Select-String`), tvinga skÃ¤rmen. OBS skillnaden: Ã¤ndringar i `app.py` (Python-kod) krÃ¤ver
server-**omstart**, inte bara omladdning â€” bara mallar och statiska filer plockas upp per request.
**GÃ¤ller om:** lokal Flask-app med mallar/statiska filer som serveras per request.
**FÃ¶rkroppsligas i:** `orchestration/webapp/` (dashboard).

| LB.62 | a | azure_run_model/ Ã¤r referens OCH skrivmÃ¥l â€” Ã¶verskrivningsfÃ¤lla | runner scp:ar output dit en facit-referens ocksÃ¥ ligger |
| LB.63 | a | Blob-output per datum, inte entitet â†’ familjekollision samma dag | flera familjer laddar upp output samma dag |
| LB.64 | a | --launch-test Ã¤rver inte poll-loopens tunneltolerans | launch-test mot nyss kallstartad VM pÃ¥ flaky tunnel |
| LB.65 | a | Data prep behÃ¶ver inte VM:ens RAM â€” bara modellstegen gÃ¶r det | man frestas lyfta icke-RAM-tungt steg till VM "fÃ¶r enhetlighet" |
| LB.66 | a | Artefakt i Blob = Ã¶verlevnad (icke-backad lokal dator), inte bekvÃ¤mlighet | vÃ¤g lokal bekvÃ¤mlighet mot artefakters Ã¶verlevnad |
| LB.67 | a | storage --auth-mode login ger TYST tomt utan dataplane-roll (â‰  403) | listar/lÃ¤ser Blob och fÃ¥r tomt svar |
| LB.68 | a | Ingen auto-shutdown pÃ¥ bcg-poc-vm â€” deallokera alltid manuellt | man rÃ¤knar med att VM:en stÃ¤nger av sig sjÃ¤lv |
| LB.69 | a | Flask "inget hÃ¤nde": gammal python-process serverar gammal kod | omstart utan synlig effekt |
| LB.70 | b | Modell-output lever i flera identiska kopior, ingen kanonisk plats | vÃ¤ljer fil fÃ¶r upload/jÃ¤mfÃ¶relse och flera finns |
| LB.71 | a | Webappen renderar statusfilens faser, inte STORY â€” ny familj krÃ¤ver fas i default_pipeline | en familj finns i STORY men syns inte i appen |
| LB.72 | a | PowerShell svÃ¤ljer citattecken/backslash i echo:ade kommandon med Windows-sÃ¶kvÃ¤gar; heredoc finns ej | Claude genererar PS/py-snutt med C:\-sÃ¶kvÃ¤g |
| LB.73 | a | BCG bundle model-data-creation bÃ¤r UK-miljÃ¶fotspÃ¥r: cp1252, uk_bundles, Qty/TotalNet, week=datetime | bundle-kedjan kÃ¶rs pÃ¥ Evidensia DuckDB-data (UTF-8, Clusters, str-datum) |
| LB.74 | a | Bundle model-data-creation: config.yml saknades + pekade pÃ¥ spÃ¶kfiler; sweden_bundles vs uk_bundles nyckel-mismatch | model-data-creation kÃ¶rs fÃ¶rsta gÃ¥ngen pÃ¥ vÃ¤xande data |
| LB.75 | a | Bundle tÃ¶mdes tyst: BCG:s ensidiga astype(str) pÃ¥ en gren ger datetime/str-divergens i intern slutmerge (instans av P.1/P.3) | bundle-output blir tom header trots att data flÃ¶dar till nÃ¤st sista steget |
| LB.76 | a | Diagnostisk sond > lager-fÃ¶r-lager: instrumentera kopia, mÃ¤t population efter varje steg, testa flera hypoteser parallellt, skriv till fil. **GÃ¤ller Ã¤ven egen infrastruktur/kontrakt** (statisk sond mot orkestrering/kod, ej bara datapipeline) â€” sond 4/5/6 (2026-06-22) kartlade orkestreringslagret + efter-kedjan tokenfritt och fann run-nivÃ¥-lÃ¤ckaget | en pipeline ELLER ett kodlager ger fel/tomt/oklart utan att krascha |
| LB.77 | a | Avsiktlig avvikelse maste markas pa platsen (annars ej skiljbar fran glomska) | du medvetet avviker fran BCG-originalet |
| LB.78 | a | Bundle-modellen var aldrig G7-patchad: hardkodad END_DATE kapar vaxande data tyst | en familjs constants.py kontrolleras ej mot de andras G7-fix |
| LB.79 | a | feature_selection skapar ej automl-mappar (OSError) - rensa ej output/model/* utan att aterskapa | output/model rensas fore D-korning |
| LB.80 | a | poll rapporterar running=True i minuter efter krasch - mat remote-logg + pgrep, ej poll | bedomer om en VM-korning lever |
| LB.81 | a | Bundle steg C (model-data-creation) kraschar lokalt (Ray/Windows) - kor pa VM | nagon kor bundle steg C lokalt |
---
### LB.65 â€” Data prep behÃ¶ver inte VM:ens RAM; bara modellstegen gÃ¶r det
**Symptom:** Sessionen 2026-06-15 utgick frÃ¥n "data prep via Azure", svÃ¤llt ur det sanna skÃ¤let att
VM sattes upp (lokal OOM pÃ¥ Stage 2, modellstegen). KÃ¤llÃ¤sning visade att DuckDB-data-prep kÃ¶rts rent
lokalt vÃ¤xande (run_dataprep_growing.txt, 642s, sex filer, ingen OOM); parquet-regenereringen Ã¤r
chunkad just fÃ¶r lÃ¥gt toppminne.
**Rotorsak:** En sann premiss ("tunga jobb behÃ¶ver RAM â†’ VM") applicerades fÃ¶r brett ("allt pÃ¥ VM").
Bara Ray-modellstegen (cluster/site/bundle, feature_selection) var OOM-orsaken; DuckDB spiller till
disk och klarar data stÃ¶rre Ã¤n RAM.
**Regel:** VM:en Ã¤r till fÃ¶r Ray-modellstegens RAM, inte fÃ¶r data prep. Data prep kÃ¶rs lokalt â€” och
MÃ…STE det (DW nÃ¥s ej frÃ¥n VM, LB.58). Skilj "vilket jobb Ã¤r tungt" frÃ¥n "allt i samma miljÃ¶".
**GÃ¤ller om:** man frestas lyfta ett icke-RAM-tungt steg till VM "fÃ¶r enhetlighetens skull".
**FÃ¶rkroppsligas i:** arkitekturbeslutet (data prep lokalt â†’ Blob â†’ VM lÃ¤ser modell-input).

### LB.66 â€” Parqueten i Blob Ã¤r Ã¶verlevnad, inte bekvÃ¤mlighet
**Symptom:** Ã…terkommande dragning att lÃ¤gga data prep i Azure trots att den kÃ¶rs snabbt lokalt.
**Rotorsak (Jens kontext 2026-06-15):** Den lokala datorn Ã¤r en icke sÃ¤kerhetskopierad enpunktsrisk
som fÃ¶rsvinner nÃ¤r Jens lÃ¤mnar bolaget. OneDrive-synk fungerar inte med pythonkedjan (krÃ¤ver lokalt
arbete utan backup). Git bÃ¤r koden, men Excel-/stora artefakter Ã¤r otrackade (fÃ¶r stora, affÃ¤rsdata,
ignoreras vid push). Azure Blob Ã¤r den IT-godkÃ¤nda, sÃ¤kerhetskopierade miljÃ¶n fÃ¶r INPUT och OUTPUT.
**Regel:** Artefakter (parquet, output-Excel) ska till Blob fÃ¶r att Ã–VERLEVA utvecklaren, Ã¤ven nÃ¤r
berÃ¤kningen sker lokalt. "KÃ¶r dÃ¤r du mÃ¥ste (DW-tvÃ¥ng), lagra dÃ¤r det Ã¶verlever." Detta Ã¤r skÃ¤let
projektet lever i Azure, skilt frÃ¥n berÃ¤knings-skÃ¤let (RAM).
**GÃ¤ller om:** man vÃ¤ger lokal bekvÃ¤mlighet mot artefakters Ã¶verlevnad â€” Ã¶verlevnad vinner.
**FÃ¶rkroppsligas i:** blob.py upload_inputs, input-containern.

### LB.67 â€” storage --auth-mode login returnerar tyst tomt utan dataplane-roll (ABAC)
**Symptom:** `az storage container list --auth-mode login` gav TOMT svar (ingen rad, inget fel).
`--auth-mode key` listade input/output/runstatus korrekt.
**Rotorsak:** Control-plane-Owner â‰  dataplane-lÃ¤sare. Listning av containrar Ã¤r en dataplane-operation
som krÃ¤ver Storage Blob Data-roll (ABAC-blockerad). AAD-vÃ¤gen nekar TYST (tom lista), inte med 403.
**Regel:** FÃ¶r dataplane (lista/lÃ¤sa/skriva blob-innehÃ¥ll) anvÃ¤nd kontonyckel-lÃ¤get (--auth-mode key /
PRICINGMODEL_AUTH=key) tills AAD-datarollen finns (Kent). Tomt svar frÃ¥n --auth-mode login Ã¤r INTE
"kontot Ã¤r tomt" â€” det Ã¤r saknad dataplane-roll. Verifiera med nyckel-lÃ¤get innan slutsats.
**GÃ¤ller om:** man listar/lÃ¤ser Blob och fÃ¥r tomt â€” testa nyckel-lÃ¤get innan slutsats.
**FÃ¶rkroppsligas i:** blob.py (_AUTH_MODE=key som dokumenterad skuld).
**Generell version:** kandidat fÃ¶r MASTER_AZURE (korsar projektgrÃ¤ns â€” se eskalering nedan).

### LB.68 â€” Ingen auto-shutdown pÃ¥ bcg-poc-vm (motbevisar minnesantagande)
**Symptom:** Antagandet "VM:en stÃ¤ngs av automatiskt efter x timmar" levde. VM:en hade kÃ¶rt ~2h
utan att stÃ¤ngas.
**Rotorsak:** `az resource show ... Microsoft.DevTestLab/schedules/shutdown-computevm-bcg-poc-vm`
â†’ ResourceNotFound. Ingen auto-shutdown konfigurerad. (Ã„ven om en fanns triggar auto-shutdown pÃ¥ fast
klockslag, inte "x timmar efter start" â€” skyddar mot nattglÃ¶mska, inte dagsdrift.)
**Regel:** Manuell `deallocate` Ã¤r ENDA skyddet mot lÃ¶pande VM-kostnad. Lita aldrig pÃ¥ ett antaget
auto-skydd. Samma klass som LB.60 (antaget tillstÃ¥nd ser identiskt ut med verifierat).
**GÃ¤ller om:** man rÃ¤knar med att VM:en "skÃ¶ter sig sjÃ¤lv" kostnadsmÃ¤ssigt â€” det gÃ¶r den inte.
**FÃ¶rkroppsligas i:** STATE (VM-rad), FD.16 (automatiskt skyddsnÃ¤t, framtid).

### LB.69 â€” Flask "inget hÃ¤nde": en gammal python-process serverar gammal kod
**Symptom:** story_config/dashboard Ã¤ndrad, fil inflyttad, app "omstartad" â€” men appen visar gammalt.
Bet tre gÃ¥nger denna session (2026-06-16).
**Rotorsak:** en TIDIGARE python-instans dog aldrig; den fortsÃ¤tter serva gammal kod pÃ¥ porten
(eller blockerar porten sÃ¥ ny instans inte binder). `Get-Process python*` visade tvÃ¥ processer med
olika StartTime.
**Regel:** fÃ¶re omstart av Flask-appen ALLTID `Get-Process python* | Stop-Process -Force`, verifiera
att listan Ã¤r TOM, starta sedan EN instans. Browsercache (Ctrl+Shift+R) Ã¤r en SEPARAT bov; /api/story
cachas hÃ¥rdare â€” inkognito vid behov (LB.61-grannlÃ¤ra).
**GÃ¤ller om:** man itererar pÃ¥ webappen och startar om utan att dÃ¶da gammal process.
**FÃ¶rkroppsligas i:** session-close-checklista; LB.61 (mall-cache, samma symptomklass).

### LB.70 â€” Modell-output lever i flera identiska kopior; faststÃ¤ll kanonisk plats
**Symptom:** cluster vÃ¤xande output_summary fanns i 3 kopior, alla 4180 KEY (identiska): 
`_archive_growing_2026-04-27_v2_pg4fix\`, `output\azure_run_model\`, `output\output_summary_ready.xlsx`.
verify_tool-verktygen pekade pÃ¥ OLIKA kopior (rationalityâ†’arkiv, proof_chainâ†’azure_run_model).
**Regel:** faststÃ¤ll EN kanonisk vÃ¤xande output-fil per familj fÃ¶re blob-upload/jÃ¤mfÃ¶relse, annars
speglas kopie-fÃ¶rvirringen. BekrÃ¤fta att kopiorna Ã¤r identiska via KEY-antal. Den fil verify_tool
senast validerade (kvittots "Path:"-rad) Ã¤r rÃ¤tt kandidat (source-before-hypothesis). BÃ¤ttre Ã¤ndÃ¥:
spegla lokal struktur rakt av med overwrite (vÃ¤xande kÃ¶r Ã¶ver gammalt) â€” dÃ¥ finns bara en sanning.
**GÃ¤ller om:** ett modellsteg kÃ¶rts/sparats flera gÃ¥nger i flera mappar.
**FÃ¶rkroppsligas i:** FD.33 (blob-spegling), upload_pipeline_mirror.py.


### LB.71 â€” Webappen renderar statusfilens faser, inte STORY-posterna
**Symptom:** bundle lades i story_config (STORY + FUNNEL), appen startades om â€” men bundle
syntes inte i Motor-sektionen. story_config var korrekt; /api/story serverade bundle.
**Rotorsak (mÃ¤tt 2026-06-16):** dashboard.html itererar `d.phases` (statusfilen frÃ¥n Blob)
och matchar mot STORY enbart fÃ¶r gruppering (`(STORY[p.key]||{}).group===gkey`). En familj
renderas ENDAST om den Ã¤r en fas i statusfilen â€” att finnas i STORY/FUNNEL rÃ¤cker inte.
**Regel:** en ny modellfamilj/steg krÃ¤ver TRE stÃ¤llen fÃ¶r att synas: (1) `default_pipeline`
i run_status.py (PERMANENT â€” framtida kÃ¶rningar fÃ¥r fasen), (2) story_config STORY+FUNNEL
(app-data + tratt), (3) ev. handpatch av befintliga statusfiler i Blob (fÃ¶r att se den i
GAMLA kÃ¶rningar). GlÃ¶m inte (1) â€” utan den fÃ¶rsvinner fasen vid nÃ¤sta riktiga kÃ¶rning, Ã¤ven
om (2)+(3) gÃ¶r att den ser klar ut nu. PHASE_RECEIPT (app.py) behÃ¶vs dessutom fÃ¶r att
drill-3-kvitton ska hittas.
**GÃ¤ller om:** en ny familj/fas ska synas i statusdashboarden.
**FÃ¶rkroppsligas i:** FD.34 (bundle-aktiveringens fyra stÃ¤llen).

### LB.72 â€” PowerShell svÃ¤ljer citattecken i echo:ade kommandon med Windows-sÃ¶kvÃ¤gar
**Symptom:** ett genererat PowerShell/Python-kommando med `C:\Projekt\...`-sÃ¶kvÃ¤g, echo:at
eller klistrat, kraschar: citattecken faller bort, `\v`/`\r`/`\b` tolkas som escape, eller
`The '<' operator is reserved for future use` (heredoc `<< EOF` finns INTE i PowerShell â€”
det Ã¤r bash). Bet 5+ gÃ¥nger under sessionen 2026-06-16.
**Rotorsak:** att bygga ett kommando via ett mellanled (echo, generator) som innehÃ¥ller
Windows-sÃ¶kvÃ¤gar med backslash + inbÃ¤ddade citattecken fÃ¶rvrÃ¤nger strÃ¤ngen innan PowerShell
ens kÃ¶r den. Samma familj som SSH-quoting-fÃ¤llan (LB-grannlÃ¤ra).
**Regel:** leverera PowerShell-kommandon som RENA block (inte echo:ade), och Python-snuttar
som FILER: `@'...'@ | Out-File -FilePath $env:TEMP\x.py -Encoding utf8` fÃ¶ljt av
`py -3.11 $env:TEMP\x.py`. ALDRIG `py -3.11 -c "..."` med Windows-sÃ¶kvÃ¤g inuti. Heredoc
existerar inte i PowerShell â€” anvÃ¤nd here-string `@'...'@`.
**GÃ¤ller om:** Claude genererar PowerShell/Python-snuttar som innehÃ¥ller Windows-sÃ¶kvÃ¤gar.
**FÃ¶rkroppsligas i:** alla leveranser efter upptÃ¤ckten denna session (here-string-mÃ¶nstret).

### LB.73 â€” BCG bundle model-data-creation bÃ¤r UK-miljÃ¶fotspÃ¥r
**Symptom:** bundle:s `2.Sweden_Bundle_Clinic_Model_Data_Creation.py` + `bundle_utils.py` brÃ¶ts pÃ¥
fyra olika stÃ¤llen nÃ¤r de kÃ¶rdes pÃ¥ Evidensias vÃ¤xande data: (1) `pd.read_csv(encoding="cp1252")`
kraschade pÃ¥ UTF-8-tecken (`0x9d`); (2) config-nyckel `uk_bundles` vs skriptets `sweden_bundles`;
(3) aggregering pÃ¥ `Qty`/`TotalNet` medan datan har `SoldQuantity`/`SalesTotal`; (4) `week_starting_monday`
antas datetime genomgÃ¥ende medan DuckDB-output Ã¤r str.
**Rotorsak:** modellen Ã¤r Ã¥teranvÃ¤nd frÃ¥n ett tidigare BCG-klientprojekt (UK/IVC â€” `module_path`-kommentar
pekade pÃ¥ `D:\IVC E Phase 1\...Mohammed Moheed Tai\`, utkommenterad `UK_bundle_cluster`-rad). Ytan
anpassades fÃ¶r Sverige men inte djupet â€” miljÃ¶antaganden (encoding, kolumnnamn, datatyper) Ã¤r fotspÃ¥r
frÃ¥n ursprungsmiljÃ¶n, inte medvetna val fÃ¶r Evidensia.
**Regel:** anpassa ALLTID vÃ¥r data till BCG:s antaganden vid INLÃ„SNINGSPUNKTEN (load_and_clean_transactions
+ fte-inlÃ¤sning i huvudskriptet), aldrig genom att Ã¤ndra BCG:s nedstrÃ¶mslogik. Encodingâ†’utf-8, kolumnnamn-
rename, datatyp-normalisering hÃ¶r alla hemma dÃ¤r. Additivt (bevara BCG:s ursprungstanke parallellt:
`if 'Cluster' ... and 'Clusters' not in`).
**GÃ¤ller om:** en BCG-modellkomponent kÃ¶rs pÃ¥ data frÃ¥n en annan pipeline Ã¤n ursprungets (â‰ˆ all vÃ¤xande drift).
**FÃ¶rkroppsligas i:** bundle_utils.py + 2.Sweden_Bundle_Clinic_Model_Data_Creation.py (additiva fixar 2026-06-17).

### LB.74 â€” Bundle model-data-creation: saknad config + spÃ¶kreferenser
**Symptom:** skriptet lÃ¤ser `src/config.yml` â€” filen fanns inte (bara `config_data_prep.yml`). Den
configen pekade pÃ¥ `0826_raw_data_basket_analysis_Clinic_Hospital.csv` (finns ej) och hade nyckeln
`uk_bundles` (skriptet vill `sweden_bundles`). Dessutom: dry-run/preflight var GRÃ–N (runnern pekade rÃ¤tt)
men input var fryst/saknad â€” preflight testade att runnern PEKAR rÃ¤tt, inte att DATAN fanns i rÃ¤tt version.
**Rotorsak:** bundle parkerades (FD.11) â€” runner/app/fas byggdes (FD.34) men den vÃ¤xande databygges-kedjan
(dataprepâ†’model-data-creationâ†’xlsxâ†’VM) intrimmades aldrig. Kopplingarna var gjorda fÃ¶r BCG:s engÃ¥ngskÃ¶rning.
**Regel:** (1) skapa config.yml mot VERIFIERADE filer (mÃ¤t vad som finns, peka inte pÃ¥ spÃ¶ken); BOM-fri
(`UTF8Encoding $false` â€” annars kraschar yaml.safe_load). (2) En grÃ¶n dry-run som testar att en runner
PEKAR rÃ¤tt bevisar inte att datan EXISTERAR i rÃ¤tt version â€” framtida dry-run bÃ¶r verifiera input-filens
DATUMSPANN (vÃ¤xande vs fryst), inte bara dess existens.
**GÃ¤ller om:** en parkerad komponent Ã¥teraktiveras, eller en config Ã¤rvs frÃ¥n ursprungsmiljÃ¶n.
**FÃ¶rkroppsligas i:** src/config.yml (skapad 2026-06-17, Evidensia-sÃ¶kvÃ¤gar).

### LB.75 â€” Bundle tÃ¶mdes tyst pÃ¥ datetime/str-divergens i intern slutmerge (instans av P.1/P.3)
**Symptom:** bundle model-data-creation gav "Pipeline completed" men `Bundle_Clinic_Data.csv` hade
1 rad (bara header) pÃ¥ vÃ¤xande data â€” ingen krasch, tyst tomt. Data flÃ¶dade till 314k rader genom steg 1-3,
men `process_bundles_with_fte` returnerade 0.
**Rotorsak (pinpointad via sond, LB.76):** funktionen bygger tvÃ¥ grenar â€” `txn_elasticity` (week behÃ¥lls
datetime) och `bundle_visits` (week â†’ str via BCG:s rad `txn_data_expected["week"] = ...astype(str)` efter
FTE-merge). Den interna slutmerge:n `txn_elasticity.merge(bundle_visits, on=[level,"week"])` fÃ¶renar dem â€”
men en gren har datetime, andra str (`"2022-06-27 00:00:00"` vs `"2022-06-27"`) â†’ noll matchningar â†’ tom.
BCG:s `astype(str)` trÃ¤ffar bara ena grenen. Fungerade pÃ¥ deras Alteryx-data (konsekvent datetime); brÃ¶ts
pÃ¥ vÃ¥r DuckDB-data. Detta Ã¤r exakt P.1 (likhetsvalidering utan tÃ¤ckningskontroll â€” tyst populationsbortfall)
+ P.3 (anta tyst filtrering). En bugg BCG sjÃ¤lva aldrig hittade, eftersom de aldrig kÃ¶rde pÃ¥ icke-Alteryx-data.
**Regel:** additiv typsÃ¤kring FÃ–RE slutmerge:n (bÃ¥da grenars nyckelkolumner â†’ samma typ), rÃ¶r inte BCG:s
befintliga rader. Generellt: misstÃ¤nk varje merge mellan grenar som behandlat en nyckelkolumn olika.
**GÃ¤ller om:** en funktion bygger flera grenar ur samma data och fÃ¶renar dem pÃ¥ en nyckel som genomgÃ¥tt
typ-/format-konvertering i bara en gren.
**FÃ¶rkroppsligas i:** bundle_utils.py (additiv weekâ†’datetime fÃ¶re rad 341, 2026-06-17). Bevis: 27 921 rader
vÃ¤xande output, datumspann 2022-07-04 â†’ 2026-04-27.

### LB.76 â€” Diagnostisk sond slÃ¥r lager-fÃ¶r-lager-felsÃ¶kning
**Symptom:** bundle-buggen tog en hel dag att lÃ¶sa lager fÃ¶r lager (inputâ†’configâ†’encodingâ†’beroendenâ†’
kolumnnamnâ†’minneâ†’datetime), dÃ¤r varje fix avslÃ¶jade nÃ¤sta â€” mycket tid gick till att UPPTÃ„CKA att det
fanns Ã¤nnu ett lager. Den verkliga roten (LB.75) hittades fÃ¶rst nÃ¤r vi bytte metod.
**Rotorsak:** reaktiv felsÃ¶kning (kÃ¶râ†’kraschaâ†’fixaâ†’upprepa) ser bara ett lager i taget. En pipeline med
flera tysta fel ger inte upp sin rot fÃ¶rrÃ¤n man fÃ¶ljer datan genom HELA kedjan i ett svep.
**Regel (sond-metodik):** nÃ¤r en pipeline ger fel/tomt men inte kraschar â€” bygg en sond:
(1) reproducera logiken inline i en KOPIA (rÃ¶r aldrig originalet); (2) mÃ¤t population/tillstÃ¥nd efter VARJE
transformation (tappet syns som "Nâ†’0" pÃ¥ en rad); (3) testa flera rotorsaks-hypoteser PARALLELLT i samma
kÃ¶rning (uppstrÃ¶ms filter/flaggor, mitten joins/aggregeringar, nedstrÃ¶ms datatyper/nycklar); (4) skriv till
FIL (brus som Ray-loggar begraver annars svaret); (5) kÃ¶r pÃ¥ minsta reproducerande enhet (en bundle/KEY).
**Formulering som triggar det snabbt (KÃ„RN-kandidat):** *"Bygg en sond som fÃ¶ljer datan steg fÃ¶r steg
genom [funktionen], mÃ¤t tillstÃ¥ndet efter varje transformation, och testa dessa hypoteser parallellt:
[H1 uppstrÃ¶ms], [H2 mitten], [H3 datatyp/nyckel]. RÃ¶r inte originalkoden."*
**GÃ¤ller om:** en pipeline ger ovÃ¤ntat/tomt resultat utan att krascha, sÃ¤rskilt Ã¶ver flera transformationssteg.
**FÃ¶rkroppsligas i:** sond-skripten som lÃ¶ste bundle 2026-06-17 (tvÃ¥ kÃ¶rningar gav exakt rad + uttÃ¶mda hypoteser).

## Hur listan vÃ¤xer

Ny lÃ¤rdom lÃ¤ggs till nÃ¤r vi snubblar Ã¶ver en teknisk fÃ¤lla â€” miljÃ¶, infrastruktur, kod-mekanik,
sÃ¶kvÃ¤g-divergens. En befintlig lÃ¤rdom **uppdateras** (med "Ã¤ndrad 2026-XX-XX") eller **om-tieras** om
regeln revideras eller dess fÃ¤lla stÃ¤ngs av ett verktyg/en fas â€” men tas inte bort (additiv fÃ¶r historik,
KÃ„RNPRINCIPER Â§4.7).

**Vid sessionsstart:** lÃ¤s **tier-a** i snabbindexet (aktiva fÃ¤llor) â€” inte hela listan. Tier-b lever i
sina verktyg, tier-c Ã¤r arkiv.

**Vid sessionsslut (KÃ„RNPRINCIPER Â§6.6-prÃ¶vning):** Ã¶vervÃ¤g om sessionen gav en ny LB. Ã„r den en *instans*
av en befintlig KÃ„RNPRINCIP (P.1-P.4, R7, A.9, miljÃ¶disciplin) â†’ lÃ¤gg den hÃ¤r som konkret exempel men
befordra inte regeln; regeln bor i KÃ„RN. Ã„r den generell Ã¶ver projekt â†’ befordra till MASTER och lÃ¥t LB
peka dit. Noll nya LB Ã¤r ofta rÃ¤tt.

**Konkreta instanser av "MÃ¤t, gissa inte" (KÃ„RN Â§8.4) i detta projekt** â€” mekanismen bor i KÃ„RN, dessa Ã¤r
bevisen som motiverar den: (1) **kÃ¤llidentitet** â€” `transaction_data` kommer frÃ¥n `Fact_BillingInvoiceRows`
JOIN `Dim_Item`, bevisad per kod (median-kvot 1,0000), inte den fÃ¶rst antagna tabellen. (2) **net/brutto** â€”
`SalesTotal` Ã¤r brutto (`SalesExVAT Ã— 1,25`), inte lika med `SalesExVAT`; AI:ns fÃ¶rsta gissning var fel.
(3) **L4** â€” `ProductGroupL4Name` fanns inte i DW som antaget; mÃ¤tning avgjorde. Alla tre: kolumnnamn och
minnesbild ljÃ¶g, mÃ¤tning mot referens avgjorde.

---

*Skapad 2026-05-23 vid dokumentstruktur-omtaget; extraherad ur SESSION_*-filer. LB.29-30 tillagda
2026-05-29 efter session dÃ¤r verify_tool-fÃ¤llan och venv-divergensen upptÃ¤cktes och dokumenterades.
LB.31-37 tillagda 2026-06-02 efter sessionen dÃ¤r full lokal cluster-kÃ¶rning OOM:ade, VM
fÃ¶rbereddes, och check_env-verktyget byggdes (commits `74f1ab0` + `ef258e5`). LB.38-43 tillagda 2026-06-08 efter VM-kÃ¶rning av cluster pipeline med pg4-fix. LB.44-47 tillagda 2026-06-10 efter F.8 Site kÃ¶rd end-to-end pÃ¥ vÃ¤xande data (steg 1-4 VM, steg 5 lokalt): Excel-stegen kÃ¶rs lokalt (LB.44), write_df_preserve_named_range com_error-fix (LB.45), Azure subscription-fÃ¤llan (LB.46), scp mellanslags-sÃ¶kvÃ¤g (LB.47). LB.40 bekrÃ¤ftad familje-oberoende pÃ¥ Site â€” 4180 KEY producerade inklusive AAP130 med elasticitet -0.52 p=0.001 (end-to-end-bevis kommiterad i `7e0f11f`..`89b9467`). LB.48-51 tillagda 2026-06-11 efter F.9 Bundle-dataprep kÃ¶rd vÃ¤xande + Bundle-modellen datadrivet parkerad (FD.11): lÃ¤s runnern fÃ¶re patch-deklaration (LB.48), all_varchar vid masterdata-parquet-konvertering (LB.49), dubbel-fÃ¶nster-fÃ¤llan/konstant-ankare (LB.50, DRIFT), BCG-kod UK-rester + config-verifiering fÃ¶re kÃ¶rning (LB.51). Bundle-dataprep committad i `1daf093`. LB.52-53 tillagda 2026-06-11 efter F.10 Step 6 kÃ¶rd fÃ¶rsta gÃ¥ngen pÃ¥ vÃ¤xande data (Alternativ A): KEY-split-fÃ¤llan i blended_model (LB.52), xlwings named-range com_error pÃ¥ mall-skrivning (LB.53). Step 6 producerade 108 979 rader / 15 128 ProductKeys, median final_elasticity -0.497, 100% negativa.*

### LB.77 â€” Avsiktlig avvikelse mÃ¥ste mÃ¤rkas pÃ¥ platsen (annars gÃ¥r den ej att skilja frÃ¥n glÃ¶mska)
**Symptom:** sond 5 (kontrakts-integritet) flaggade `succeed()` som dÃ¶d kod (0 anrop), tre fas-nycklar
saknade i `PHASE_RECEIPT`, och 24+ nakna `except: pass`/`log.warning`. Var och en KAN vara medveten â€”
men inget i koden sa det, sÃ¥ en sond (eller en eftertrÃ¤dare) kan inte skilja avsikt frÃ¥n olycka.
**Rotorsak:** en utelÃ¤mnad nyckel, en oanropad metod, ett svalt fel ser EXAKT likadant ut oavsett om
det var ett designval eller en miss. FrÃ¥nvaro Ã¤r tyst; tystnad bÃ¤r ingen avsikt.
**Regel:** gÃ¶r avsikt MÃ„TBAR (spegelbild av "mÃ¤t, gissa inte", KÃ„RN Â§8.4). Ã„r nÃ¥got medvetet utelÃ¤mnat
eller medvetet tomt â€” sÃ¤g det pÃ¥ platsen: en kommentar vid `except`, en markering vid den utelÃ¤mnade
nyckeln, en docstring vid den kvarhÃ¥llna metoden. DÃ¥ blir en REVIEW-flagga frÃ¥n en sond ett svar
("medvetet, se rad X"), inte en utredning. Det som inte Ã¤r mÃ¤rkt behandlas som glÃ¶mska tills motsatsen
bevisas.
**GÃ¤ller om:** kod bÃ¤r avsiktliga avvikelser (utelÃ¤mnade fÃ¤lt, kvarhÃ¥llen dÃ¶d kod, medvetet svalda fel)
som en granskare/sond inte kan hÃ¤rleda avsikten bakom.
**FÃ¶rkroppsligas i:** `verify_tool/probes/contract_integrity.py` (sond som flaggar omÃ¤rkta avvikelser);
`orchestration/shared/run_status.py` (`finalize`-docstring fÃ¶rklarar varfÃ¶r `succeed` Ã¤r fÃ¶rÃ¥ldrad).
*Instans/spegelbild av KÃ„RN "gÃ¶r avsikt mÃ¤tbar". succeed() ska stÃ¤das nÃ¤sta session: tas bort eller
mÃ¤rkas kvarhÃ¥llen â€” sjÃ¤lva poÃ¤ngen med denna lÃ¤rdom.*

*LB.73-76 tillagda 2026-06-17 efter sessionen dÃ¤r bundle:s vÃ¤xande databygge intrimmades end-to-end och en
tyst tÃ¶mnings-bugg i BCG:s `process_bundles_with_fte` spÃ¥rades till rotorsak (datetime/str-divergens i intern
slutmerge, rad 341) via diagnostisk sond. Bundle model-data-creation producerar nu 27 921 rader vÃ¤xande output
(datumspann â†’ 2026-04-27). Fyra BCG-miljÃ¶fotspÃ¥r dokumenterade (LB.73), config-/dry-run-lucka (LB.74), rotorsak
+ additiv fix (LB.75), sond-metodik (LB.76, KÃ„RN-kandidat). Alla fixar additiva vid inlÃ¤sningspunkten â€”
BCG:s nedstrÃ¶mslogik orÃ¶rd.*

*Omstrukturerad 2026-06-13: tier-kolumn (a/b/c) infÃ¶rd i snabbindexet â€” sessionsstart lÃ¤ser bara tier-a;
`GÃ¤ller om`- och `FÃ¶rkroppsligas i`-fÃ¤lt tillagda i formatet (KÃ„RNPRINCIPER Â§4.6/Â§7); LB.59-61 infogade
(Phase Z frontyta â€” run_id-kollage, power-state-verifiering, Flask-mall-cache); LB.54-58 rekonstruerade
frÃ¥n referens (deras brÃ¶dtext saknades i kÃ¤llfilen â€” markerade fÃ¶r verifiering mot ursprungssession);
index-rader korsrefererar nu motsvarande KÃ„RNPRINCIP/MASTER_AZURE-post dÃ¤r LB:n Ã¤r en instans; bolagsnamn
borttaget ur utvecklarrad. InnehÃ¥ll i LB.1-53 ofÃ¶rÃ¤ndrat.*

*LB.77 tillagd + LB.59 stÃ¤ngd + LB.35/76 utvidgade 2026-06-22 efter sessionen dÃ¤r orkestrerings-motorn
validerades med tre statiska sonder (infrastructure_map, contract_integrity, after_chain_probe),
run_id Ã¤ndrades till datafÃ¶nster (window_run_id) och RunStatus.finalize() byggdes (heartbeat-spÃ¶ket
dÃ¶tt). succeed() fÃ¶rÃ¥ldrad â€” stÃ¤das nÃ¤sta session.*

---

### LB.78 â€” Bundle-modellen var aldrig G7-patchad (hÃ¥rdkodad END_DATE kapade vÃ¤xande data)

**Symptom:** bundle-modellen kÃ¶rdes pÃ¥ maj-input (xlsx â†’ 2026-05-25) men `data_for_model.csv`
slutade 2025-06-23 (BCG:s frysta fÃ¶nster). model.py loggade "Finished model.py in 6.57 sec"
utan att producera output. Tre tidigare kÃ¶rningar gav identisk april-revenue maskerad som maj.

**Rotorsak:** bundle constants.py (`5. Bundle Clinic Models/code/`) hade HÃ…RDKODADE datum
(`START_DATE='2022-07-01'`, `END_DATE='2025-06-29'`, `END_DATE2='2025-06-30'`), anvÃ¤nda som
filter i model.py L482 och regular_price.py L224: `df[(week >= START_DATE) & (week < END_DATE2)]`.
Cluster + Site G7-patchades i FAS 13 (LB-G7-klassen); **bundle missades.** Bundle-runnern
injicerade redan `export BCG_START_DATE/BCG_END_DATE` korrekt (run_bundle_model L150), men
constants.py lÃ¤ste aldrig env:en â†’ END_DATE fÃ¶rblev 2025-06-29 â†’ maj kapades.

**Regel:** alla tre familjers constants.py ska ha env-override (`os.environ.get("BCG_END_DATE",
"2025-06-29")`) + `END_DATE2` HÃ„RLEDD via datetime (+1 dag), aldrig hÃ¥rdkodad separat. Tomma
env-vars = BCG fryst (bit-identisk repro). Horisontell validering: nÃ¤r en familj patchas, kontrollera
de andra TVÃ… samma session â€” denna lÃ¤rdom uppstod just fÃ¶r att bundle aldrig kontrollerades mot
cluster/site-fixen.

**GÃ¤ller om:** den hÃ¥rdkodade-datum-arkitekturen finns kvar (deaktiveras om BCG byter datummodell).

**FÃ¶rkroppsligas i:** `tools/patch_bundle_constants_g7.py` (idempotent env-override-patch, speglar
cluster), bundle/site/cluster `constants.py` (alla tre nu env-Ã¶verbara).

---

### LB.79 â€” feature_selection skapar inte sina automl-mappar (OSError om output rensats)

**Symptom:** efter G7-fix nÃ¥dde feature_selection automl-iterationen men kraschade med
`RayTaskError(OSError)` inuti en Ray-worker, vid `to_excel(f"{summary_path}{mg}_All_itrs.xlsx")`
(feature_selection.py rad 338). Pipeline dog efter ~24 sek.

**Rotorsak:** feature_selection skriver en xlsx per model-group till `output/model/automl/` men har
INGEN `os.makedirs` â€” mappen mÃ¥ste finnas. Egen cleanup (`rm -rf output/model/*`) raderade den.
FAS 18 (april) hade automl-mappen kvar sedan en tidigare kÃ¶rning, sÃ¥ felet syntes aldrig dÃ¥ â€”
det dÃ¶k upp fÃ¶rst nÃ¤r vi rensade output rent infÃ¶r maj.

**Regel:** fÃ¶re D-kÃ¶rning, skapa automl-mappstrukturen om den saknas:
`mkdir -p ~/bcg/bundle/output/model/automl/details ~/bcg/bundle/output/model/automl/results
~/bcg/bundle/output/model/model_objects`. Generellt: rensa ALDRIG output/model/* utan att
Ã¥terskapa mappstrukturen modellen skriver till. (Permanent kandidat: patcha feature_selection med
`os.makedirs(summary_path, exist_ok=True)`.)

**GÃ¤ller om:** feature_selection saknar egen makedirs (deaktiveras om den patchas att skapa mappen).

**FÃ¶rkroppsligas i:** `BUNDLE_KEDJAN_KARTLAGD.md` Â§7, bundle-kÃ¶rschemat (mkdir-steg i fÃ¶rkrav D).

---

### LB.80 â€” poll rapporterar running=True i minuter efter att jobbet kraschat

**Symptom:** run_bundle_model:s poll visade "poll: running=True | Finished data_prepration.py" i
28 minuter EFTER att pipelinen kraschat (remote-loggen visade pipeline dÃ¶d efter 24 sek, pgrep
visade ingen launcher-process). Vi vÃ¤ntade i onÃ¶dan, och trodde flera gÃ¥nger att en kÃ¶rning
arbetade nÃ¤r den var dÃ¶d.

**Rotorsak:** poll-mekanismen lÃ¤ser senaste klara steget ur loggen men upptÃ¤cker inte
process-dÃ¶d (ingen pgrep-koll i poll-loopen). En kraschad pipeline lÃ¤mnar "Finished
data_prepration.py" som sista rad â†’ poll upprepar den + running=True i all evighet.

**Regel:** lita ALDRIG pÃ¥ poll-raden fÃ¶r sann kÃ¶rstatus. MÃ¤t direkt:
`ssh ... 'tail -20 ~/bcg/logs/<run_id>_p1_bundle.log; pgrep -af launcher.py || echo INGEN'`.
Remote-logg (visar Error/Traceback) + pgrep (visar liv) = sanning. Samma klass som LB.60
(verifiera mot faktiskt tillstÃ¥nd, ej logg-/antagande).

**GÃ¤ller om:** poll-loopen saknar process-livskoll (deaktiveras om poll fÃ¥r pgrep-verifiering).

**FÃ¶rkroppsligas i:** `BUNDLE_KEDJAN_KARTLAGD.md` Â§8, `verify_tool/probes/bundle_model_output_sond.py`
(mÃ¤ter faktisk output istÃ¤llet fÃ¶r att lita pÃ¥ poll).

---

### LB.81 â€” Bundle steg C (model-data-creation) Ã¤r ett VM-steg, ej lokalt (Ray-krasch pÃ¥ Windows)

**Symptom:** `2.Sweden_Bundle_Clinic_Model_Data_Creation.py` kraschade lokalt pÃ¥ Windows med
`Windows fatal exception: access violation` i Ray:s remote_function.py, vid
`all_bundle_data_creation` (bundle_utils.py ~rad 151), pÃ¥ `build_bundle_for_type.remote()`.

**Rotorsak:** model-data-creation anvÃ¤nder Ray (`@ray.remote`, init med `num_cpus=12,
object_store_memory=2 GB`). Lokala maskinen (31 GB) klarar inte Ray:s shared-memory-allokering
â†’ access violation. Samma minnesvÃ¤gg som hela modell-pipelinen (varfÃ¶r VM finns). Bevisat
identiskt 2026-06-24 OCH FAS 18. Den lokala bundle_weekly_model...xlsx (2025-10-03 = BCG-original)
var aldrig omskriven lokalt â€” bekrÃ¤ftar att xlsx:en alltid byggts pÃ¥ VM.

**Regel:** bundle steg C kÃ¶rs ALLTID pÃ¥ VM (`~/bcg/bundle_dataprep/`, via `~/bcg/cluster/.venv`).
Lokalt kÃ¶rs BARA steg A + B (DuckDB, ej Ray). Bundle korsar miljÃ¶er: A/B lokalt, C/D pÃ¥ VM, E lokalt.

**GÃ¤ller om:** lokala maskinen saknar RAM fÃ¶r Ray (deaktiveras pÃ¥ en maskin med tillrÃ¤ckligt minne).

**FÃ¶rkroppsligas i:** `BUNDLE_KEDJAN_KARTLAGD.md` Â§3, `verify_tool/probes/bundle_chain_validator.py`
(H1 FAIL-flaggar lokal kÃ¶rning av steg C).

