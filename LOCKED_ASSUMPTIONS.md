# LOCKED_ASSUMPTIONS — Låsta förutsättningar för BCG Pricing-projektet

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde — replikering, validering, migrering)
**Lever i:** `C:\Projekt\BCG`
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Skapad:** 2026-06-05
**Senast uppdaterad:** 2026-06-05

---

## Vad detta dokument är (och inte är)

`LOCKED_ASSUMPTIONS.md` håller **låsta förutsättningar** — proaktiva designbeslut som
ska *inte* revideras impulsivt även om kommande data eller analyser föreslår annat.

**Varför filen finns:** För att chefer ska kunna fatta affärsbeslut behöver de en stabil
referensram. Om kluster-strukturer, gränsvärden eller datakällor förändras varje gång
data växer blir målet rörligt och beslutsunderlaget otillförlitligt. Vissa förutsättningar
ska vara "konstanta verkligheter" som modellen byggs runt — inte parametrar som justeras
för att jaga BCG:s siffror eller förbättra signifikansgrad.

**Format för varje post:**
```
LF.N — Kort titel
Förutsättning: Vad som är låst
Varför låst: Affärsskäl
Vad som händer om vi bryter mot den: Konsekvens
Vad som skulle krävas för revision: Eskaleringsnivå
Datum låst / källa: Spårbarhet
```

**Detta är inte:**
- **Tekniska lärdomar** ("fällor som hänt oss") → `LESSONS_BCG.md` (`LB.N`)
- **Analytiska insikter** ("vad vi upptäckt om modellen") → `INSIGHTS_BCG.md` (`IB.N`)
- **Operationella beslut** ("vad vi valde i en specifik situation") → `BCG_PRICING_PLAYBOOK.md` decision log

**Skillnaden:** LB är reaktiva, IB är observationer, D är situativa val. **LF är proaktiva
låsningar** som skyddar affärskontinuitet över sessioner och datavolymer.

---

## Snabbindex

| ID | Förutsättning | Vad bryts om vi ändrar |
|---|---|---|
| LF.1 | Cluster-hierarki 2-nivå platt (ej BCG:s 4-nivå med CH-mellansteg) | Fallback-räddningsgrad förändras varje körning |
| LF.2 | Anchor-datum 2022-07-01 för växande fönster (ej rolling windows) | Hela elasticitetsbasen ändras |
| LF.3 | BCG OneDrive-facit och egna verifierade outputs är skrivskyddade | Replikeringsbeviset förloras |
| LF.4 | Modell-KEY = Cluster × ItemCode (ej annan granularitet) | Hela modellen står på denna nyckel |
| LF.5 | IB.2-gate: `Significant?` = `RSQ ≥ 0.5 AND PVALUE ≤ 0.2` (ej p<0.05) | Signifikansrapporter blir inte jämförbara |
| LF.6 | FTE via Way 1 (BCG:s interpolerade fil), ej Way 2 (DW-native härledning) | Modellen jagar ett rörligt mål om FTE-källan ändras |
| LF.7 | `ProductGroupL4Name` är BCG:s bespoke kategorisering, ej DW-härledd | Service-mappningen bryts; fallback-grupperingen blir inkompatibel |

---

## Låsta förutsättningar

### LF.1 — Cluster-hierarki är 2-nivå platt

**Förutsättning:** Vår cluster-hierarki har **2 nivåer**:
- Fin: `Clinics 0`, `Clinics 1`, `Clinics 2`, `Sjukhus A`, `Sjukhus B`, `Sjukhus C`, `Sjukhus Södran` (7 värden)
- Grov: `Clinics`, `Hospital` (2 värden)

Vi återskapar **inte** BCG:s 4-nivå-hierarki med `Clinics_CH`/`Hospital_CH`-mellansteg som finns
i BCG:s `cluster_h_map` i `constants.py`. CH-segmenteringen i BCG:s
`final_model_cluster_granularity.xlsx` (med 4 `New_cluster`-värden) är ett härledningssteg vi
medvetet hoppar över.

