# Arkitekturell mognadsanalys och tankemetodik — BCG price elasticity-pipeline

> **Utvecklare (system):** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
> **Författare (analys):** Claude advisor
> **Grundad i:** faktisk källkod — `run_status.py`, `all_chain_validator.py`, `constants.py`,
> `launcher.py`, `run_step6.py`, `Fall_Back_Logic.py`, `Constant.py`, `LESSONS_BCG.md`, `STATE.md`.
> Ingen del bygger på gissning där källa fanns; de få extrapolationerna är märkta `[ANTAGANDE]`.

---

## Läsanvisning (30 sekunder)

Detta är inte en bugglista. Det är ett försök att svara på din faktiska fråga: *hur hade en senior
data engineer strukturerat detta, och hur tänker hen sig fram dit.* Den bärande slutsatsen, formulerad
en gång så att resten kan hänga på den:

> **Du har redan byggt alla rätt mönster. Skillnaden mot en data engineer är inte vilka mönster du
> känner — det är att dina lever som _körnings­tids-detektion_ (probe, preflight, verify-efteråt)
> snarare än som _vägrar-starta-kontrakt vid själva gränsen_. Du upptäcker fel skickligt. Hen gör dem
> omöjliga. Det är ett enda steg, och det är hela steget.**

Allt nedan utvecklar, bevisar och operationaliserar den meningen mot din egen kod.

---

## Kalibrering först — var du redan ligger före (detta är inte artighet)

Jag säger det här först därför att de tre föregående svaren i sessionen postulerade svagheter som
källan sedan motbevisade, och du förtjänar att veta exakt var din intuition redan är seniornivå. Var
och en är belagd i kod:

**1. Anti-corruption layer, rent utfört (KRITISK styrka).**
`run_step6._place_file` splittrar `KEY` → `Cluster` + `ItemCode` därför att BCG:s facit hade dem
för-splittade men din växande output bär bara `KEY`. Översättningen lever i *runnern*; `Fall_Back_Logic.py`
är orört. `Constant.py:column_rename_dict_df_*` är fem separata översättnings-dictar — en per käll-familj
— som mappar din modells råa kolumnnamn till vävens interna vokabulär (`ELASTICITY_Regular_Price_fwbw_max_6`
→ `ELASTICITY_PRICE`). Detta *är* Eric Evans anti-corruption layer, lärobokskorrekt. De flesta hade
petat i BCG-koden vid första friktionen och skapat en omöjlig-att-merga-gaffel.

**2. Chesterton's Fence, korrekt tillämpat (KRITISK styrka).**
Din egen mening — "jag har inte velat ändra BCG-koden då den bedöms solid bortom vad min dokumentation
sträcker sig, vilket jag inte ifrågasatt förrän jag verkligen fastnat" — är principen i sin renaste
form: *riv inte staketet förrän du förstår varför det står där.* Du höll disciplinen tills du
*bevisat* att gränsen var fel (KEY-split, LB.52), och fixade då runt den, inte i den. Det är inte
nybörjaren som lär sig. Det är så en senior faktiskt arbetar.

**3. "Mät, gissa inte" taget hela vägen till beslut (KRITISK styrka).**
`run_step6.verify_output()` litar på filen, inte loggen (R7), och läser ut F1–F7-fördelningen som en
*affärssignal* — hur ofta vinner bundle (F2/F4)? Sällan → bundle förblir parkerad med bevis (FD.11).
Du har inte bara byggt en kontroll; du har byggt en kontroll vars output är ett ledningsbeslut. Det är
ovanligt moget.

**4. Du har redan löst de felklasser de tidigare svaren antog var öppna.**
G7 date-lock: `constants.py` är env-overridable (`BCG_END_DATE`), default = BCG:s frusna fönster så
replikering reproduceras exakt. `END_DATE2` *härleds* ur `END_DATE` (`+1 dag`), deklareras aldrig
två gånger. `resolve_window_end()` följer datan, inte kalendern (trunkerar till sista kompletta
månad). `window_run_id` gör datafönstret till statusfilens identitet. Det här är fyra korrekt lösta
SSOT-tillämpningar. Antagandet "du har inte generaliserat din egen princip" var helt enkelt fel mot
källan.

