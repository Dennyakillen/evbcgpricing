# KANSLIGHETSREGISTER — vad i BCG-prisverktyget som kan vara känsligt, var det ligger och vem som beslutar

*Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB). Läge 2026-10-21. Byggt ur mätning, inte ur minnet:
spegelmanifestet 2026-10-20, `git ls-files` och git-historiken (174 commits), kolumnnamn och värdenas form i datafilerna (antal
ifyllda, unika, namn- och e-postform — inga värden har lästs ut) och lagringskontots inställningar, allt 2026-10-21.*

## Syfte och mandat

Registret är underlag för att IT själv ska kunna bedöma informationssäkerhet och dataskydd i verktyget. Det är **inte en juridisk
bedömning**. Klassen på varje rad är utvecklarens bedömning. Besluten ligger hos:

| Fråga | Beslutar |
|---|---|
| Får personuppgifterna lagras där de ligger, hur länge och vem får läsa dem | dataskyddsombudet / IT-säkerhet |
| Får BCG:s material ligga i Evidensias DevOps och Blob | avtalsägaren för BCG-uppdraget |
| Åtkomst, nätverk, nycklar, skydd mot radering | IT |

Öppna frågor till dem: §6.

## 1. Klasser

| Klass | Betyder |
|---|---|
| **RÖD** | personuppgifter — även pseudonymiserade (kund-, patient- och användar-id som kan kopplas till en person i DW) — eller åtkomstmedel (nycklar, lösenord) |
| **RÖD-arv** | inga personuppgifter, men identifierar verksamheten: klinik-id, kliniknamn, adress eller nyckeltal per klinik, i innehållet eller i filnamnet |
| **GUL** | intern affärsdata: priser, marginaler, volymer, elasticiteter, modellresultat, kvitton |
| **AVTAL** | BCG:s konsultmaterial: kod, metod och leveransfiler |
| **GRÖN** | inget känsligt |

## 2. Översikt per plats

| Plats | Högsta klass | Åtkomst styrs av |
|---|---|---|
| Azure DevOps-repot | AVTAL · RÖD-arv · GUL; en fil med anställdas arbetskontakter (§3, G3); dokumentationen namnger utvecklaren | DevOps-projektets behörigheter |
| Blob `evbcgpricinginput`, kanoniskt lager (`input`, `output`, `pipeline`, `receipts`, `runstatus`, `quarantine`) | **RÖD** (pseudonymiserat, §4 B4) | lagringskontots roller och kontonyckel (§5) |
| Blob `spegel/bcg_2026-10-20/` | **RÖD** (§4 B1–B5) | samma |
| Blob `spegel/historik/` (git-historiken) | **RÖD** (som repot, G3) | samma |
| VM `bcg-poc-vm`, disken | **RÖD** — arbetskopior under modellkörning; vad som ligger kvar är **omätt** | SSH-nyckel, VPN, roll på VM:en (`OFFBOARDING_KRITISKT.md` rad 5–6) |
| GitHub-repot (privat, på utvecklarens konto) | **RÖD** (samma som historiken) | utvecklarens konto — `OFFBOARDING_KRITISKT.md` rad 11 |
| DW (källan) | RÖD | DW-förvaltaren — utanför registret |

## 3. Git och DevOps