**Varför låst:** Affärs-referensramen måste vara stabil över sessioner. Om vi inför en härledd
mellannivå nu och tar bort den vid nästa körning förändras alla fallback-räddade elasticiteter.
Chefer som fattar prisbeslut på output behöver kunna jämföra körning N mot körning N+1 utan att
strukturen rört sig. CH-segmenteringen är dessutom BCG:s härledning, inte en datapunkt — den
representerar ett analytiskt val vi inte gjort själva.

**Vad som händer om vi bryter:** Fallback-räddningsgraden ändras (BCG gick från 17.8% rå till 48.4%
post-fallback med 4-nivå-hierarki; vi når 23.8% pre-fallback och 23.8% post-fallback med 2-nivå).
Genom att låsa vid 2-nivå accepterar vi lägre räddningsgrad men får stabil referensram.

**Vad som skulle krävas för revision:** Affärsbeslut från chef + dokumenterat skäl ("data har
ändrats på sätt som motiverar ny hierarki"). Inte ett tekniskt val.

**Datum låst:** 2026-06-05 (FAS F.7, denna session)
**Källa:** Diskussion 2026-06-05 efter observation att post-fallback Significant?=362/1521 = pre-fallback

---

### LF.2 — Anchor-datum för växande fönster är fast 2022-07-01

**Förutsättning:** Datafönstret är **växande från fast anchor 2022-07-01** till en parametriserbar
`BCG_END_DATE`. Rolling windows (där både start och slut rör sig) är inte default — det är ett
medvetet senare analytiskt steg om det överhuvudtaget behövs.

**Varför låst:** Elasticiteten är historikens funktion. Om anchor-datum rör sig får varje körning
en annorlunda historisk bas och elasticiteterna blir inte jämförbara över tid. En produkt som visade
-0.5 elasticitet i körning A och -0.3 i körning B — är det produktens beteende som ändrats, eller
har vi mätt på en annan tidsperiod? Med fast anchor är svaret entydigt: produktens beteende.

**Vad som händer om vi bryter:** Två sammanhang försvinner: (a) jämförbarhet mellan körningar,
(b) möjligheten att tolka skillnader som "data har förändrats" snarare än "vi mäter på annan period".

**Vad som skulle krävas för revision:** Affärsfråga som specifikt kräver rolling windows
(t.ex. "hur har elasticiteten förändrats senaste 2 åren?"). Då skapas en parallell körningsserie,
men anchor-låsningen för huvudmodellen står kvar.

**Datum låst:** 2026-05-28 (FAS 9, G7-parametrisering)
**Källa:** `FAS_F_G7.md`, kommentar i `constants.py`: *"Window design: growing window with fixed anchor 2022-07-01 (rolling windows are a deliberate later analytical step)"*

---

### LF.3 — BCG facit och verifierade outputs är skrivskyddade

**Förutsättning:** Två kategorier av filer är **skrivskyddade**:
1. BCG:s original i OneDrive `BCG_orginal_V2_New\` — aldrig skriv till
2. Egna verifierade outputs i `azure_run_model\` (per modell) — `IsReadOnly=True` satt på fil

**Varför låst:** Dessa filer är **bevisen** att replikeringen fungerar. BCG-facit är konsultarvet
(unikt artefakt vi inte kan återskapa). Egna verifierade outputs är vår sanning på vårt format
som verifierat bit-för-bit mot BCG-facit. Båda är referenser som framtida körningar jämförs mot.

**Vad som händer om vi bryter:** En felriktad körning skriver över beviset. Vi förlorar
referenspunkten och kan inte längre svara på frågan "stämmer vår nya körning fortfarande med
BCG:s logik?".

**Vad som skulle krävas för revision:** Ny verifieringsomgång där ny baslinje bevisas mot BCG-facit
bit-för-bit, sedan låses ny baslinje (gamla flyttas till `_archive_*`).

**Datum låst:** 2026-05-28 (FAS 9, förutsättning 1 för FAS F)
**Källa:** PowerShell `Set-ItemProperty $f -Name IsReadOnly -Value $true` applicerad på tre filer

---

### LF.4 — Modell-KEY = Cluster × ItemCode

**Förutsättning:** Modellens **primary key** är `KEY = Cluster_Granularity + '-' + ItemCode`.
Vi ändrar inte granularitet, inte sortering, inte separator, inte komponentkolumner.

**Varför låst:** Hela elasticitets-modellen står på denna nyckel. Output-format, fallback-logik,
verify_tool, compare-skript, downstream-rapporter — allt förutsätter denna KEY-struktur.
`ProductGroupL4Name` (Service) påverkar inte kärnelasticiteten — den bärs för YOY-säsong och
output/blend-gruppering. Modellen är **produkt × kluster**, ingen annan granularitet.

**Vad som händer om vi bryter:** Inte ens "förbättring". Allt downstream bryts: verify_tool,
fallback_blend, compare_elasticity_runs, alla aggregeringar. En förändring i KEY-struktur är
inte en optimering — det är att bygga om hela modellen.

**Vad som skulle krävas för revision:** Strategiskt beslut om ny modellgenenration (inte
optimering av denna). Innebär ny FR-cykel, ny baslinje, ny replikeringsfas.

**Datum låst:** 2026-05-25 (FAS 4, bekräftat i IB.8)
**Källa:** `INSIGHTS_BCG.md IB.8`, BCG:s `constants.py` L8 + L46

---

### LF.5 — Signifikans-gate är RSQ ≥ 0.5 AND PVALUE ≤ 0.2

**Förutsättning:** Vår `Significant?`-flagga använder **BCG:s lösa gate**:
- `RSQ ≥ 0.5` AND `PVALUE_Regular_Price_fwbw_max_6 ≤ 0.2`

Inte `p < 0.05` (traditionellt statistiskt). Inte annan tröskel.

**Varför låst:** Detta är **BCG:s gate**. Att ändra den skulle:
1. Bryta jämförbarhet med BCG:s ursprungliga siffror (618/1276 = 48.4%)
2. Förändra hur många KEY som klassas som "trovärdiga för prisbeslut"
3. Göra alla historiska affärsrapporter inkompatibla med nya

Den lösa gaten är ett **affärsval**, inte ett statistiskt: BCG bedömde att i en domän med tunn
data per grupp är p ≤ 0.2 tillräckligt tillsammans med RSQ ≥ 0.5 för att vara "användbar"
elasticitet. Det är inte vår plats att överpröva det valet utan att eskalera.

**Vad som händer om vi bryter:** Två chefer som tittar på rapporter från olika perioder ser
olika antal "signifikanta" KEY för samma produkter — och drar fel slutsatser om modellens
stabilitet.

**Vad som skulle krävas för revision:** Affärsbeslut från chef baserat på dokumenterad analys
av falska positiver vs falska negativer. Inte ett tekniskt val.

**Datum låst:** 2026-05-25 (FAS 5, IB.2-korrigering)
**Källa:** `INSIGHTS_BCG.md IB.2`, BCG `data_prep_after_model_output.py` L145

---

### LF.6 — FTE via Way 1 (BCG:s interpolerade fil), inte Way 2 (DW-native)

**Förutsättning:** `Sum_FTE_Interpolated` (control-variabel i modellen) hämtas från
**BCG:s färdigt interpolerade fil** `Sweden_Interpolated_Productivity_time.csv`. Vi härleder
inte FTE från vår egen Quinyx-data via en återskapad
`Sweden_Productive_Time_Data_Creation.py`-process.

**Varför låst:** FTE-värden är konsekventa över tid när källan är fast. BCG:s
interpolerade fil är en *kurerad* artefakt som vi inkluderar i Git medvetet (per `.gitignore`-kommentar
2026-05-26) som "extern indata under förvaltning". Way 2 (DW-native) är en framtida skalningsväg,
inte default.

**Vad som händer om vi bryter:** Modellen jagar ett rörligt mål — FTE-värden förändras varje gång
DW-extraktionen körs och interpolerings-algoritmen revideras. Elasticitets-skillnader mellan
körningar kan då bero på FTE-källans förändring snarare än på riktig affärsmässig drift.

**Vad som skulle krävas för revision:** FAS efter F (skalning till fresh-data utan BCG-beroende)
där Way 2 implementeras, valideras mot Way 1, och dokumenteras som ny baslinje. Tills dess: Way 1.

**Datum låst:** 2026-05-25 (FAS 4)
**Källa:** Kommentar i `export_b4b_for_model.py`: *"FTE (Sum_FTE_Interpolated) — WAY 1 (faithful), read from source not guessed... WAY 2 (rebuild FTE from our Quinyx data via Sweden_Productive_Time_Data_Creation.py) is the scaling step for fresh-data runs."*

---

### LF.7 — ProductGroupL4Name är BCG:s bespoke kategorisering, inte DW-härledd

**Förutsättning:** `ProductGroupL4Name` (= `Service` i fallback) hämtas från **BCG:s prod-fil**
(`Complete_Product_Data.xlsx` eller motsvarande), **inte** från vår DW-kolumn
`Master_Underkategori3`. Vi mappar inte L4 via DW.

**Varför låst:** Empirisk upptäckt (FAS 3, `discover_l4_mapping.py`): BCG:s
`ProductGroupL4Name` **existerar inte i `dbo.Dim_Item`**. Det är BCG:s egen kategorisering, byggd
under deras projekt, inte härledbar från någon DW-kolumn. Vår närmaste motsvarighet
`Master_Underkategori3` är dessutom halv-NULL (LB-historik).

**Vad som händer om vi bryter:** Försök att härleda L4 från DW ger ofullständig täckning
(NULL för många ItemCode) och annan gruppering än BCG. Fallback-blenden grupperar på `Service`
× `big_cluster` — ändras Service-mappningen ändras alla representant-val och därmed alla räddade
elasticiteter. Affärsrapporter blir inkompatibla mellan körningar.

**Vad som händer om vi bryter:** Två chefer som tittar på "Prescription i Hospital" får olika
ItemCode-mängd beroende på vilken Service-mappning som användes.

**Vad som skulle krävas för revision:** Strategiskt beslut att Evidensia bygger egen produkthierarki
(ersättning för BCG:s L4). Då blir det en separat fas med ny baslinje, inte en optimering av denna.

**Datum låst:** 2026-05-22 (FAS 3, empirisk upptäckt)
**Källa:** `discover_l4_mapping.py`-output, `INSIGHTS_BCG.md` (referens till `Master_Underkategori3`-NULL)

---

## Hur posten levs

Listan **lever**. Nya LF identifieras när:
- Vi tar ett designbeslut som är affärsmässigt motiverat snarare än tekniskt
- Vi väljer att inte återskapa något BCG gjort därför att det skulle göra modellen "rörlig"
- Vi låser en parameter eller struktur för stabilitetens skull

En LF läggs till genom att:
1. Identifiera valet under en session (kärnprincipens 6.4 — sök först om det redan finns)
2. Föreslå LF.N med format ovan
3. Få Jens bekräftelse innan filen skrivs

En LF revideras genom:
1. Affärsbeslut från chef (inte tekniskt val)
2. Dokumenterad analys av konsekvens
3. Eskalering till playbookens decision log som permanent ändring

---

## Senaste uppdateringar

| Datum | Vad |
|---|---|
| 2026-06-05 | Fil skapad med LF.1-7 vid avslut av FAS F.7 (cluster-fallback på växande). LF.1 identifierad efter observation att post-fallback Significant?=362/1521 = pre-fallback p.g.a. saknad CH-mellannivå — Jens beslut: behåll 2-nivå-hierarki, inte återskapa CH. LF.2-7 retroaktivt formaliserade från tidigare sessioner. |