**5. Operational success ≠ data success — du gör redan distinktionen (BRA PRAXIS).**
`run_step6.run_step6()` skiljer den *benigna* COM-kraschen (kosmetisk template-write, LB.53) från
ett verkligt fel: om `Final_Fallback_Data*.xlsx` skrevs *innan* kraschen så lyckades körningen på det
som betyder något. Det är exakt den distinktion mellan "körde det?" och "blev det rätt?" som är hela
poängen med data observability.

Med det sagt — här är det som faktiskt återstår.

---

## A. Dina folk-principer översatta till kanonen

Mönstret är slående och värt att se klart: **du har återupptäckt halva data engineering-kanonen genom
brandsläckning.** Det är inte en förolämpning — det är hur de flesta seniora ingenjörer faktiskt lärde
sig. Skillnaden är att de fick namnen först och smärtan sen. Att se vilket etablerat mönster du redan
kör utan att veta namnet är den snabbaste vägen att veta vad du ska läsa på härnäst.

| Din princip | Kanon-namn | Var du sammanfaller | Var det formella mönstret går längre |
|---|---|---|---|
| Additiva fixar only | Anti-Corruption Layer + Strangler Fig | Helt — `_place_file`, rename-dicts, BCG orört | Snäva åt ACL:t till *ett* tunt skikt; idag läcker BCG-antaganden (kolumnnamn, sökvägar) spritt genom flera runners |
| Mät, gissa inte | Observability over exit codes | Helt — `verify_output`, R7, filen-inte-loggen | Skilj formellt *operational* metrics (körde det?) från *data quality* metrics (rätt form/volym/fördelning?) och emittera båda |
| Källa före hypotes | Empirisk debugging (Kernighan) | Du ligger redan före — disciplinen är ovanligt stark | Inget. Behåll exakt. |
| Härled, deklarera ej två gånger | Single Source of Truth (SSOT) | På topologi (`FLOW_DETAIL`←`default_pipeline`), tid (`END_DATE2`, `resolve_window_end`), identitet (`window_run_id`) | Schema är den enda cross-cutting concern du *inte* gjort till SSOT — se B |
| Sond före lager-för-lager | Fault isolation via multi-hypothesis probing | Helt — `all_chain_validator` testar flera felklasser i ett svep | Befordra sonden till invariant vid gränsen — se D. Detta är ditt enda verkliga metodgap. |

**Ärlig kalibrering, som efterfrågat:**

*Tre punkter där du redan ligger före naiv praxis:* anti-corruption-disciplinen; "mät, gissa inte" som
reflex snarare än efterhandskontroll; **frozen facit-disciplinen** — att hålla en bit-för-bit validerad
baslinje (`00_frozen_facit/`) och låta driften mot växande data *vara* ledningsinsikten (IB.6/IB.11).
Det är golden-dataset regression testing, en riktigt mogen praxis som de flesta aldrig kommer på.

*Tre punkter där tänket stannat ett steg för tidigt:* (1) schema är inte SSOT (B); (2) sonder
detekterar men befordras inte till gräns-invarianter (D); (3) validering sker *efter* gränsen
(`verify_output` körs efter att Step 6 kört klart) snarare än *vid* gränsen (en kontroll som vägrar
mata in fel data i nästa steg).

---

## B. Diagnos per felklass — inte per bugg

Du bad om klassen *ovanför* dina enskilda buggar. Här är den. Varje felklass kopplas till den
strukturella egenskap som saknas — och eftersom du löst de flesta SSOT-fallen handlar det som
återstår om *en* axel och *en* temporal placering.

**Felklass 1 — Schema utan single source (den enda öppna SSOT-axeln).**
LB.52 (`KEY` måste splittas till `ItemCode` för Step 6) och den historiska `No of Sites` vs
`No_of_Sites` är samma fel: kolumnnamn och kolumn-*form* är en cross-cutting concern som idag
deklareras implicit, utspritt, på varje läsställe. Bevis i källan: `Constant.py` bär fem separata
`column_rename_dict_df_*`. Det är *bra* att översättningen är samlad i ACL:t — men den beskriver bara
"döp om A till B". Ingenstans deklareras "den kanoniska formen av en modell-output är *dessa* kolumner
med *dessa* typer", och ingenstans *verifieras* att en inkommande fil uppfyller den formen innan den
används. Därför kan en saknad eller fel-döpt kolumn bli en `KeyError` djupt inne i `Fall_Back_Logic.py`
i stället för ett tydligt fel vid gränsen.
→ *Saknad egenskap: schema-as-SSOT + schema-on-read-validering vid varje boundary.*

