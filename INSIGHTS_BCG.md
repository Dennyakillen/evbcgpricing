# INSIGHTS_BCG — Affärs- och domäninsikter, BCG Pricing

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde — replikering, validering, migrering)
**Lever i:** `C:\Projekt\BCG` (detta repo). Helt skild från Business_Analytics `INSIGHTS.md`.
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Senast uppdaterad:** 2026-05-29

---

## Vad detta dokument är (och inte är)

`INSIGHTS_BCG.md` håller **vad vi lärt oss om BCG:s modell och Evidensias data** — substansinsikter som
styr hur resultaten ska tolkas och vad som är affärsmässigt rätt mål. Varje insikt har ett stabilt
`IB.N`-ID.

**Detta är inte:**
- **Tekniska lärdomar** (hur vi körde pipelinen, plattformsfällor) → `LESSONS_BCG.md` (`LB.N`).
- **Beslut** (vad vi valde och varför) → playbookens decision log (`D*`, `D-B*`).

En insikt här svarar på *"vad är sant om modellen/datan, och vad betyder det för affären?"* — inte
*"hur fick vi koden att köra?"*.

---

## Snabbindex

| ID | Insikt | Bärande konsekvens |
|---|---|---|
| IB.1 | Icke-signifikans på fin nivå är BCG:s normaltillstånd (18 % rått sig.) | Tolka inte svaga tal som fel |
| IB.2 | Fallback är representant-väljare, inte omklustring | Steg 5/6 ommodellerar inte; det väljer |
| IB.3 | Enda genuina externa input är FTE (Quinyx) | Resten härleds eller är död config |
| IB.4 | Källan var alltid Evidensias egen data | BCG:s gruppering är grövre än DW |
| IB.5 | `SalesTotal` = brutto inkl 25 % moms (≠ `SalesExVAT`) | Modellomsättning = brutto |
| IB.6 | Affärsvärdet sitter i FÄRSK data, inte exakt replikering | Replikering är grund, inte leverans |
| IB.7 | Elasticitet är log-log → koefficienten ÄR elasticiteten | Ingen eftertransform behövs |
| IB.8 | Modellens KEY = Cluster × ItemCode | L4 bär ej kärnelasticiteten |
| IB.9 | Grövre granularitet → starkare, renare elasticitet | Bundle > Cluster > Site i signaltäthet |
| IB.10 | Signifikanta tecken-flip-grupper på fin nivå är svag-signal-OLS | Inte replikeringsfel; stärker IB.9 |
| **IB.11** | **Snapshot-drift = 0.057% på fryst fönster (DW idag vs BCG 2025-07)** | **Användbart baseline-band för framtida valideringar** |

---

## Insikter

### IB.1 — Icke-signifikans på fin nivå är BCG:s normaltillstånd
BCG:s egen frusna baslinje (`Model_output` i Sweden_Product_Cluster_Elasticity_Dashboard.xlsx) har bara
**227 / 1276 (17,8 %) rått signifikanta** (p<0,05) på fin Cluster×ItemCode-nivå. Våra OVR0001-elasticiteter
(−0,09…−0,19, icke-signifikanta) **matchar BCG:s** (−0,12 / −0,15, p=0,055 / 0,18). Det vi länge tolkade
som svaga elasticiteter var trogen replikering — BCG får samma svaga tal på samma koder.
**Konsekvens:** Bedöm aldrig egna elasticiteter mot en absolut "borde vara signifikant"-norm. Mät mot
BCG:s output på samma kod. *(Teknisk motsvarighet: LB.5. Bekräftat på full Cluster-körning: 18,0 % rått
signifikant — praktiskt taget identiskt med BCG:s 17,8 %.)*

### IB.2 — Fallback är representant-väljare, inte omklustring
Fallback gör **ingen ny regression** på grövre nivå — den **väljer** bland redan beräknade elasticiteter.

**Steg 5 (cluster-blend, `blended_logic`):** Per `(Service, big_cluster)`: sortera
`[Significant? DESC, TotalNet DESC]`, behåll första raden som representant, merge tillbaka på alla fina
rader. En svag fin grupp **ärver** den starkaste revenue-grannens representant. Fyra fallback-nivåer:
`New_cluster ∈ {Clinics, Clinics_CH, Hospital_CH, Hospital}`; grövsta `big_cluster ∈ {Clinics, Hospital}`.
Rescue (227 → 618) sker i blenden FÖRE flaggan räknas. Resultat: 618 / 1276 (48,4 %) blir signifikanta
genom representant-arv, inte genom bättre modellering — så glesa grupper görs användbara. *(Bevisat
bit-för-bit: 43/43 representanter.)*

