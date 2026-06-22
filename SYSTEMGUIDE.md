# Systemguide — BCG-prismodellen på Evidensias egen data

*Utförlig genomgång av hela flödet, för läsning i verktyget. Bygger vidare på
FUNKTIONSKARTA.md (den korta översikten) med mer djup om varför varje steg finns,
vad det producerar, och vad som är färskt kontra fruset. Skriven för en förvaltare
eller intressent som vill förstå systemet utan att läsa koden.*

*Utvecklad av Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB).
Faktagrund: DRIFT.md (drift), README.md (arkitektur), REPLIKERING_OCH_VALIDERING.md
(bevis). Där dokumentationen och dagens faktiska körning skiljer sig, gäller nuläget.*

---

## Innehåll

1. Vad systemet är — och varför det finns
2. Tre faser: Input → Motor → Efter
3. Vad "äga modellen" betyder (replikering + drift)
4. Vad som är färskt och vad som är fruset
5. Hur en ny period körs
6. Var saker bor (kod, data, dokumentation)

---

## 1. Vad systemet är — och varför det finns

BCG byggde 2025 en priselasticitetsmodell åt Evidensia: en pipeline i Python som
skattar hur efterfrågan svarar på pris, per produkt och kliniktyp, och matar ett
Excel-baserat prisverktyg. Frågan var aldrig "har BCG rätt?" utan **"kan Evidensia
äga detta — köra det själva, på färsk data, och lita på resultatet för prisbeslut?"**

Att äga en modell betyder tre saker, i ordning:
1. **Återskapa den exakt** på samma data BCG använde — bevisar att vi förstår metoden.
2. **Köra den på färsk, växande data** — bevisar att den överlever utanför BCG:s
   frusna ögonblicksbild.
3. **Validera den färska outputen** utan ett facit att jämföra mot — bevisar att vi
   kan bedöma korrekthet på egen hand.

Det här systemet gör alla tre, och allt är versionshanterat. Replikeringen är grunden;
drift på färsk data är själva produkten.

**En priselasticitet** är den procentuella volymförändringen vid 1 % prisförändring.
Modellen skattar den per produktkod × klinikkluster med en log-log-regression — i en
sådan modell *är* priskoefficienten elasticiteten direkt. Eftersom de flesta
fingranulära grupper har för lite data för en stabil skattning (bara ~18 % är
statistiskt signifikanta på rå klusternivå), hanteras det med en **fallback-väv**: en
prioritetskaskad som låter glesa grupper ärva en starkare representant i stället för
att modelleras dåligt. Väven *väljer* en representant — den modellerar inte om.

---

## 2. Tre faser: Input → Motor → Efter

Hela systemet är tre led, som en fabrik. Var och en har ett tydligt syfte och en
tydlig övergång till nästa.

### FAS 1 — INPUT (förbereda data)

**Syfte:** förvandla rå transaktionsdata till modellklar veckodata.

Rådatan är Evidensias egen — varje fakturarad i datalagret (DW), tabellen
`dbo.Fact_BillingInvoiceRows`, dag för dag, tillbaka till 2017. Flödet:

**(1) Extraktion.** Hela faktatabellen hämtas ur DW till en parquet-fil
(`transaction_data.parquet`) — en snabb, läsbar ögonblicksbild på ~27 miljoner rader.
Detta görs chunkat (år för år) eftersom hela datasetet är för stort för att hållas i
minnet på en gång. En separat **frusen** parquet sparas som anker-baslinje (BCG:s
ursprungsfönster t.o.m. 2025-06), så vi alltid kan jämföra växande mot fruset.

**(2) Tvätt och form.** Tre SQL-steg (DuckDB) läser parqueten plus dimensioner
(artikel, avdelning, kluster, bemanning) och formar modellklar data:
- `00_read` läser in alla källor
- `01_process` filtrerar, väljer de produkter som står för 80 % av omsättningen per
  grupp (Top-80), och summerar till veckonivå
- `02_export` skriver ut resultatet

Detta orkestreras av `replicate_dataprep.py`, som styr datumfönstret.

**(3) Resultat.** Tre modellklara CSV-filer (cluster-, clinic/hospital- och
site-nivå) plus stöddata för fallback. Dessa laddas upp till Azure Blob och blir
input till motorn.

**Tre fällor som bitit oss (dokumenterade lärdomar):**
- **Parqueten är läskällan, inte DW.** SQL-prepen läser parquet — ingen ny period kan
  dyka upp i utdata förrän parqueten regenererats. Vill du ha en ny månad: kör
  extraktionen FÖRST.
- **Två datumlås måste flyttas tillsammans.** Datumfönstret styrs på två ställen — ett
  veckofönster OCH ett "räkenskapsår"-lås. Flyttar man bara det ena filtreras ny data
  bort tyst. `replicate_dataprep.py` injicerar båda.
- **Veckologik sätter taket.** Datan summeras per måndagsvecka, så sista *kompletta*
  veckan blir taket — inte nödvändigtvis sista dagen i månaden.