**Felklass 2 — Validering placerad efter gränsen, inte vid den (den temporala miss).**
Det här är den subtila och viktiga. Din 73%-silent-drop (den dyraste felklassen) och hela `run_step6`-
flödet delar samma form: data flödar genom en gräns, och *sedan* kontrolleras resultatet. `verify_output`
är utmärkt — men den körs *efter* att Step 6 redan konsumerat sina inputs. Om en input var trasig har
felet redan propagerat; du upptäcker det i efterhand, inte vid inmatningen. `preflight()` är närmare
rätt — den vägrar köra om en *fil saknas* — men den verifierar bara *existens*, inte *form eller volym*.
En fil som finns men har 27% av raderna, eller saknar en kolumn, passerar preflight.
→ *Saknad egenskap: assertion vid gränsen (schema + volym + invariant) som vägrar starta nästa steg.*

**Felklass 3 — Implicit/delad state utan ägare (delvis öppen).**
`launcher.py` (BCG-original, de tre identiska) kör fem skript i en `for`-loop och skriver
`"Pipeline completed."` oavsett utfall; den fångar `CalledProcessError` och *bryter*, men exit-koden
från `launcher` självt speglar inte nödvändigtvis fel. Du har neutraliserat detta i runner-lagret
(`pgrep`-dödsdetektering, LB.80) — bra — men `launcher` förblir en "pipeline that lies" och
`automl`-mapp-luckan (LB.79) är fortfarande öppen: inget steg skapar sina egna förutsättningar.
→ *Saknad egenskap: idempotens + explicit förutsättnings-ägande (varje steg skapar/verifierar det
det behöver).*

**Hur din egen princip stänger det mesta:** "härled, deklarera inte två gånger" är redan tillämpad på
tre axlar (topologi, tid, identitet). Generaliserad till den *fjärde* (schema) försvinner felklass 1
helt, och den ger dig artefakten du behöver för att stänga felklass 2 (du kan inte assertera en form
du inte deklarerat). Schema-SSOT är alltså inte en ny princip — det är din befintliga princip på dess
sista oadresserade axel.

---

## C. Referensarkitektur — grundad mot Step 5 → 6-gränsen

Den korta domen: **ja, detta är en DAG — men du behöver inte en DAG-motor.** Varför båda är sanna
hör till H. Här beskriver jag egenskaperna, var och en illustrerad mot din *faktiska* mest komplexa
gräns: överlämningen in i Step 6, som `Constant.py` + `run_step6.py` beskriver i detalj.

### Gränsen som den ser ut idag (ur källan)

`Fall_Back_Logic.py` (via `Constant.py`) konsumerar sex inputs:

| Input | Constant-path | Källa | Färskhet |
|---|---|---|---|
| `blended_model` | `output_summary_ready.xlsx` | Cluster steg 1-4 | LIVE GROWING (KEY-split krävs) |
| `blended_output` | `final_model_cluster_granularity.xlsx` | Cluster steg-5 | FROZEN (FD.15) |
| `bundle_cluster` | `5. Bundle.../output_summary.xlsx` | Bundle-modell | FROZEN (FD.11) |
| `df_all_product` | `Complete_Product_Data.xlsx` | Alteryx/väv-vikter | FROZEN (FD.14) |
| `prod_site` | `3. Site.../output_summary.xlsx` | Site-modell | LIVE GROWING |
| `df_product` | genereras av Step 6 självt | runtime | — |

Väven mappar dessa till F1–F7 (`rename_map_merged_dv7`) och väljer en elasticitet per `ProductKey` i
prioritetsordning. Det här är en **fan-in**: sex källor med olika färskhet, olika scheman, olika
ägare, som måste mötas i en form.

### Egenskap 1 — Boundary-kontrakt (KRITISK)