**Steg 6 (F1–F7-väv, `Fall_Back_Logic.py`):** Samma princip på sju nivåer. Per `ProductKey` väljs
`final_elasticity` via `combine_first`-prioritet (första tillgängliga vinner): F1 site → F2 bundle →
F3 cluster → F4 bundle-across → F5 product-across → F6 service-within → F7 service-across. *(Bevisat
bit-för-bit 2026-05-27 mot BCG-facit: korr 1,000000, |diff|=0, F1–F7-fördelning identisk, 100 %
nivåmatch. FR-7 stängd.)*

**Signifikansflaggan (`significant_<level>`, def i `df_cleanup`):**
```
significant = (round(RSQ,2) >= 0.5)
            & (round(PVALUE_PRICE,2) <= 0.20)
            & (ELASTICITY_PRICE < 0)
            & (ELASTICITY_PRICE > -10)
```
Alltså fyra villkor, inte två. Utöver RSQ ≥ 0,5 och p ≤ 0,20 måste elasticiteten vara **negativ och inte
mer extrem än −10** (en "signifikant" positiv eller <−10-elasticitet är brus, inte en priseffekt).
Det är **inte** p<0,05 och inte "sig ELLER räddad". *(Korrigerat 2026-05-27: tidigare dokumenterades
flaggan som enbart RSQ/PVALUE — det var halvsant. Relevant för färsk data: nya extremvärden utanför
(−10, 0) faller automatiskt ur signifikans.)*

**Konsekvens:** Fallback (steg 5 och 6) ommodellerar aldrig — den väljer representant/nivå. Det är
mekanismen som gör glesa grupper användbara.

### IB.3 — Enda genuina externa input är FTE (Quinyx)
Det som såg ut som "externa källor" är mestadels internt: PR/media-datum = `SPECIAL_WEEKS`-konstanter;
helger = Python `holidays.Sweden()`; säsong/kvartal = härlett i pipelinen; extern prisdata + competitor +
`InScope Mapping.xlsx` = **död config** (deklarerad men aldrig läst av koden). Den **enda** genuina
uppströms-inputen är `Sum_FTE_Interpolated` (bemanning, från Quinyx), en kontrollvariabel i `cols_needed`.
**Konsekvens:** Färsk-data-arbetet behöver bara lösa FTE uppströms — inte rekonstruera ett knippe externa
flöden. FTE Väg 2 = aggregera validerad DW-vy (`Manual.Fact_Quinyx_DayClinic`), inte replikera BCG:s
Quinyx-rådata-pipeline. *(Bekräftat: launchern föll aldrig på saknad InScope/competitor-data trots att
config refererar dem — död config, som väntat.)*

### IB.4 — Källan var alltid Evidensias egen data
BCG:s `transaction_data` kom från `dbo.Fact_BillingInvoiceRows` JOIN `dbo.Dim_Item` — data **vi** matade
dem från vårt DW. BCG:s artikelgruppering (`Dim_Item`-snapshot) är deras tolkning och är **grövre** än vår
interna DW-hierarki.
**Konsekvens:** Trogen replikering på gammal data bevisar att vi behärskar metoden, men ger inga nya
insikter (konsulterna har redan levererat dem). Det enda som måste hålla per kod är samma omsättning och
volym — inte att koderna grupperas likadant. Grövre eller finare DW-native gruppering är vårt val.

### IB.5 — `SalesTotal` = brutto inkl 25 % moms
Bekräftat med data (median-kvot 1,0000): `SalesTotal` = `SalesExVAT × 1,25`. Modellens omsättning
(`TotalNet` / `DOLLAR`) = `SalesTotal` (**brutto**); `TotalNetXVat` = `SalesExVAT` (netto). Vidare:
`NoofUnits ≠ SoldQuantity` — separata kolumner (~16× isär); modellens volym = `SoldQuantity`.
**Konsekvens:** Net/brutto-frågan (tidigare öppen, G1) är stängd. Tidiga gissningar om detta var fel —
data avgjorde, inte kolumnnamn. *(Princip: "mät, gissa inte", KÄRNPRINCIPER.)*

