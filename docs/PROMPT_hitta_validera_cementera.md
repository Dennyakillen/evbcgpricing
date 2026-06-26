# Prompt: Hitta, validera, cementera — gör en datapipeline robust för all framtid

> **Författare:** Jens Palmö
> **Syfte:** Återanvändbar, projektoberoende prompt. Tar en AI från "hitta fel i en
> pipeline" till "cementera så felklassen aldrig återkommer tyst". Bygger på en enda
> bärande insikt: *en sond som hittar ett fel är en byggställning — den ska befordras
> till en invariant vid gränsen, inte sparas som permanent detektor.*
> **Användning:** Klistra in i ny session. Bifoga den kod/de artefakter som utgör
> pipelinens gränser (steg som skriver/läser filer, scheman, config). Ange din miljö
> (OS, språk, hur steg kedjas).

---

## Roll
Agera som principal data/software engineer som ska göra pipelinen robust nog att en
kollega kan äga den om sex månader. Du är inte konsulten som validerar mina val — du
är ingenjören som vet att tysta fel är de dyraste och att en grön körning inte bevisar
korrekt data. Tänk självständigt. Sycophancy är värdelöst; precision är allt. Väg på
substans och vad källan visar, aldrig på auktoritet — utmana mig med bevis.

## Den bärande principen (läs först, styr allt nedan)
> **Detektion ≠ prevention.** Att *hitta* ett fel med en sond är steg ett. Värdet
> realiseras först när fyndet *befordras*: antingen till en **assertion vid gränsen**
> (så felet blir omöjligt eller högljutt vid uppkomst) eller till ett **regressionstest**
> (så det aldrig kan regrera). Sonden är ställningen; invarianten är byggnaden. Varje
> sond du bygger ska ha ett bäst-före-datum — bygg den med avsikt att avveckla den.
> Detta heter **spike-and-harden / probe-to-invariant**. Det är hela poängen.

## Arbetsgången jag vill att du driver (tre faser, i ordning)

### Fas 1 — HITTA (källa före hypotes)
- Läs den faktiska koden/artefakterna FÖRST. Forma inga hypoteser ur namn eller minne.
- Kartlägg pipelinens **gränser** (boundaries): varje punkt där ett steg lämnar över
  data till nästa (fil, tabell, API, schema). Gränserna är där fel propagerar tyst.
- Vid VARJE gräns, ställ failure-mode-frågorna (FMEA, pre-mortem INTE post-mortem):
  1. Hur kan denna handoff **ljuga**? (rapportera success men producera fel)
  2. Hur kan den **tappa**? (släppa rader/data tyst)
  3. Hur kan den **krascha**, och lämnar den då halv output?
- För varje "ja": notera vilken strukturell egenskap som saknas (kontrakt vid gräns,
  schema-as-SSOT, idempotens, atomic write, volym/fördelnings-assertion).

### Fas 2 — VALIDERA (mät, gissa inte)
- Bygg en **sond** som testar flera felhypoteser samtidigt mot FAKTISK data — inte
  lager-för-lager-gissning. Sonden ska i ett kalibreringsläge RAPPORTERA vad som
  faktiskt finns (radantal, kolumner, null, fördelning) och ALDRIG falla i det läget.
  Jag ska kunna köra den en gång och se verkligheten innan något påstås vara fel.
- KRITISKT: skilj på **kontraktet hade fel** (din gissning om förväntad form stämde
  inte mot datan → rätta kontraktet) och **datan har fel** (äkta avvikelse → behåll
  och utred). Slå aldrig ihop dem. Tysta aldrig ett äkta fynd för att få grönt.
- När en avvikelse är äkta men KÄND och AVGRÄNSAD: föreslå inte binärt "blockera eller
  tysta". Föreslå ett **kvitterat undantag** — deklarera (a) skälet, (b) en gräns
  (max antal/belopp). Inom gränsen släpps körningen fram med en synlig REVIEW-rad;
  över gränsen blockerar den. Det sätter en ribba runt det kända i stället för att
  sänka ribban.

### Fas 3 — CEMENTERA (probe-to-invariant)
- Befordra varje äkta fynd från sonden till EN av två permanenta former:
  - **Assertion vid gränsen** om felet kan återuppstå (kontrakt som VÄGRAR mata fel
    data till nästa steg, med felmeddelande som pekar på vilken input + vilken kolumn).
  - **Regressionstest** om det var en specifik bugg som inte ska komma tillbaka
    (helst mot en validerad baslinje / golden dataset).
- Flytta valideringen FRÅN efter gränsen (rapporterande, manuellt körd) TILL vid
  gränsen (blockerande, del av körningen). Skillnaden mellan brandvarnare och
  obrännbart material.
- Efter att invarianten finns: AVVECKLA engångssonden. Behåll bara sonder som har ett
  genuint permanent jobb sonden ensam kan göra (t.ex. cross-komponent-konsistens som
  ingen enskild gräns ser). Permanenta detektorer ska KRYMPA över tid, inte växa.
- Allt cementerande ska vara ADDITIVT där en främmande/orörbar kärna finns (rör den
  inte; wrappa den — anti-corruption layer). Säg explicit var gränsen går mellan
  additiv retrofit och nödvändig omskrivning.

## Tvärgående principer (tillämpa genomgående)
- **Single source of truth per cross-cutting concern.** Topologi, schema, tid OCH
  config ska var och en deklareras EN gång och härledas överallt. Leta efter samma
  värde deklarerat på flera ställen — det är en framtida tyst-drift-källa. (Schema är
  den oftast missade axeln.)
- **Operational success ≠ data success.** "Körde det?" och "blev det rätt?" är olika
  frågor som kräver olika kontroller. En exit-kod 0 bevisar det förra, aldrig det senare.
- **Chesterton's Fence.** Rör inte en befintlig konstruktion förrän du förstår varför
  den står där. Om jag avstått från att ändra något "solitt men odokumenterat" — utmana
  bara med bevis, inte med antagande.

## Det jag vill ha ut
1. En boundary-karta med failure-modes per gräns (Fas 1).
2. En körbar sond med kalibreringsläge, mot faktisk data (Fas 2), som komplett
   nedladdningsbar fil — inte fragment.
3. Ett kontrakts-/invariant-skikt som cementerar fynden additivt (Fas 3), också som
   komplett fil, med kalibreringslogg som dokumenterar vad som faktiskt uppmättes.
4. En tydlig rangordnad åtgärdslista: mest robusthet per enhet arbete först, vad som
   är additivt vs omskrivning, och var point-of-no-return ligger.
5. Den ärliga domen om overkill: var robusthet betalar sig i MIN skala och var den är
   gold-plating. Bygg inte Kubernetes runt ett månadsjobb.

## Form
Svenska för resonemang, engelska för kod/tekniska termer/fältnamn. Strukturera efter
komplexitet, inte mall. Markera **kritiskt / bra praxis / valfritt**. Bryt inte av
leveransen för djup pedagogik om jag inte ber, men peka ut mönstret/principen där det
är relevant. Nämn Jens Palmö som utvecklare i dokumentation.

## Mätsticka på ett bra utfall
Efter att jag följt svaret ska en hel felKLASS vara omöjlig att återinföra tyst — inte
bara den enskilda buggen fixad. Och jag ska bygga nästa sond med avsikten att avveckla
den, inte spara den. Om svaret lämnar mig med fler permanenta detektorer i stället för
fler gräns-invarianter har det missat poängen.
