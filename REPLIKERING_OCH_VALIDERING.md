# REPLIKERING & VALIDERING — Hur vi bevisade att vi äger modellen

**Projekt:** `evbcgpricing`
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Det här dokumentets syfte:** en fullständig, fristående redogörelse för arbetet med att
replikera BCG:s priselasticitetsmodell, validera den replikeringen bit-för-bit, och sedan
köra den på Evidensias egen växande data. Det är skrivet så att en utvecklare om flera år —
utan tillgång till oss — kan förstå exakt vad som byggts, hur det bevisats, och hur mycket
evidens som ligger bakom varje siffra. Det här är "vi gjorde jobbet"-dokumentet.

---

## 1. Varför detta finns

BCG levererade en priselasticitetsmodell och en uppsättning slutsatser 2025. Affärsfrågan
var inte "har BCG rätt?" utan "kan Evidensia **äga** detta — köra det själva, på färsk data,
och lita på resultatet för prisbeslut?" Att äga en modell betyder tre saker, i ordning:

1. **Återskapa den exakt** på samma data BCG använde (bevisar att vi förstår metoden, inte
   bara utfallet).
2. **Köra den på färsk, växande data** (bevisar att metoden överlever utanför BCG:s frusna
   snapshot).
3. **Validera den färska outputen** utan ett facit att jämföra mot (bevisar att vi kan
   bedöma korrekthet på egen hand).

Det här dokumentet redogör för alla tre, med bevis för var och en.

---

## 2. Vad modellen faktiskt är

En priselasticitet är den procentuella volymförändringen vid 1 % prisförändring. BCG
skattar den per **produktkod × klinikkluster** med en **log-log-OLS-regression**: i en
log-log-modell *är* priskoefficienten elasticiteten direkt (INSIGHTS IB.7). Regressionen
kontrollerar för säsong och media/PR-effekter.

De flesta fingranulära grupper har för lite data för en stabil skattning — bara ~18 % är
statistiskt signifikanta på rå klusternivå (IB.1). Modellen hanterar det med en
**fallback-väv**: en sjunivåers prioritetskaskad (F1 site → F2 bundle → F3 cluster →
F4 bundle-across → F5 product-across → F6 service-within → F7 service-across). För varje
produkt tas första signifikanta nivån, så glesa grupper ärver en starkare representant
istället för att modelleras dåligt (IB.2). Väven **väljer**, den modellerar inte om.

Datan var alltid Evidensias egen — BCG hämtade den från vårt datavaruhus
(`dbo.Fact_BillingInvoiceRows` joinat mot `dbo.Dim_Item`); deras artikelgruppering är en
grövre ögonblicksbild av vår interna hierarki (IB.4). Den enda genuina externa inputen är
FTE-bemanning från Quinyx (IB.3) — konkurrentdata, externa prisflöden och en "InScope"-
mappning deklareras i BCG:s config men läses aldrig faktiskt av koden (död config, IB.3).

---

## 3. Replikeringen — bevisad bit-för-bit