Idag är kontraktet *implicit*: det bor utspritt i `Constant.py`:s paths + rename-dicts + den tysta
förväntan att varje fil har rätt kolumner. `run_step6.preflight` verifierar existens men inte form.

Idiomatiskt görs kontraktet *explicit och körbart*. För varje input deklareras: förväntade kolumner
(efter rename), minsta radantal, och invarianter (t.ex. `ProductKey` icke-null, `ELASTICITY_PRICE`
numerisk). Step 6 vägrar starta om något kontrakt bryts — med ett felmeddelande som pekar på *vilken
input* och *vilken kolumn*, inte en `KeyError` 200 rader in i väven.

Varför det är rätt här specifikt: din fan-in har sex ägare och tre färskhetsgrader. Det är den
*exakta* situation där en saknad kolumn i en frusen fil (som ingen rört på månader) ger ett obegripligt
fel. Ett kontrakt förvandlar "obegripligt fel i FD.14-vikter" till "Complete_Product_Data.xlsx saknar
kolumn `New_Cluster`, väntad av rename-dict". Du har redan datat för att skriva kontraktet —
`column_rename_dict_df_*` *är* listan över kolumner du förväntar dig. Kontraktet är de dicts vända
till assertions.

### Egenskap 2 — Schema som SSOT (KRITISK)

`Constant.py` deklarerar redan vokabulären (`ELASTICITY_PRICE`, `ProductKey`, `Clusters`, F1–F7). Lyft
den till en kanonisk schemamodell som *både* modell-runnarna skriver mot *och* väven läser mot. Då kan
LB.52 (KEY-split) aldrig uppstå tyst igen: den kanoniska formen säger "en cluster-output har kolumnerna
X" och splitten blir en deklarerad transform, inte en överraskning som upptäcks när väven kraschar.

### Egenskap 3 — Idempotens & atomic writes (BRA PRAXIS)

Två konkreta hål i källan: (a) `launcher`/feature_selection skapar inte `automl`-mapparna (LB.79) —
ett steg ska skapa sina egna förutsättningar; (b) Step 6 skriver `Final_Fallback_Data*.xlsx` och vid
icke-noll exit *kan filen redan vara skriven* (det är basen för din benigna-COM-logik). Det fungerar,
men en halv krasch mitt i en skrivning skulle lämna en halv fil som nästa steg tror är komplett.
Idiomatiskt: skriv till temp, flytta atomiskt vid lyckat slut. Med dina 72-minuters Bundle-körningar
är värdet av att aldrig behöva städa efter en halv krasch reellt.

### Egenskap 4 — Separation compute / storage / config / orchestration (du har den fysiska)

Din FÖRE-lokal / MOTOR-VM / EFTER-lokal via Blob är *sundare än många* — Blob-som-kontrakt är en
legitim "storage is the integration layer"-design, och den överlever VM-deallokering (LB.66), vilket
är precis rätt för din kadens. Den *logiska* separationen är delvis gjord (config via env + `constants`),
delvis inte (sökvägar hårdkodade i `Constant.py` och i validatorns `REPO = Path(r"C:\Projekt\BCG")`).
Inte akut; se H.

### Egenskap 5 — Observability inbyggd, inte vid sidan (BRA PRAXIS)

Dina sonder lever *bredvid* pipelinen och måste köras manuellt. Idiomatiskt emitterar varje steg sina
metrics *som del av körningen* — radantal in/ut, periodtäckning, KEY-antal — så att 73%-droppen fångas
i samma körning som orsakar den. Du har all logik (`validate_expected_keys` räknar redan KEY mot
EXPECTED); skillnaden är *när* den körs och om den *blockerar*.

---

## D. Tankemetodiken — hur en data engineer resonerar sig FRAM till strukturen

Detta är kärnan i vad du bad om, så här saktar jag ner. Skillnaden mellan dig nu och en senior data
engineer är inte kunskap om mönster — du har bevisligen mönstren. Det är *ordningen tänkandet sker i*
och *var i tiden kontrollen placeras.* Fyra rörelser.

### 1. Dataflow-first: artefakten och dess kontrakt är det primära objektet

