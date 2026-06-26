# Valideringslagret — limmet runt BCG-motorn

> **Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
> **Författare (verktyg + denna karta):** Claude advisor, Phase Z, 2026-06.
> **Syfte:** Förvaltningskarta för det additiva valideringslager som omger den
> orörda BCG-motorn. Beskriver vad varje verktyg gör, när det körs, i vilken
> ordning, och — viktigast — *varför* det är byggt som det är, så att mönstret
> kan återanvändas i framtida pipelines.

---

## Den bärande tesen (läs först)

Det här lagret rör **aldrig** BCG:s kärnlogik. BCG-motorn är validerad bit-för-bit
mot frozen facit och behandlas som ett orört reningsverk. Allt här är **fogmassan
och limmet** runt motorn: det som säkrar att rätt data kommer in, processas genom
alla steg och familjer utan att något tappas tyst, och kommer ut som replikerbart,
korrekt utfall på ny färsk data.

Tre principer styr hela lagret:

1. **Additivt only.** Tas vilket verktyg som helst bort fungerar pipelinen precis
   som förut — bara utan skyddet. Inget verktyg är ett beroende för BCG-koden.
2. **Mät, gissa inte.** Varje verktyg har ett kalibrerings-/rapportläge som visar
   vad som *faktiskt* finns innan något påstås vara fel. Toleranser och förväntade
   värden sätts mot uppmätt verklighet, aldrig mot antagande.
3. **Validatorn måste vara minst lika feltålig som det den validerar.** En grind
   som kraschar på en utgången token är en grind som ljuger. Observation loss
   (kan inte se) skiljs alltid från failure (är trasigt) — ärvt ur azure_vm.py:s
   AZ.7-disciplin.

---

## De två sorternas "är det rätt?" — varför det krävs flera verktyg

| Fråga | Karaktär | Verktyg |
|---|---|---|
| Finns alla länkar? Passar skarvarna? | **Statisk** (rören tomma) | dry_run_full_pipeline |
| Är alla familjer i synk mot samma fönster? | **Tvärgående** (mellan familjer) | window_coherence |
| Har varje boundary-fil rätt form/volym/nyckel? | **Lokal** (en gräns) | pipeline_contracts |
| Är en känd dataavvikelse hanterad rätt? | **Data-semantik** | prefilter_unpriced |
| Ger hela limmet känt utfall på oförändrad data? | **Dynamisk** (vått, end-to-end) | run_smoke_facit |

Ingen enskild fråga räcker. Ett tomt rör som ser perfekt ut (statisk) säger inget
om vad som händer när vatten flödar (dynamisk). Och att en *fil* har rätt form
(lokal) säger inget om att *alla familjer* kördes mot samma period (tvärgående).

---

## Verktygen — vad, när, varför

### 1. `dry_run_full_pipeline.py` — passar skarvarna?
**Vad:** Går längs hela rördragningen med rören tomma. Kollar att varje runner +
skript + interpreter finns, att `window_run_id` är *identiskt* tvärs run_data /
familje-runners / run_after (driftar det får familjerna olika statusfiler och
finalize() ljuger), att varje runner svarar på `--dry-run` utan att krascha, och
— med `--vm` — att az/VM/Blob nås.
**När:** Före varje varm körning. Billigt, sekunder.
**Varför så:** Fångar den friktionsklass som får en flertimmarskörning att faila
*direkt* — fel sökväg, namnskarv, fönster-osynk. Att upptäcka det kallt på sekunder
slår att upptäcka det i minut 50 av en VM-körning.
**Kör:**
```
py -3.11 verify_tool\dry_run_full_pipeline.py --start 2022-07-01 --end <YYYY-MM-DD>
py -3.11 verify_tool\dry_run_full_pipeline.py --end <YYYY-MM-DD> --vm   # + levande az/VM
```

### 2. `window_coherence.py` — är familjerna i synk?
**Vad:** Den tvärs-familje-grinden. Bevisar att alla MOTOR-familjer (härledda ur
default_pipeline, PhaseLocation.VM) är klara mot *samma* fönster innan EFTER startar.
Två källor: LOKAL (default, offline — output_summary-filtider mot parquet) eller
BLOB (`--via-blob`, striktare, läser delade statusfilen, kräver token).
**När:** Före EFTER-kedjan (run_after). Bör anropas i run_after.preflight.
**Varför så:** Stänger det enda strukturella glappet — ingen komponent ägde
helheten över familjer. Fellaget: cluster körd, site av misstag hoppad, run_after
väver på förra körningens site-fil → trovärdigt men fel utfall, tyst. Grinden gör
det till ett hårt STOP. Token-död degraderar mjukt till lokal koll (AZ.7) — grinden
kraschar aldrig på observation loss.
**Kör:**
```
py -3.11 verify_tool\window_coherence.py --start 2022-07-01 --end <YYYY-MM-DD>
py -3.11 verify_tool\window_coherence.py --end <YYYY-MM-DD> --via-blob   # striktare
```

### 3. `pipeline_contracts.py` — har varje boundary-fil rätt form?
**Vad:** Boundary-kontrakt för Step 6:s sex inputs. Verifierar form (kolumner),
volym (radantal mot golv) och invarianter (icke-null nyckel, numerisk elasticitet),
och VÄGRAR starta nästa steg annars. Kalibrerat mot faktiska kolumner (`--calibrate`).
Hanterar känd null-nyckel via prissatt-vs-icke-prissatt-logik (se verktyg 4).
**När:** I run_step6.preflight, före placering. Eller fristående för kontroll.
**Varför så:** Flyttar valideringen FRÅN efter gränsen (en KeyError djupt i
Fall_Back_Logic) TILL vid gränsen (tydligt fel som pekar på vilken input + kolumn).
Volym-golvet *är* 73%-drop-skyddet, befordrat från sond till blockerande invariant.
**Kör:**
```
py -3.11 verify_tool\pipeline_contracts.py --calibrate   # visa faktiskt innehåll
py -3.11 verify_tool\pipeline_contracts.py               # blockerande
```