### IB.6 — Affärsvärdet sitter i FÄRSK data, inte exakt replikering
Beslutsfattaren vill ha **samma modell körd på refreshad data**. Alla valideringar (golden reference,
bit-för-bit, steg 5/6-facit) är *grundläggning* — de bevisar att vi äger logiken, men de är inte produkten.
Produkten är den färska körningen, med diffar små nog att inte flippa ett top-line-prisbeslut.
**Konsekvens:** Precisionskravet styrs av affärsmålet, inte av att matcha BCG till sista decimalen på
gammal data. Output-rimlighetsgrinden (ersätter facit när facit försvinner) hör till **färsk-data-fasen**
(ROADMAP FAS F), inte replikeringsfasen — den byggs när det finns en färdig baslinje att kalibrera mot.
*(2026-05-27: hela replikeringen FR-1..7 är komplett — alla familjer + F1–F7-väven körda och bit-för-bit
validerade på gammal data inom det hårdkodade datumfönstret. 2026-05-28: G7-datumparametrisering klar
på branch `fas-f-fresh-data`. 2026-05-29: Spår B operationaliserad — DW-extraktion validerad mot facit,
växande-fönster-CSV på plats. Återstår: datafullständighets-grind, pipelinekörning på färsk data, output-
rimlighetsvalidering.)*