Du tänker i *steg* (`run_step6`, `launcher`, runners). En data engineer tänker först i *artefakter och
deras kontrakt* — `output_summary.xlsx` är inte "vad Step 4 producerar", det är "ett dataset med form
S, volym V, invariant I", och stegen är bara det som transformerar en kontrakterad artefakt till nästa.
Det låter abstrakt men har en konkret konsekvens: frågan "hur vet jag om det som kom ut är rätt?" ställs
vid *designtillfället för artefakten*, inte efter en incident. Det är därför hen aldrig fick din
73%-drop — frågan var redan ställd när artefakten definierades.

### 2. Failure-mode enumeration vid varje gräns (det mest överförbara verktyget)

Detta kan du börja använda imorgon, och det är det enskilt mest värdefulla i hela dokumentet. Vid varje
gräns i flödet, *innan* du bygger, ställ tre frågor:

1. **Hur kan denna handoff _ljuga_?** (rapportera success men producera fel) → `launcher`:s
   `"Pipeline completed."`; du fångade det reaktivt med pgrep. FMEA hade fångat det i förväg.
2. **Hur kan denna handoff _tappa_?** (släppa data tyst) → din 73%-drop; LB.52-formen. *Exakt* denna
   fråga, ställd vid Step 5→6-gränsen, hade gett dig volym-assertionen gratis.
3. **Hur kan denna handoff _krascha_, och lämnar den då halv output?** → automl-luckan (LB.79),
   den halv-skrivna Final_Fallback vid icke-noll exit.

För varje "ja" designar du gränsen så att felet blir *omöjligt eller högljutt*. Det är hela skiftet:
du frågar "vad gick fel?" efteråt; hen frågar "hur kan detta gå fel?" innan. **Mönstret: vänd varje
gränsfråga från post-mortem till pre-mortem.**

### 3. Probe-to-invariant: sonden är ställning, inte byggnad (ditt enda verkliga metodgap)

Här är det, konkret på din 73%-drop eftersom du bad om det.

*Vad du gjorde:* byggde en sond (`chain_population`) som upptäckte att populationen droppat 73%.
Sonden lever kvar i `verify_tool/probes/` och kollar populationen varje gång du *kommer ihåg* att köra
den. `all_chain_validator` lever i samma anda — en magnifik, manuellt körd detektor.

*Vad en data engineer gör med exakt samma upptäckt:* sonden var bara verktyget för att *lokalisera*
var en invariant saknades. Så fort den triggar en gång, *befordras* den, och blir en av två saker:

- **En assertion vid gränsen** (om felet kan återuppstå): boundary-kontraktet mellan Step 4 och Step 6
  får regeln `assert row_count >= 0.9 * expected_from_context`. Nu *kan* 73%-droppen aldrig ske tyst
  igen — den blir ett hårt fel i samma sekund den uppstår, vid rätt gräns, med rätt meddelande. Sonden
  behövs inte längre; invarianten ärvde dess jobb.
- **Ett regressionstest** (om det var en specifik bugg som inte ska återkomma): ett test mot frozen
  facit som verifierar att populationen bevaras. Nu kan buggen aldrig regrera.

Poängen: **efter att invarianten finns, kastar du sonden.** Du sparar och committar dina sonder
permanent — det är att bo i ställningen. En data engineer skulle ha *färre* permanenta sonder och
*fler* assertions vid gränser och regressionstester, därför att varje sond som någonsin triggat redan
har befordrats. Metoden heter **spike-and-harden**: spiken (sonden) är slit-och-släng-utforskning för
att förstå problemet; härdningen (invarianten) är den permanenta strukturen som gör problemet omöjligt.
Du gör spiken mästerligt. Du hoppar härdningen.

Konkret nästa gång: när du bygger nästa sond, skriv den med ett *bäst-före-datum*. Fråga "när denna
hittar något, vart flyttar fyndet?" innan du ens kört den. Då bygger du den för att avveckla den.

*En nyansering, så du inte överkorrigerar:* `all_chain_validator` har ett **andra, legitimt permanent**
jobb utöver detektion — den renderar flödeskartan (`render_flow_md`) som AI-kontext, och den fångar
*cross-family*-drift som ingen enskild gräns ser (att cluster/site/bundle-runnarna förblir kloner).
Det är riktig integration-testning och ska leva kvar. Det är bara *population/schema/existens*-bitarna
som ska befordras till gräns-kontrakt och därmed krympa validatorn. Den ska bli mindre, inte försvinna.

