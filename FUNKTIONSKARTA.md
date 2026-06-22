# Funktionskarta — hur datan flödar genom systemet

*Pedagogisk översikt för genomgångar. Tre kartor: **Input** (innan Azure-motorn),
**Motorn** (Azure-VM), **Efter** (lokalt efter motorn). Avsiktligt kort — detaljerna
finns i DRIFT.md och respektive README.*

*Utvecklad av Jens Palmö (Senior Business Analyst, Evidensia). Funktionskartan
beskriver flödet på en nivå en ny förvaltare eller intressent ska förstå utan att
läsa koden.*

---

## Helheten i en mening

Rådata hämtas ur datalagret → tvättas och formas till modellklar veckodata →
tre modellfamiljer beräknar priselasticiteter på en kraftfull Azure-maskin →
resultatet vävs ihop och görs prismodell-klart lokalt. Allt sparas på Azure Blob
så det kan återskapas oberoende av en enskild dator.

---

## KARTA 1 — INPUT (innan Azure-motorn)

**Syfte:** förvandla rå transaktionsdata till tre modellklara veckodatafiler
(cluster-, clinic/hospital- och site-nivå) plus stöddata för fallback.

```
   [ Datalagret (DW) ]
   dbo.Fact_BillingInvoiceRows
   = varje fakturarad, dag för dag
            │
            │  (1) EXTRAKTION
            │  regenerate_transaction_parquet.py  (pyodbc, kräver VPN/kontorsnät)
            │  hämtar HELA faktatabellen (2017 → senaste stängda månad)
            ▼
   [ transaction_data.parquet ]
   ~27 M rader, rå dagsdata, en snabb läsbar ögonblicksbild
   (en FRUSEN parquet sparas separat som anker-baslinje)
            │
            │  (2) "TVÄTT" + FORM  — DuckDB SQL, tre steg
            │  00_read.sql     läser parquet + dimensioner (item, avdelning, kluster, FTE)
            │  01_process.sql  filtrerar, väljer Top-80%-koder, summerar till vecka
            │  02_export.sql   skriver ut CSV-filerna
            │  (orkestreras av replicate_dataprep.py, som styr datumfönstret)
            ▼
   [ Tre modellklara CSV:er + stöddata ]
   • Sweden_weekly_model_data_P_C.csv        (cluster-nivå)
   • Sweden_weekly_model_data_P_CH.csv       (clinic/hospital-nivå)
   • Sweden_weekly_model_data_site_level.csv (site-nivå)
   • Complete_Product_Data.csv               (fallback-stöd)
            │
            │  (3) parqueten + CSV:erna laddas upp till Azure Blob
            ▼
        → blir INPUT till motorn
```

**Tre saker som är lätta att missa (och som bitit oss):**
- **Parqueten är läskällan, inte DW.** SQL-prepen läser parquet — så ingen ny period
  kan dyka upp i utdata förrän parqueten regenererats. Vill du ha en ny månad: kör
  extraktionen FÖRST.
- **Två datumlås måste flyttas tillsammans.** Datumfönstret styrs på två ställen
  (veckofönstret OCH ett "räkenskapsår-flagg"-lås). Flyttar man bara det ena
  filtreras ny data bort tyst. `replicate_dataprep.py` injicerar båda.
- **Veckologik sätter taket.** Datan summeras per måndagsvecka, så sista *kompletta*
  veckan blir taket — inte nödvändigtvis sista dagen i månaden. *(Exakt fallback-
  beteende — t.ex. om systemet kan gå till gårdagen — är att bekräfta vid validering;
  återstår att verifiera mot källan.)*

---

## KARTA 2 — MOTORN (Azure-VM)

**Syfte:** beräkna priselasticiteter (hur efterfrågan svarar på pris) för tre
modellfamiljer. Körs på en kraftfull VM eftersom beräkningarna är minnestunga.