| # | Filgrupp | Klass | Mätt innehåll | Används av |
|---|---|---|---|---|
| G1 | Pipelinekoden (`Pipeline/**/code/`, `**/scripts/*.sql`, konfiguration) | AVTAL | BCG:s kod, anpassad av Evidensia | kedjan |
| G2 | Klustringens indata `Pipeline/01. Clustering/Sweden_clustering_SQL/input/`: NPS per kostnadsställe och månad (83 rader), konkurrentpriser per klinik (2 104), konkurrenter och koordinater per klinik (74), befolkning per upptagningsområde (75), FTE per bolag, kostnadsställe och månad (4 263) | RÖD-arv | värden per klinik eller kostnadsställe — inga personnamn och inga enskilda enkätsvar. FTE för mycket små kostnadsställen kan ligga nära enskilda personer | klustringen (`scripts/00_read.sql`) |
| G3 | `…/input/Sweden_Hospitals_cluster_business_area_mapping.csv` (72 kliniker) | **RÖD** (låg: arbetskontakter) | klinik-id, kliniknamn, adress, affärsområde — och anställdas namn och e-post: `BusinessAreaManager` (4 namn), `DepartmentManager` (58 namn/e-post), `ChiefVeterinarian` (37 e-post), `ByUser` (1 e-post). Klustringen läser inte dessa kolumner ur filen; chefskolumnerna i `01_process.sql` hämtas ur `loc.Dim_Department` (B3). Beslut 2026-10-21 (Jens): filen följer med oförändrad, dokumentationen räcker | klustringen |
| G4 | PREP:s indata `Pipeline/02. Elasticity/Sweden_Elasticity_Data_Prep_SQL/input/`: klinik → kluster (58 och 75 rader), interpolerad produktiv tid per klinik och vecka (9 184) | RÖD-arv | klinik-id och FTE per klinik och vecka | PREP |
| G5 | Valideringskvitton `verify_tool/receipts/**.xlsx` (12) | GUL | aggregerade jämförelser mot BCG | dashboarden |
| G6 | Övrig kod, konfiguration och dokumentation | GUL / GRÖN | interna tabell- och kolumnnamn, nyckeltal i text | — |
| G7 | Undantas från DevOps (exportens beslutsfil): arkiven `_ATT_RADERA/`, `archives/`, inventeringsfiler med klinikkoder i filnamnen, utvecklingsverktyg | RÖD-arv / GUL | — | finns bara i historiken |

**Åtkomstuppgifter:** ingen `.env` och inga nyckel-, signatur-, lösenords- eller privata nyckelformer i någon av historikens 174
commits (mätt 2026-10-21). `tools/dw/.env` (DW-server och databas) finns medvetet bara lokalt; mallen `tools/dw/.env.example` ligger i git.

## 4. Blob

| # | Filgrupp | Var | Klass | Mätt innehåll (kolumner, inga värden) | Används av |
|---|---|---|---|---|---|
| B1 | `loc.DIM_Customer 20250627.csv` (161 MB) | spegel, `…/Sweden_Elasticity_Data_Prep_SQL/input/` | **RÖD** | kund-id, kund sedan, ort, land, kundtyp, aktiv, första och senaste faktura, organisationsnamn, momsregistreringsnummer (för enskild näringsidkare bygger det på personnumret; om fältet är ifyllt för sådana är omätt) | **ingen kod** (bara bortkommenterat i `01_process.sql`) — speglad för att inget skulle försvinna (beslut 2026-10-20) |
| B2 | `loc.DIM_Patient.csv` (578 MB) | samma | **RÖD** | patient-id, kund-id, djurets namn, kön, art, ras, födelsedatum, avliden/datum/orsak, försäkring och försäkringsbolag | **ingen kod** — som B1 |
| B3 | `loc.Dim_Department.csv` (två kopior) | spegel, PREP:s och klustringens `input/` | **RÖD** | klinikdimensionen med samma chefskolumner som G3 (värdena omätta här; i G3 är de anställdas namn och e-post). `01_process.sql` läser `DepartmentManager` och `ChiefVeterinarian` härifrån (`department_dim`) | `00_read.sql` (PREP, klustring) |
| B4 | Bränslet: `transaction_data.parquet` (1,3 GB, 27,7 miljoner rader), `transaction_data_frozen_facit_2025-06.parquet` (1,0 GB) | kanoniskt `input/parquet/` + spegel | **RÖD** (pseudonymiserat) | fakturarader: kund-, patient-, användar- och konsultations-id, fakturanummer, Klarna-flagga, belopp, moms, datum | REGEN → PREP |
| B5 | Härledd radnivådata: `Sweden_masterdata.csv` (7,7 GB), `sweden_master_data.parquet` (klustring 0,7 GB, bundle 0,9 GB), `Raw_Data_Clinic_Hospital.csv` (2 × 177 MB) | spegel | **RÖD** (pseudonymiserat) | kund-, patient- och besöks-id per rad, artikel, belopp, klinik och klinikadress | PREP, klustring, bundle-prep — återskapas ur B4 |
| B6 | `loc.Dim_Item 20250627.csv` (288 MB) | spegel | GUL | artikelregister: pris, inköpspris, marginal, leverantör, streckkod | PREP |
| B7 | Modellindata per fönster, modellutdata, steg 6-utdata, Model Feed | kanoniskt `input/data_prep/`, `output/` + spegel | RÖD-arv | veckodata och elasticiteter per site och produkt; site-utdata har en fil per site (koden i filnamnet) | MOTOR, steg 5/6, dashboarden |
| B8 | BCG:s leveransfiler: facit (`pipeline/00_frozen_facit/`, `bcg_original/`), mallar (`Excel_Outputs/`), bundle-prepens indata | kanoniskt + spegel | AVTAL (klinikmappningen `0808_…` även RÖD-arv) | BCG:s modellindata och -utdata | steg 6, validatorerna |
| B9 | Kvitton, körstatus, karantän, spegelns självbeskrivning (`_spegel/`: manifest med fullständiga filnamn) | `receipts`, `runstatus`, `quarantine`, spegel | RÖD-arv / GUL | — | dashboarden, återställaren |
| B10 | `spegel/historik/evbcgpricing_2026-10-21.bundle` | spegel | **RÖD** | allt som någonsin committats: G3, G7 och fem små utdata-CSV (modellresultat, GUL) som inte finns i dagens version | återställning av historiken |

