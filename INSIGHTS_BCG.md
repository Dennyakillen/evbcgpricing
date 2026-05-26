# INSIGHTS_BCG — Affärs- och domäninsikter, BCG Pricing

**Projekt:** `evbcgpricing` (BCG:s priselasticitetsflöde — replikering, validering, migrering)
**Lever i:** `C:\Projekt\BCG` (detta repo). Helt skild från Business_Analytics `INSIGHTS.md`.
**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Senast uppdaterad:** 2026-05-26

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
| IB.2 | Fallback är representant-väljare, inte omklustring | Steg 5 ommodellerar inte; det väljer |
| IB.3 | Enda genuina externa input är FTE (Quinyx) | Resten härleds eller är död config |
| IB.4 | Källan var alltid Evidensias egen data | BCG:s gruppering är grövre än DW |
| IB.5 | `SalesTotal` = brutto inkl 25 % moms (≠ `SalesExVAT`) | Modellomsättning = brutto |
| IB.6 | Affärsvärdet sitter i FÄRSK data, inte exakt replikering | Replikering är grund, inte leverans |
| IB.7 | Elasticitet är log-log → koefficienten ÄR elasticiteten | Ingen eftertransform behövs |
| IB.8 | Modellens KEY = Cluster × ItemCode | L4 bär ej kärnelasticiteten |

---

## Insikter

### IB.1 — Icke-signifikans på fin nivå är BCG:s normaltillstånd
BCG:s egen frusna baslinje (`Model_output` i Sweden_Product_Cluster_Elasticity_Dashboard.xlsx) har bara
**227 / 1276 (17,8 %) rått signifikanta** (p<0,05) på fin Cluster×ItemCode-nivå. Våra OVR0001-elasticiteter
(−0,09…−0,19, icke-signifikanta) **matchar BCG:s** (−0,12 / −0,15, p=0,055 / 0,18). Det vi länge tolkade
som svaga elasticiteter var trogen replikering — BCG får samma svaga tal på samma koder.
**Konsekvens:** Bedöm aldrig egna elasticiteter mot en absolut "borde vara signifikant"-norm. Mät mot
BCG:s output på samma kod. *(Teknisk motsvarighet: LB.5.)*

### IB.2 — Fallback är representant-väljare, inte omklustring
Steg 5 (`blended_logic`) gör **ingen ny regression** på grövre nivå. Per `(Service, big_cluster)`:
sortera `[Significant? DESC, TotalNet DESC]`, behåll första raden som representant, merge tillbaka på alla
fina rader. En svag fin grupp **ärver** den starkaste revenue-grannens representant. Flaggan
`Significant ?` = `RSQ ≥ 0.5 AND PVALUE ≤ 0.2` (inte p<0,05, inte "sig ELLER räddad"). Rescue (227 → 618)
sker i blenden FÖRE flaggan räknas. Fyra fallback-nivåer: `New_cluster ∈ {Clinics, Clinics_CH,
Hospital_CH, Hospital}`; grövsta `big_cluster ∈ {Clinics, Hospital}`.
**Konsekvens:** 618 / 1276 (48,4 %) blir `Significant ?=1` genom representant-arv, inte genom bättre
modellering. Det är så glesa grupper görs användbara. *(Bevisat bit-för-bit: 43/43 representanter.)*

### IB.3 — Enda genuina externa input är FTE (Quinyx)
Det som såg ut som "externa källor" är mestadels internt: PR/media-datum = `SPECIAL_WEEKS`-konstanter;
helger = Python `holidays.Sweden()`; säsong/kvartal = härlett i pipelinen; extern prisdata + competitor +
`InScope Mapping.xlsx` = **död config** (deklarerad men aldrig läst av koden). Den **enda** genuina
uppströms-inputen är `Sum_FTE_Interpolated` (bemanning, från Quinyx), en kontrollvariabel i `cols_needed`.
**Konsekvens:** Färsk-data-arbetet behöver bara lösa FTE uppströms — inte rekonstruera ett knippe externa
flöden. FTE Väg 2 = aggregera validerad DW-vy (`Manual.Fact_Quinyx_DayClinic`), inte replikera BCG:s
Quinyx-rådata-pipeline.

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
bit-för-bit, steg 5-facit) är *grundläggning* — de bevisar att vi äger logiken, men de är inte produkten.
Produkten är den färska körningen, med diffar små nog att inte flippa ett top-line-prisbeslut.
**Konsekvens:** Precisionskravet styrs av affärsmålet, inte av att matcha BCG till sista decimalen på
gammal data. Output-rimlighetsgrinden (ersätter facit när facit försvinner) hör till **färsk-data-fasen**,
inte replikeringsfasen — den byggs när det finns en färdig baslinje att kalibrera mot.

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

---

## Hur listan växer

Ny insikt läggs till när vi lär oss något **substantiellt om modellen eller datan** som påverkar
tolkning eller mål — inte när vi löser ett tekniskt problem (det → `LESSONS_BCG.md`). Vid sessionsstart:
läs hela listan. Vid sessionsslut: överväg om sessionen gav ny insikt som förtjänar ett `IB.N`.

---

*Skapad 2026-05-26 vid dokumentstruktur-omtaget. Extraherad ur SESSION_2026-05-25, NEXT_SESSION.md (PoC-2),
TECHNICAL_PREREQUISITES.md §8. Inga nya insikter uppfunna — befintliga strukturerade och numrerade.*