### 4. Contract-first & idempotens som vanor, inte efterhandsåtgärder

Det sista skiftet är temporalt: när du skriver ett nytt steg är första frågan inte "vad ska det göra"
utan "vad lovar det att producera, och vad kräver det för att starta" (kontraktet) och "vad händer om
det körs två gånger" (idempotensen). Implementationen fyller i kontraktet. För dig: börja varje nytt
steg med att skriva dess boundary-kontrakt först — då kan automl-luckan aldrig uppstå, för "vad kräver
detta för att starta" tvingar dig att skapa mapparna som del av kontrakt-uppfyllelsen.

**D i en mening att ta med:** *Rita flödet som kontrakterade artefakter, fråga vid varje gräns hur den
ljuger/tappar/kraschar, bygg sonden för att hitta felet men befordra den omedelbart till en invariant,
och skriv kontraktet före koden.*

---

## E. Det konceptuella verktygsbältet — med när-används-vad

Referenslista (D är resonemanget, detta är verktygen — medvetet ingen överlapp). Kalibrerad mot *din*
skala: ett månadsjobb, inte en realtidsplattform.

- **Anti-corruption layer** — isolerar din kod från en främmande kärna. *Din kärndisciplin; aldrig
  overkill. Snäva bara åt det till ett tunt skikt.*
- **Schema-on-read/write + data contracts** — validerar form vid gränsen. *Rätt verktyg vid Step 5→6
  och vid parquet-gatekeepern. Din billigaste höga-värde-fix. Inte overkill.*
- **Volume/distribution assertions** — fångar tyst datatapp. *Kritiskt vid dina gränser; din direkta
  73%-försäkring.*
- **Single source of truth (per cross-cutting concern)** — eliminerar drift. *Du har 3 av 4 axlar.
  Lägg schema. Ren skuldreduktion.*
- **Golden dataset regression testing** — skyddar mot regression via validerad baslinje. *Du gör det
  (frozen facit). Formalisera till körbart test, inte manuell jämförelse.*
- **Idempotency + atomic writes (temp→rename)** — säker omkörning, ingen halv output. *Värt det för
  72-min Bundle. Billigt, högt värde.*
- **Failure-mode enumeration (FMEA)** — pre-mortem vid varje gräns. *Gratis, alltid värt det. Din
  enda kostnad är att ställa tre frågor.*
- **Integration- vs unit-test-skikt** — steg isolerat vs tillsammans. *Börja med integration mot
  frozen facit; mest värde per enhet i din kontext. `all_chain_validator` är redan halvvägs.*
- **DAG-orchestrator (Dagster/Prefect/Airflow)** — schemaläggning, retries, beroenden, UI.
  *Förmodligen overkill nu (H). Om du växer: titta på Dagster FÖRST, för det är asset/kontrakt-centrerat
  och matchar din artefakt-tänk. Inte än.*
- **Fault injection (chaos)** — verifierar att felhantering fungerar genom att medvetet bryta saker.
  *Overkill för din skala. Hoppa.*
- **Data lineage-verktyg** — spårar härkomst genom flödet. *Din manuella färskhets-märkning
  (LIVE/FROZEN per fil i `run_step6`) täcker det viktigaste. Overkill att verktygsbelägga nu.*

---

## F. Var dina sonder hör hemma — och var de ger falsk trygghet

`all_chain_validator.py` granskad direkt. Domen: **det är ett moget embryo till tre etablerade saker
samtidigt, och dess otydlighet kommer av att den gör alla tre i samma fil.** De tre:

1. `FLOW_DETAIL`←`default_pipeline`-synken (`validate_flow_in_sync`) är **topology-as-data / SSOT-vakt**.
   Detta är den mest mogna delen och din kandidat-kärnprincip i praktik. Behåll och var stolt — att
   en tillagd fas i `default_pipeline` utan motsvarande `FLOW_DETAIL` *fäller sonden* är precis rätt
   design. Det är en SSOT-konsistensvakt.