Vi byggde om pipelinen steg för steg och bevisade att varje steg återskapar BCG:s frusna
output exakt, på BCG:s ursprungliga datafönster. Beviskedjan (`verify_tool\proof_chain\`):

| Steg | Vad som återskapades | Bevis |
|---|---|---|
| **FR-1 Dataprep** | Modellens indata = BCG:s: samma rader, omsättning, volym per rad | korrelation 1.000000, |diff| = 0 |
| **FR-3 Cluster-blend** | Steg-5-representantval per (service, kluster) | 43 / 43 representanter identiska |
| **FR-4 Cluster-modell** | Klusternivå-elasticiteter | 3 812 grupper; beslutsrelevanta identiska |
| **FR-5 Site-modell** | Site-nivå-elasticiteter | 4 673 grupper; rank-korr 0.91 |
| **FR-6 Bundle-modell** | Varukorgs-elasticiteter | 125 grupper; rank-korr 0.93 |
| **FR-7 Fallback-väv** | Hela F1–F7 slutelasticiteten per produkt | 108 979 rader, korr 1.000000, 100 % nivåmatch |

FR-7 är den avgörande: hela väven, end-to-end, producerade **samma slutelasticitet som BCG
för varje produkt, bit-för-bit** (|diff| = 0, identisk F-nivå-fördelning). Det är vad "vi
äger metoden" betyder i bevistermer — inte ett liknande svar, utan *samma* svar.

### Buggar funna och fixade under replikeringen

Replikeringen avslöjade konkreta defekter i den ärvda koden (dokumenterade i
`LESSONS_BCG.md`): relativa sökvägsfel, ett kolumnnamns-fel (`No of Sites` vs
`No_of_Sites`), saknade härledda kolumner, en CSV/XLSX-formatmiss, och en mojibake-
encodingbugg i Modul 2. DuckDB-SQL-pipelinen ersatte Alteryx för Modul 1, 2, 3 och 6;
Modul 4 kräver fortfarande Alteryx. BCG:s kod bar även UK-legacy-rester och döda
config-nycklar (LB.51) — verifierade före varje körning istället för att antas körklara.

### En nyans värd att dokumentera (teckenflips)

Några fingranulära grupper hade *motsatt tecken* mot BCG (t.ex. en site som visade +0,87
där facit hade −2,29). Det är inte replikeringsfel — det är svag-signal-OLS nära
brusgränsen, där tunn data gör koefficienten instabil och en marginell indataskillnad
vänder tecknet. De är få, de uppträder bara på de finaste nivåerna, och fallback-väven
rensar bort dem före varje beslut (IB.10). De *motiverar* väven snarare än underminerar
replikeringen.

---

## 4. Köra på färsk data (FAS F)

Med replikeringen bevisad parametriserades pipelinen att köra på ett växande fönster
(ankare fast vid 2022-07-01, slutdatum framflyttat) istället för BCG:s hårdkodade
2025-06-fönster. De tre modellfamiljerna kördes på växande data:

- **Cluster** och **Site**-elasticiteter: regenererade på växande data.
- **Bundle**: parkerad på evidens (se §6).

Sedan kördes fallback-väven (Step 6) för första gången på växande data
(`run_step6.py`). Resultat: 108 979 rader / 15 128 produkter, median slutelasticitet
−0,497, **100 % negativa, 100 % inom det rationella (−10, 0)-bandet**. F-nivå-fördelningen:

| Nivå | Andel |
|---|---|
| F6 service within cluster | 74,6 % |
| F3 cluster level | 9,8 % |
| F5 product across clusters | 9,5 % |
| F7 service across clusters | 3,9 % |
| F2 bundle level | 1,8 % |
| F4 bundle across clusters | 0,4 % |
| F1 site level | 0,0 % |

74,6 % av produkterna hämtar sin elasticitet från F6 — de flesta produkter saknar egen
signifikant signal ens på klusternivå, vilket är precis varför väven finns (bekräftar IB.1
/ IB.9).

---

## 5. Validera den färska outputen (utan facit)

På färsk data finns inget BCG-facit att matcha mot, så korrekthet bedöms tre vägar
(`verify_tool\output_rationality\` och `verify_tool\provenance\`):

1. **Fristående rimlighet** — är varje färsk elasticitet trovärdig? 100 % negativa, 100 % i
   band. Ja.
2. **Drift mot 2025-baslinjen** — 95 % av produkterna driftar under 0,5; omsättningsvägd
   elasticitet rörde sig −0,532 → −0,512 (netto +0,020, försumbart). Modellen är *stabil*
   över tio månader — egenskapen en prismodell behöver.
3. **Härkomst (provenance)** — exakt vilka inputs som är färska vs frusna, gjort explicit så
   ingen övertolkar resultatet. Rapporteras som REVIEW avsiktligt (de tre frusna låsen),
   inte som ett fel.

### Vad de tio extra månaderna ändrade (dekomponering)

Driften dekomponerades per service, kluster och omsättningsvikt
(`analysis\analys_bcg_freshness.py`). Fyndet, data-bestämt: kärnsortimentets priskänslighet
stod stilla. De fem största omsättningstjänsterna (Consult, Imaging, Surgery, Internal,
Hospitalisation — tillsammans >4,7 mdr) är i princip platta. Rörelsen som finns är antingen
**brusnormalisering** i små svag-signal-artiklar (Healthcare: +0,97 rå drift men bara 34
Mkr, där 2025-extremvärden stabiliserades mot rimliga nivåer — IB.10) eller **lågvolym
riktade skiften** (Accessories mer priskänsliga, Consumables mindre). Ingen stor tjänst
bytte riktning. Att färsk data *tämjer* extremvärden snarare än skapar nya är i sig ett
tecken på en välartad modell.

Detta fångas för top management i `presentations\elasticity_since_bcg.pdf` (BCG:s −0,532 vs
dagens −0,512, med hela evidensbasen) och som dataunderlag i
`output_analyspaket\Analyspaket_BCG_Freshness_<datum>.xlsx`.

---

## 6. Centrala beslut längs vägen

- **Bundle parkerat på evidens (FD.11).** Varukorgs-transaktioner var 23,9 % av
  omsättningen, men bundle-grenen vinner bara **2,2 %** av besluten i väven — eftersom
  Cluster/Site-nivåerna räddar elasticiteten innan väven når bundle för 97,8 % av
  produkterna (INSIGHTS IB.12: väv-vinst ≠ volym-materialitet). Att färdigställa
  bundle-modellen (UK-legacy-broar, FTE-bro, VM-körning) skulle påverka 2,2 % av utfallen —
  oproportionerlig kostnad. Återbesöks-trigger: om rimlighetsgrinden visar sjukhustjänster
  ofta insignifikanta/sourceless i väven.
- **Tre frusna lås accepterade medvetet (LF.9).** Väv-vikter, steg-5-routning och
  bundle-grenen står kvar på 2025-värden för att leverera en färsk läsning nu istället för
  att blockera på tre uppströms-byggen vars sammanlagda beslutspåverkan är liten.
  Dokumenterat, synliggjort av provenance-kontrollen, med en definierad uppdaterings-
  roadmap (FD.15 → FD.14 → FD.11).

---

## 7. Evidensen på ett ställe

- **Replikeringsbevis:** `verify_tool\proof_chain\` (FR-1..7, README dokumenterar kedjan).
- **Extraktionsvalidering:** `verify_tool\extraction_validation\` (DW vs facit).
- **Output-rimlighet:** `verify_tool\output_rationality\` (färsk-output-rimlighet).
- **Härkomst & freshness:** `verify_tool\provenance\` (färskt vs fruset, stabilitet).
- **Kvitton:** `verify_tool\receipts\<datum>\` — varje körning skriver ett daterat
  Excel-kvitto; lita på kvittot, inte konsolen (R7).
- **Beslut & antaganden:** `docs/governance/` (PLAYBOOK decision log, LOCKED_ASSUMPTIONS,
  FUTURE_DEVELOPMENT, ROADMAP).
- **Domän- & tekniska lärdomar:** `docs/knowledge/` (INSIGHTS_BCG `IB.*`,
  LESSONS_BCG `LB.*`).

---

*Sammanställt av Jens Palmö. Varje siffra i detta dokument spåras till ett omkörbart skript
och ett daterat kvitto — replikeringen är inte ett påstående, den är en beviskedja.*