## 5. Lagringskontots skydd (mätt 2026-10-21)

| Inställning | Värde | Betydelse |
|---|---|---|
| Offentlig (anonym) åtkomst | avstängd på kontot; ingen av de sju containrarna är publik | ingen kan läsa utan behörighet |
| Transport | endast HTTPS, minst TLS 1.2 | — |
| Kryptering i vila | Microsoft-hanterade nycklar | — |
| Nätverk | tar emot anslutningar från alla nät (`defaultAction: Allow`) | skyddet är behörighet, inte nät |
| Kontonyckel (Shared Key) | tillåten (ej satt = tillåten enligt Microsoft) | den som har nyckeln når allt, även B1–B5. Koden och verktygen autentiserar med kontonyckeln; stängs den av måste de gå över till Entra-inloggning |
| Mjuk borttagning, versioner | avstängda | raderat eller överskrivet går inte att återställa — `OFFBOARDING_KRITISKT.md` rad 10 |
| Rolltilldelningar | **omätt** — utvecklarens behörighet räckte inte | IT ser dem under Åtkomstkontroll (IAM) på kontot |

## 6. Frågor som väntar på beslut

| # | Fråga | Beslutar | Underlag |
|---|---|---|---|
| F1 | Får kund- och patientdimensionen (B1, B2) ligga kvar i spegeln? Ingen kod använder dem | dataskyddsombudet | §4 |
| F2 | Hur länge får radnivådata (B4, B5) sparas, och vem ska ha nyckelåtkomst? | dataskyddsombudet / IT-säkerhet | §4, §5 |
| F3 | Nätverksbegränsning, kontonyckel, mjuk borttagning | IT | §5 |
| F4 | G3 med anställdas namn och e-post finns i DevOps, historiken (B10) och GitHub-repot. Räcker dokumentationen? Kolumnerna används inte av koden och kan tömmas utan att resultatet ändras | dataskyddsombudet; chef + IT för GitHub-repot | §3 G3, `OFFBOARDING_KRITISKT.md` rad 11 |
| F5 | Får BCG:s kod och leveransfiler (G1, B8) ligga i Evidensias DevOps och Blob? | avtalsägaren | — |
| F6 | Vad ligger kvar på VM-disken? | IT (mäts genom att starta VM:en och lista arbetsmappen) | §2 |

## 7. Så hålls registret aktuellt

- Ny datafil eller ny kolumn med personanknytning → en rad här, i samma commit som filen.
- Kolumnnamnen kontrolleras med rubrikraden (CSV) eller schemat (parquet) — värdena behöver inte läsas.
- Före delning utanför Evidensia: gå igenom registret.

## Ändringar

| Datum | Ändring |
|---|---|
| 2026-10-21 | Första versionen. |