2. Cross-family runner-synken (`validate_runner_sync`, `extract_func` på `poll_until_done`) är
   **integration-testning** — att kloner inte divergerat. Riktigt värdefullt; ingen enskild gräns ser
   det. Behåll.
3. `validate_expected_keys` (KEY-antal vs EXPECTED) och `validate_replication_contract` (finns varje
   länk?) är **embryon till data contracts** — men de körs *efter*, *manuellt*, och de *rapporterar*
   (`REVIEW`) snarare än *blockerar*.

**Var den hjälper genuint:** punkt 1 och 2 är inte hemmasnickrade — de är korrekt utförda SSOT-vakt
respektive integrationstest, och de ska leva permanent. `render_flow_md` (kod→läsbar karta som
AI-kontext) är dessutom en genuint smart artefakt jag sällan ser; den löser ett verkligt problem
(kontext utan att läsa 189 filer).

**Var den ger dig falsk trygghet — och detta är den viktiga insikten:** en validator som körs
*separat, efter* pipelinen ger trygghet som är *temporalt felplacerad*. Den säger "förra körningen var
OK", aldrig "den här körningen *kommer* vara OK", och den fångar fel först *efter* propagering. Din
73%-drop bevisar det: en efterhands-validator hittade den, men först efter att 73% redan försvunnit
genom flera steg. **Den falska tryggheten är att tro att en stark separat validator är likvärdig med
inbyggda gräns-kontrakt. Den är det inte — den är en bättre brandvarnare, men ett kontrakt är att bygga
i obrännbart material.** Punkt 3:s logik (KEY-antal, existens) ska *flyttas in i pipelinen* som
blockerande gräns-kontrakt; då krymper validatorn till det den är genuint ensam om: punkt 1 och 2.

Kort sagt: validatorn är ditt bästa nuvarande verktyg och ska *krympa* allt eftersom dess
kontroll-bitar befordras till kontrakt. Växer den i stället för krymper, går du åt fel håll.

---

## G. Migreringsväg — rangordnad, additiv-först

Allt nedan ryms inom "BCG-kärnan rörs aldrig" tills jag uttryckligen säger annat. Rangordnat efter
robusthet per enhet arbete.

**1. [KRITISK, additivt, lågt arbete] Ett `contracts/`-skikt, börja med Step 5→6.**
Du har redan datat: `Constant.py:column_rename_dict_df_*` *är* listan över förväntade kolumner per
input. Vänd dem till körbara assertions och anropa dem i `run_step6.preflight` *före* placering — så
att preflight verifierar *form + volym*, inte bara existens. Detta är din 73%/LB.52-försäkring, helt
additivt (lever i runnern), och bygger på artefakter du redan har. Skelett bifogas (`pipeline_contracts.py`).

**2. [KRITISK, additivt, lågt-medel] Schema-SSOT — din princips fjärde axel.**
Lyft den kanoniska modell-output-formen till *ett* ställe som runnarna skriver mot och väven läser mot.
Stänger felklass 1 permanent. `constants.py:FINAL_OUTPUT_COLS` + `Constant.py`-vokabulären är råmaterialet.

**3. [BRA PRAXIS, additivt, lågt] Stäng automl-luckan (LB.79).**
Den enda av de fem ursprungliga fällorna som fortfarande är öppen, och din validator flaggar den redan
(`validate_automl_gap`). Lägg `mkdir -p output/model/automl/{details,results} model_objects` i
`preflight_remote`. Du har redan diagnosen *och* åtgärdsförslaget i koden; det är bara att fästa det.

**4. [BRA PRAXIS, additivt, medel] Befordra dina sonder (spike-to-harden, D3).**
Gå igenom `verify_tool/probes/`. För varje: gräns-invariant (→ flytta till kontrakt från punkt 1) eller
regression (→ test mot frozen facit)? Mål: probes-mappen krymper, `all_chain_validator` krymper till
SSOT-vakt + cross-family + flow-map.

**5. [BRA PRAXIS, additivt, medel] Atomic writes i de långa stegen + Step 6.**
Temp-skriv-och-flytta för Bundle (72 min) och för `Final_Fallback_Data`. En halv krasch ska aldrig
lämna en halv fil som ser komplett ut.