### IB.7 — Elasticitet är log-log → koefficienten ÄR elasticiteten
Både `QuantitySold(SalesTotal>0)` och `Regular_Price_fwbw_max_6` har `Transform=1` (log) i BCG:s
`transform_control_TT.csv`. I en log-log-OLS är priskoefficienten elasticiteten direkt
(`ELASTICITY_Regular_Price_fwbw_max_6`).
**Konsekvens:** Ingen eftertransform behövs för att läsa ut elasticiteten. (Tidigare "viktigaste
oklarheten" — stängd.)

### IB.8 — Modellens KEY = Cluster × ItemCode
`KEY = Cluster_Granularity + '-' + ItemCode`. `ProductGroupL4Name` (Service) påverkar **inte**
kärnelasticiteten — den bärs för YOY-säsong och output/blend-gruppering. I vår DW är L4
(`Master_Underkategori3`) halv-NULL, vilket inte biter på kärnelasticiteten men är relevant för
gruppering vid DW-native skalning.
**Konsekvens:** Kärnmodellen står på Cluster×ItemCode. L4-luckan är ett grupperings-/outputproblem, inte
ett elasticitetsproblem.

### IB.9 — Grövre granularitet → starkare och renare elasticitet
De tre modellfamiljernas fulla körning visar ett konsekvent, tolkningsbart mönster: ju grövre modellnivå,
desto starkare negativ median, högre andel negativa, och färre absurda svansvärden.

| Familj | Grupper | Median elasticitet | Neg-andel | p<0,05 | Svansband (min/max) |
|---|---:|---:|---:|---:|---|
| Cluster (produkt×kluster) | 3812 | −0,138 | 76,5 % | 18,0 % | −820 / +64 |
| Site (produkt×site) | 4673 | −0,054 | 62,4 % | 9,3 % | −232 / +1204 |
| Bundle (varukorgar/klinik) | 125 | −0,211 | 85,6 % | 22,4 % | −1,33 / +1,21 |

**Varför:** Grövre nivå = fler observationer per grupp = mindre brus = starkare signal och färre
instabila koefficienter. Site (finast) har tunnast data per grupp → svagast median, lägst rå signifikans,
störst svansvärden (prisstabila grupper, LB.9). Bundle (grövst, varukorgar med naturlig prisvariation)
har renast band — inga extremer alls.
**Konsekvens:** (1) Bedöm varje familjs elasticiteter mot dess egen granularitetsnivå, inte mot varandra
— Site:s svagare tal är väntade, inte sämre. (2) Site:s låga rå signifikans (9,3 %) är just varför
fallback (steg 6, F1–F7) finns: glesa site-grupper ärver representanter från grövre nivåer. (3) Detta
stärker IB.1 — låg fin-nivå-signifikans är normaltillstånd, och det förvärras med finare granularitet.
Steg 6:s multi-nivå-blend är designad för precis detta.

### IB.10 — Signifikanta tecken-flip-grupper på fin nivå är svag-signal-OLS, inte replikeringsfel
Vid verifieringen av Site och Bundle fanns några "signifikanta" grupper där vår elasticitet och BCG:s har
**motsatt tecken** — t.ex. Site `8103-LPROSEN002` (vår +0,87 vs facit −2,29) och Bundle
`Hospital-CDF114,EEX113,NIH` (vår +1,21 vs facit −0,88). Vid första anblick oroande.
**Varför det inte är fel:** Dessa är svag-signal-OLS nära brusgränsen — grupper med tunn data där
regressionen är instabil och en marginell skillnad i indata vänder tecknet. De passerar signifikansgrindens
RSQ/p-trösklar men ligger på gränsen där koefficienten är illa bestämd. De är **få**, och de **rensas bort
av fallbacken** (steg 6, F1–F7) innan något prisbeslut — exakt det fallbacken finns för (IB.2).
Cluster (grövre, mer data per grupp) har inga sådana flips; de uppträder bara på de finaste nivåerna.
**Konsekvens:** (1) Bedöm replikeringstrohet på rank-korrelation + beslutsrelevanta (signifikanta efter
full grind) grupper, inte på varje enskild fin-nivå-grupp. (2) Tecken-flips på finaste nivån stärker IB.9:
finare granularitet = svagare signal = fler instabila koefficienter. (3) De motiverar fallbackens
existens snarare än att underminera replikeringen. *(Sett vid FAS V-verifieringen 2026-05-28; Site
rank-korr 0,91, Bundle 0,93, beslutsrelevanta 78,5 % resp. 81,4 % identiska.)*

### IB.11 — Snapshot-drift mellan BCG:s extrakt och DW idag är ~0.057% (revenue, fryst fönster)
**Observation (2026-05-29):** Att köra `export_b4b_for_model.py` med BCG:s ursprungliga fönster
(2022-07..2025-06) mot dagens DW och jämföra mot BCG:s frusna facit (`0828_..._P_C.csv` i OneDrive)
ger följande diffar:

| Mått | Facit (BCG) | Ours (DW idag) | Diff |
|---|---:|---:|---:|
| Rader | 485,248 | 484,827 | -0.09% |
| Sum TotalNet (brutto) | 6,505,893,292 | 6,502,199,267 | **-0.057%** |
| Sum SoldQuantity | 6,439,977 | 6,482,891 | +0.67% |
| Distinct ItemCode | 1,151 | 1,151 | 0 |
| Distinct KEY | 4,949 | 4,930 | -19 (-0.4%) |

**Per-kluster (gross TotalNet):**
- 6 av 7 kluster inom ±0.5% (Clinics 0..1, Sjukhus A/B/C/Södran)
- Clinics 2: +1.19% (största positiva drift)
- Sjukhus Södran: -1.41% (största negativa drift)

**Tolkning:** DW har levt vidare sedan BCG:s 2025-07-extrakt — krediteringar, sena fakturor, mix-skifte,
klinik-omklassningar, restituerade transaktioner. Inte fel. Volym uppåt + revenue neråt = priser har gått
ner marginellt (eller kreditmix har ändrats).

**Konsekvens:** (1) Användbart **baseline-band**: 0.057% är ett rimligt snapshot-drift att förvänta sig
framåt vid liknande tidsavstånd från en extrakt. (2) På klusternivå kan enskilda kluster drifta upp till
~1.5% i båda riktningarna — om en framtida körning visar drift utöver detta band utan extra månader, är
det signal på något annat (klinik öppnat/stängt, datakvalitetsproblem). (3) Detta är *grund*-driften
för rimlighetsgrindens design (IB.6) — output-rimlighet ska inte trigga larm på drifter inom detta band.

---

## Hur listan växer

Ny insikt läggs till när vi lär oss något **substantiellt om modellen eller datan** som påverkar
tolkning eller mål — inte när vi löser ett tekniskt problem (det → `LESSONS_BCG.md`). En befintlig insikt
**korrigeras på plats** (med kort spårparentes) när källan visar att den var halvsann — vi lägger inte en
motsägande dubblett bredvid. Vid sessionsstart: läs hela listan. Vid sessionsslut: överväg om sessionen
gav ny insikt som förtjänar ett `IB.N`.

---

*Skapad 2026-05-26 vid dokumentstruktur-omtaget; extraherad ur SESSION_2026-05-25, NEXT_SESSION.md (PoC-2),
TECHNICAL_PREREQUISITES.md §8. IB.9 tillagd efter att alla tre modellfamiljer körts fullt på VM. Omstrukturerad
2026-05-27: IB.2-korrigeringen (tredje/fjärde signifikansvillkoret) invävd i IB.2 i stället för dubblerad;
FR-7-stängning reflekterad i IB.2/IB.6. IB.11 tillagd 2026-05-29 efter att Spår B operationaliserats och
snapshot-drift mätts mot facit.*