### 4. `prefilter_unpriced.py` — är en känd dataavvikelse hanterad rätt?
**Vad:** Additiv pre-filter som *explicit* tar bort icke-prissatta poster (null
ItemCode på kategorin "Internal", t.ex. labbreagens) innan de når väven, loggat,
och *flaggar* misstänkt null på prissatt produkt (äkta bugg).
**När:** I run_step6.preflight, före pipeline_contracts.
**Varför så:** I BCG-koden faller dessa redan ur — men tyst, via en inner join.
Rätt utfall, fel mekanism: en verklig produkt som tappar sin nyckel skulle gömma
sig i samma tysta hål. Filtret gör det avsiktliga explicit och synligt, utan att
röra BCG-koden. *Lärdom: ibland är "felet" en sonds upptäckt av ett korrekt utfall
som sker ömtåligt — laga mekanismen, inte utfallet.*
**Kör:**
```
py -3.11 verify_tool\prefilter_unpriced.py --report   # visa vad som filtreras
```

### 5. `run_smoke_facit.py` — ger limmet känt utfall? (helt offline)
**Vad:** End-to-end rök-test mot frozen facit. Kör lager 1 (dry_run_full) + lager 2
(window_coherence, lokal) + lager 3 (profilera Final_Fallback och jämför mot en
fryst referens: radantal, distinkta keys, F-fördelning, elasticitet-median).
**När:** När du vill bevisa att limmet är obrutet — efter ändringar i fogmassan,
före en färsk körning. Sekunder, ingen token/VM/Blob.
**Varför så:** Frozen facit är "rätt droppe" — hela populationen vid känd tidpunkt
med känt utfall. En enskild produkt går inte att testa isolerat (elasticiteten
beräknas relativt hela populationen). Referensen fryser inte bara talen utan din
*förståelse* av vad de betyder; drift på oförändrad data = regression i limmet.
**Kör:**
```
# ENGÅNG: bless:a en känd-god referens (gör det MEDVETET — förstå talen först)
py -3.11 verify_tool\run_smoke_facit.py --bless --fallback-file "<känd-god Final_Fallback.xlsx>"
# DÄREFTER: bevisa att limmet är obrutet
py -3.11 verify_tool\run_smoke_facit.py
```

---

## Körordning — den dagliga rytmen

**Före en färsk körning (struktur + synk):**
```
py -3.11 verify_tool\dry_run_full_pipeline.py --end <YYYY-MM-DD>        # passar skarvarna?
py -3.11 verify_tool\run_smoke_facit.py                                  # är limmet obrutet?
```

**I EFTER-kedjan (run_after.preflight bör anropa):**
```
window_coherence  → alla familjer i synk mot fönstret?  (annars STOP)
prefilter_unpriced → icke-prissatta bort, misstänkta flaggade
pipeline_contracts → varje Step 6-input rätt form/volym  (annars STOP)
```

**Efter en färsk körning (valfritt, conservation — ej byggt än):**
Population in vs ut per skarv. Nästa naturliga lager när ovanstående suttit ett tag.

---

## Referens-fingeravtryck (facit, blessad 2026-06)

Det första blessade utfallet — limmets fingeravtryck på facit-data:
- **108 979 rader**, **15 128 distinkta ProductKeys** (~7 rader/produkt = per produkt×site)
- **elasticitet-median −0.4968**

Varje framtida smoke-körning jämförs mot detta inom tolerans (radantal/keys ±0.5%,
median ±0.02, F-nivå ±2 pe). Toleranserna är satta snävt för att facit är
deterministisk — vidga endast med dokumenterad motivering.

---

## Öppna trådar (ärligt — inte allt är klart)

1. **`window_coherence --via-blob` oprövad mot levande token.** Rättad blint utifrån
   felmönster (token-död 2026-06-26). Kör en gång med färsk token och verifiera att
   den läser statusfilen rätt + att mjuk degradering utlöses som tänkt.
2. **Conservation-checks ej byggda.** Population in vs ut per skarv (skarv 1–3) är
   det djupaste tysta-tapp-skyddet. Nästa lager.
3. **Rotorsaken till null-nyckel-tappet** (tyst inner join i Fall_Back_Logic rad
   ~252) är skyddad additivt via prefilter, men lever i limmet — inte i BCG. Körs
   Fall_Back_Logic utan runnern kringgås filtret. Medveten avvägning (Chesterton's
   Fence vinner), men dokumenterad.
4. **Toleranser i smoke-testen** är initiala gissningar — kalibrera mot facit-
   determinismen efter första riktiga jämförelsen.

---

## Mönstret att ta med till nästa pipeline

Det här lagret är ett återanvändbart mönster, inte en BCG-specifik lösning:

- **Boundary-kontrakt** vid varje skarv (form + volym + invariant), blockerande,
  kalibrerade mot mätning.
- **Tvärgående koherensgrind** när flera parallella grenar måste mötas.
- **End-to-end smoke mot en blessad referens** — frys en känd-god körning, jämför
  varje framtida mot den.
- **Probe-to-invariant:** varje sond som hittar något befordras till en assertion
  eller ett test, och slängs sedan. Detektorer ska krympa, inte växa.
- **Validatorn minst lika feltålig som systemet** — observation loss ≠ failure.

Den generella prompten för att tillämpa detta på ett nytt projekt:
`PROMPT_hitta_validera_cementera.md`.

---

*Förvaltas av Jens Palmö. Valideringslagret är additivt och rör aldrig BCG-kärnan.*