### FAS 2 — MOTORN (beräkna elasticiteter)

**Syfte:** skatta priselasticiteter för tre modellfamiljer. Körs på en kraftfull
Azure-VM (128 GB RAM, Ray-parallellt) eftersom beräkningarna är minnestunga.

Tre familjer, var och en kör modellsteg 1–4 på VM:en:
- **Cluster** — elasticitet per produktkluster
- **Site** — elasticitet per klinik
- **Bundle** — elasticitet för produktknippen (parkerad på evidens, se nedan)

Metoden per produktgrupp: OLS log-log-regression pris mot volym, med
kontrollvariabler (bl.a. bemanning/FTE). En multi-modell-fallback väljer bästa nivå
per produkt. Varje familj producerar `output_summary.xlsx` (rå elasticitet per KEY:
produkt × nivå), som laddas upp till Blob och blir input till Efter-steget.

**Varför VM och inte molnfunktion:** beräkningarna kräver mycket minne och
parallellisering — en vanlig maskin orkar inte. VM:en stängs av (deallocate) efter
körning så den inte kostar i onödan. Motorns utfall valideras mot BCG:s frusna facit
för att bevisa att metoden är korrekt replikerad innan den körs på växande data.

### FAS 3 — EFTER MOTORN (väva ihop och göra prismodell-klart)

**Syfte:** väva ihop de tre familjernas elasticiteter till EN slutsignal per produkt,
och göra den prismodell-klar. Körs lokalt eftersom stegen använder Excel-COM (xlwings)
som inte kan köras i molnet.

**(1) Steg 6 — Fall Back Logic.** Väver de tre familjernas elasticiteter enligt en
sjunivåers prioritetsordning (site → bundle → cluster → bundle-across → product-across
→ service-within → service-across). För varje produkt tas första signifikanta nivån.
Resultat: `Final_Fallback_Data.xlsx` — ~109 000 rader, ~15 000 produkter, en
slutelasticitet per produkt.

**(2) Steg 7 — Build R12 model feed.** Kombinerar elasticiteten med rullande
12-månaders volym och omsättning, och fyller modellens indataflikar (kod × site).
Resultat: `Model_Feed.xlsx` — färdig att klistra in i prismodellen. ~99,5 % av
raderna bär en matchad elasticitet.

**(3) Förtroende-validering.** Två sviter körs och skriver Excel-kvitton som
verktyget visar per steg:
- **provenance** — vad är färskt kontra fruset (rapporteras som "granskning", inte
  fel, eftersom tre lager medvetet är frusna)
- **rationality** — är varje färsk elasticitet rimlig (100 % negativa, 100 % inom
  bandet (−10, 0))

**(4)** Allt laddas upp tillbaka till Blob. Då bär Blob hela kedjan — Input, Motor,
Efter — och verktyget kan visa alla steg som en sömlös yta med status, körtid och
förtroende, och göra filerna nedladdningsbara.

---

## 3. Vad "äga modellen" betyder — bevisen

### Replikeringen (bevisad bit-för-bit)

Pipelinen byggdes om steg för steg och bevisades återskapa BCG:s frusna output exakt,
på BCG:s ursprungliga datafönster:

| Steg | Vad som återskapades | Bevis |
|---|---|---|
| Dataprep | Modellens indata = BCG:s | korrelation 1,000000, ingen diff |
| Cluster-blend | Representantval per service × kluster | 43/43 identiska |
| Cluster-modell | Klusternivå-elasticiteter | beslutsrelevanta identiska |
| Site-modell | Site-nivå-elasticiteter | rank-korrelation 0,91 |
| Bundle-modell | Varukorgs-elasticiteter | rank-korrelation 0,93 |
| Fallback-väv | Hela slutelasticiteten per produkt | 109 000 rader, korr 1,000000 |

Den sista raden är den avgörande: hela väven, end-to-end, producerade **samma
slutelasticitet som BCG för varje produkt** — inte ett liknande svar, utan samma svar.
Det är vad "vi äger metoden" betyder i bevistermer.

Replikeringen avslöjade och fixade konkreta defekter i den ärvda koden: sökvägsfel,
ett kolumnnamns-fel, saknade härledda kolumner, en formatmiss och en encoding-bugg.

### Drift på färsk data (resultatet)

Modellen körs nu på Evidensias egen växande data. När den senast kördes på data
t.o.m. 2026-04 gav fallback-väven 108 979 rader / 15 128 produkter, 100 % negativa,
100 % inom det rimliga bandet. Den omsättningsvägda kärnelasticiteten rörde sig från
BCG:s 2025-baslinje −0,532 till −0,512 — **materiellt stabil** över tio månader, vilket
är precis egenskapen en prismodell behöver.

Fördelningen över väv-nivåerna visar varför väven finns: 74,6 % av produkterna hämtar
sin elasticitet från service-within-cluster-nivån (F6) — de flesta produkter saknar
egen signifikant signal ens på klusternivå.

---