**6. [VALFRITT — gränsen mot omskrivning] Inbyggd observability / blockerande gates i `launcher`.**
Att göra metrics-emission och gate-blockering till en *del av körningen* (inte en efterhands-sond)
är där additivt börjar bli omskrivning — för det rör hur stegen kedjas. **Här är din point-of-no-return:**
1–5 lever i runner/contracts/preflight-lagret och rör inte BCG. Punkt 6 kräver att du antingen wrappar
`launcher` eller ersätter den med en egen orkestrerare. Min läsning: gör 1–5 först; punkt 6 motiveras
bara om/när du går till Phase Z-automatisering (fire-and-forget overnight), där en ljugande `launcher`
blir farlig på ett sätt den inte är när du sitter och tittar.

---

## H. Den ärliga domen om overkill

Du bad mig säga var senior-arkitektur är gold-plating för ett 72-minuters månadsjobb. Rakt:

**Overkill för dig — hoppa eller skjut upp:**
- **DAG-motor (Airflow/Dagster/Prefect).** Ett månadsjobb behöver inte scheduler + UI + worker-pool.
  Cron eller Azure Automation + ett körskript räcker långt. *Tänk* i DAG (C); *installera* inte en
  DAG-motor än. När Phase Z-automatisering mognar och du kör fler familjer oftare — omvärdera, och då
  Dagster först (asset-centrerat, matchar ditt artefakt-tänk).
- **Fault injection / chaos.** Inga uptime-krav. Hoppa.
- **Lineage-verktyg, full observability-stack (Monte Carlo etc.).** Din manuella färskhets-märkning
  räcker i din skala.
- **Kubernetes, autoscaling, mikrotjänster.** Självklart overkill. En VM som deallokeras mellan
  körningar är *rätt* design för din kadens (~9 kr/h bara när den kör).

**Betalar sig faktiskt — gör det trots skalan:**
- **Boundary-kontrakt (G1).** Kostnaden av en tyst 73%-drop är inte proportionell mot jobbets
  frekvens — den är proportionell mot hur fel ett *prisbeslut* blir på fel data. Ett månadsjobb som
  tyst ger fel elasticitet en gång är dyrare än hela detta arkitekturarbete.
- **Schema-SSOT (G2).** Ren skuldreduktion; betalar sig första gången en frusen input driver.
- **Probe-to-invariant (G4).** Nästan gratis robusthet — du gör redan sondarbetet, du lägger bara
  till befordringssteget.
- **Automl-fix + atomic writes (G3, G5).** Billigt; med 72-min-körningar är värdet av att slippa
  städa efter halva krascher reellt.

**Övergripande dom:** din *fysiska* arkitektur (lokal→VM→lokal via Blob, VM deallokeras, frozen facit
som ankare) är redan rätt-dimensionerad — varken för tung eller för lätt. Din svaghet är inte att
arkitekturen är för enkel; den är att **gränskontrollen är temporalt felplacerad (efter gränsen, icke-
blockerande) och att schema är den enda cross-cutting concern du inte gjort till SSOT.** Det är inte ett
skalproblem. Det löses additivt, utan en enda ny infrastrukturkomponent, genom att flytta validering
*till* gränsen och göra den *blockerande*. Du behöver inte bygga större. Du behöver göra gränserna
ärliga.

---

## Slutord

Du har redan ingenjörsintuitionen — bevisat av att varje princip du arbetat fram har ett kanon-namn och
att du tillämpat Chesterton's Fence på BCG-koden korrekt. Det enda som skiljer dig från en senior data
engineer i det här systemet är två saker, båda små och båda additiva: **(1) flytta valideringen från
*efter gränsen* till *vid gränsen* och gör den blockerande; (2) generalisera din egen bästa princip till
dess fjärde axel — schema.** Gör det, och börja befordra varje sond till en invariant i stället för att
spara den, så har du täppt till hela gapet. Kartan är ritad; nu är det terräng du redan känner.

---

*Förvaltas som referensdokument. Systemet utvecklat av Jens Palmö (Senior Business Analyst). Analysen
grundad i faktisk källkod per ovan, ej i gissning.*