```
   [ INPUT från Blob: veckodata-CSV:er ]
            │
            │  laddas till Azure-VM (Standard_E16s_v5, 128 GB RAM, Ray-parallellt)
            ▼
   ┌─────────────────────────────────────────────────────┐
   │  TRE MODELLFAMILJER (var och en steg 1–4 på VM:en)   │
   │                                                       │
   │  • CLUSTER  — elasticitet per produktkluster          │
   │  • SITE     — elasticitet per klinik (site)           │
   │  • BUNDLE   — elasticitet för produktknippen           │
   │                                                       │
   │  Metod (per produktgrupp): OLS log-log-regression     │
   │  pris↔volym, med kontrollvariabler (bl.a. FTE).        │
   │  Multi-modell-fallback väljer bästa nivå per produkt. │
   └─────────────────────────────────────────────────────┘
            │
            │  varje familj producerar output_summary.xlsx
            │  (rå elasticitet per KEY: produkt × nivå)
            ▼
   [ output_summary.xlsx × 3 ]  → laddas upp till Blob
            │
            ▼
        → blir INPUT till Efter-steget

   (En statusfil på Blob speglar varje fas: väntar / kör / klar, med körtid.)
```

**Tre saker att veta:**
- **Varför VM och inte molnfunktion:** beräkningarna kräver mycket RAM och
  Ray-parallellisering — en vanlig maskin orkar inte.
- **VM:en stängs av (deallocate) efter körning** så den inte kostar i onödan.
- **Validering mot facit:** motorns utfall jämförs mot BCG:s frusna resultat för att
  bevisa att metoden är korrekt replikerad innan den körs på växande data.

---

## KARTA 3 — EFTER MOTORN (lokalt)

**Syfte:** väva ihop de tre familjernas elasticiteter till EN slutsignal per
produkt, och göra den prismodell-klar. Körs lokalt eftersom stegen använder
Excel-COM (xlwings) som inte finns i molnet.

```
   [ INPUT: motorns output_summary × 3, hämtat FRÅN Blob ]
   + tre frusna 2025-lager (väv-vikter, cluster-routning, bundle-gren)
            │
            │  run_after.py orkestrerar:
            │
            │  (1) STEG 6 — Fall Back Logic
            │      väver de tre familjernas elasticiteter enligt en prioritets-
            │      ordning (site → cluster → produkt → bundle) till EN elasticitet
            │      per produkt. Fallback fyller luckor där en nivå saknar signal.
            ▼
   [ Final_Fallback_Data.xlsx ]  — slutelasticitet per produkt
            │
            │  (2) STEG 7 — Build R12 model feed
            │      kombinerar elasticiteten med rullande 12-mån volym/omsättning
            │      → fyller modellens indataflikar (kod × site).
            ▼
   [ Model_Feed.xlsx ]  — färdig att klistra in i prismodellen
            │
            │  (3) FÖRTROENDE-VALIDERING
            │      provenance (vad är färskt vs fruset) + rationality (rimlighet)
            │      → Excel-kvitton som appen visar per steg.
            │
            │  (4) allt laddas upp TILLBAKA till Blob
            ▼
   [ Blob bär nu hela kedjan: Input + Motor + Efter ]
            │
            ▼
        → APPEN visar alla steg (status, körtid, förtroende) som en
          sömlös yta, och gör filerna nedladdningsbara.
```

**Tre saker att veta:**
- **Varför lokalt:** Excel-COM-stegen (xlwings) kan inte köras på Linux-VM:en.
- **Tre frusna lager:** delar av väven vilar på låsta 2025-värden (medvetet, dokumenterat).
  Kärnsignalen — elasticiteten — är färsk; förtroende-kvittot flaggar ärligt vad som
  är fruset (visas som "granskning", inte "godkänt").
- **Överlevnadstesen:** allt landar på Blob, så en efterträdare kan klona koden +
  läsa Blob och köra hela kedjan utan den ursprungliga datorn.

---

## Sammanfattning: var bor vad?

| | Innehåll | Var |
|---|---|---|
| **GitHub** | Metoden — all kod + dokumentation (ingen affärsdata) | Repo |
| **Azure Blob** | Datan — parquet, motorns output, slutresultat, gamla valideringar | Blob |
| **Appen** | Nedladdningsbar yta som visar alla steg, körtid, förtroende | Lokalt/webb |

*GitHub (hur) + Blob (vad) = systemet kan återskapas oberoende av en enskild dator.*