## 4. Vad som är färskt och vad som är fruset

Detta är den operativa sanningen, och den är medvetet transparent:

| Del | Tillstånd | Hur den görs färsk |
|---|---|---|
| Cluster + Site-elasticiteter | **VÄXANDE** | redan färsk |
| R12 volym och omsättning | **VÄXANDE** | bygg om model feed |
| Cluster steg-5-routning | FRUSEN (2025) | billigast att tina (FD.15) |
| Väv-vikter | FRUSEN (2025) | Alteryx/DuckDB-ombyggnad (FD.14) |
| Bundle-gren | FRUSEN (parkerad) | bara 2,2 % väv-vinst; villkorlig (FD.11) |

**Kärnsignalen för priskänslighet — de tal som styr prissättningen — är färsk idag.**
De tre frusna låsen påverkar en liten, dokumenterad andel av utfallet. De lyfts i
ordningen kostnad-mot-påverkan (FD.15 → FD.14 → FD.11). Provenance-kvittot flaggar dem
ärligt som "granskning", så ingen övertolkar resultatet.

**Varför bundle är parkerad:** varukorgs-transaktioner var 23,9 % av omsättningen, men
bundle-grenen vinner bara 2,2 % av besluten i väven — Cluster- och Site-nivåerna räddar
elasticiteten innan väven når bundle för 97,8 % av produkterna. Att färdigställa
bundle-modellen skulle alltså påverka 2,2 % av utfallen — oproportionerlig kostnad.
Detta är ett medvetet, dokumenterat beslut, inte en lucka.

---

## 5. Hur en ny period körs

Hela kedjan är omkörbar. När en ny månad stänger:

1. **Uppdatera källdata** — regenerera parqueten från DW med det nya slutdatumet,
   kör sedan SQL-prepen (den växande vecko-CSV:n). *(Obs: parqueten måste regenereras
   först — SQL-prepen läser parquet, inte DW.)*
2. **Kör om elasticiteterna** — Cluster + Site-modellerna på VM:en.
3. **Väv ihop** — Step 6 (fallback-väven).
4. **Validera** — rationality + provenance (läs kvittot, inte konsolen).
5. **Bygg om matningen** — Build R12 (fönstret rullar fram automatiskt till senaste
   kompletta månad).
6. **Klistra in i prismodellen** — kopiera Model_Feed-flikarna till prisverktygets blå
   indataflikar (rör inte beräkningsflikarna), lägg ett prisantagande, läs
   omsättningseffekten.

R12-fönstret är samma 12-månaderslängd som BCG använde, men med slutdatumet
framflyttat till senaste kompletta månad. Elasticiteten och volymerna delar fönstret
per konstruktion (de kommer från samma extrakt). Ankaret är fast vid 2022-07-01.

---

## 6. Var saker bor

| | Innehåll | Var |
|---|---|---|
| **GitHub** | Metoden — all kod + dokumentation (ingen affärsdata) | Repo |
| **Azure Blob** | Datan — parquet, motorns output, slutresultat, gamla valideringar | Blob |
| **Verktyget** | Nedladdningsbar yta som visar alla steg, körtid, förtroende | Lokalt/webb |

GitHub (metoden, *hur*) + Blob (datan, *vad*) tillsammans gör att systemet kan
återskapas oberoende av en enskild dator. En efterträdare kan klona GitHub, läsa Blob,
och köra hela kedjan utan tillgång till den ursprungliga arbetsstationen.

**Arbetsprinciper som format systemet:**
- **Mät, gissa inte** — när en källa är oklar, hämta alla kandidater och mät mot facit.
  Det löste källidentitet, netto/brutto och produktgruppsmappning.
- **Lita på källan, inte anteckningarna** — originalkoden är facit; våra anteckningar
  har haft fel oftare än koden.
- **Validera mot fruset original, aldrig arbetskopia** — arbetskopiorna skrivs över av
  körningar och är inte facit.
- **Dokumentera medan du kodar** — varje icke-trivial fil bär ett huvud som säger vad
  den gör, vad den beror på, och vilka lärdomar som motiverar val.

---

## Vidare läsning (dokument i verktyget)

- **FUNKTIONSKARTA.md** — den korta visuella översikten (tre kartor)
- **DRIFT.md** — operativ körhandbok, steg för steg
- **README.md** — arkitektur och projektöversikt
- **REPLIKERING_OCH_VALIDERING.md** — det fullständiga bevisarbetet
- **LOCKED_ASSUMPTIONS.md** — vad som är fruset och varför
- **LESSONS_BCG.md** — tekniska lärdomar
- **INSIGHTS_BCG.md** — analytiska insikter om modellen och datan

---

*Förvaltas av Jens Palmö (Senior Business Analyst, Evidensia). Detta dokument speglar
systemet som det fungerar idag — replikeringen bevisad, drift på färsk data i
produktion, allt sparat på Blob för oberoende av en enskild dator. Där en äldre
dokumentationsrad krockar med dagens körning, gäller nuläget.*
