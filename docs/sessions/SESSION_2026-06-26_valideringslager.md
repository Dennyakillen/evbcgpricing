# Session 2026-06-26 — Valideringslager runt BCG-motorn (Phase Z)

> **Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
> **Författare (verktyg + dokumentation):** Claude advisor
> **Status:** Levererat och kört. Alla verktyg gröna eller medvetet märkta. BCG-kärnan orörd.
> **Plats i repo:** verktyg i `verify_tool/`, denna dokumentation i `verify_tool/` eller `docs/`.

---

## Vad sessionen handlade om

Att bygga, testa och cementera ett **additivt valideringslager** runt den orörda BCG-motorn
— "fogmassan och limmet" som håller ihop en redan radvaliderad metodik. Målet var inte att
ändra modellen (den är validerad bit-för-bit mot frozen facit) utan att kunna *bevisa och
visualisera* att hela röret — DW → data prep → Blob → tre familjer → EFTER → drickbart vatten
— håller på ny färsk data utan att något tvärs familjer tappas tyst, och att de avsiktliga
"ventilerna" (filter, trösklar) syns och kan mätas.

**Bärande disciplin genom hela arbetet:** additivt only (BCG-koden rörs aldrig), mät-gissa-inte
(kalibrera mot mätning före påstående), källa före hypotes (läs koden först).

---

## Vad som byggdes (åtta artefakter)

| Fil | Plats | Vad den gör | Status |
|---|---|---|---|
| `pipeline_contracts.py` | verify_tool/ | Boundary-kontrakt för Step 6:s 6 inputs: form, volym, invariant. Blockerar vid brott. | Kalibrerad mot faktiska kolumner, grön |
| `prefilter_unpriced.py` | verify_tool/ | Tar bort icke-prissatta poster (null ItemCode på "Internal") explicit före väven; flaggar misstänkt null på prissatt produkt. | Byggd, additiv lagning |
| `window_coherence.py` | verify_tool/ | Tvärs-familje-grind: alla MOTOR-familjer klara + färska mot samma fönster före EFTER. Offline default, --via-blob striktare (AZ.7-tolerant). | Grön (GO), --via-blob oprövad mot live token |
| `dry_run_full_pipeline.py` | verify_tool/ | Strukturell dry-run tvärs hela röret: sökvägar, fönster-konsistens, runner-dry-runs, VM/Blob. | 24 OK / 0 FAIL |
| `run_smoke_facit.py` | verify_tool/ | End-to-end rök-test mot frozen facit, helt offline. Profilerar utfall mot blessad referens. | Referens blessad: 108 979 rader, 15 128 keys, median −0.4968 |
| `conservation.py` | verify_tool/ | Bevarande tvärs skarvar: skarv 1 (parquet-tillväxt) full, skarv 2-3 ramverk. | Skarv 1 har schema-bugg (ID_Item, se nedan), skarv 3 mäter |
| `valve_map.py` | verify_tool/ | Ventilkarta: var ventilerna sitter, hur mycket de släpper, vad som rann ut. Genererar visuell rörkarta + Excel. | V1/V3 EXAKT, V2/V4 APPROX (kalibreras) |
| `PROMPT_hitta_validera_cementera.md` | docs/ | Återanvändbar projektoberoende prompt för hitta→validera→cementera. | Klar |

Plus stödfiler: `frozen_facit_reference.json` (smoke-baslinje), `conservation_snapshot.json`,
`probe_null_itemcode.py` (engångssond, kan arkiveras), `README_VALIDERING.md` (förvaltningskarta),
`ARKITEKTUR_MOGNADSANALYS.md` (den ursprungliga arkitekturanalysen).

---

## Vad mätningarna avslöjade om modellen (verkliga fynd)

**Step 6-väven har fyra avsiktliga ventiler, nu uppmätta:**

- **V1 (Fee-filter):** släpper 5 rader av 108 984, alla Fee. Precis som avsett.
- **V3 (signifikansporten) — huvudventilen:** släpper **77.4%** av cluster-modellerna
  (3 236 av 4 180). Nedbrutet: 2 166 på PVALUE>0.20, 1 428 på RSQ<0.5, 1 100 på fel tecken,
  10 på orimlig elasticitet (summan > avlättat = överlappande skäl, korrekt). Detta är modellens
  signifikansprofil synliggjord: ~77% av cluster-modellerna är inte statistiskt säkra nog att
  bidra till fallback. *Värt att bekräfta att detta är skilt från den historiska 73% silent
  drop — denna 77% är AVSIKTLIG filtrering, inte oavsiktlig datatapp.*
- **V2, V4:** approximationer, ej trovärdiga än (se öppna trådar).

**Step 6-input `df_all_product` (FD.14) bär 20 null-ItemCode:** alla "Na (Natrium) Catalyst" /
"Internal", 130 109 kr omsättning, replikerade över ~20 kliniker. Icke-prissatt labbreagens-
kostnad som ska falla ur väven — men idag faller den ur TYST via en inner join (rad ~252).
Rätt utfall, ömtålig mekanism. Hanteras nu explicit via prefilter_unpriced.

---

## Öppna trådar (ärligt — inte allt är klart)

1. **conservation.py skarv 1 har en schema-bugg:** den frågar parqueten efter kolumn `ItemCode`,
   men parquetens RÅDATA använder DW-namn (`ID_Item`, `ID_Customer`, `ID_Patient`). Frågan
   måste ändras till `ID_Item`. (valve_map har redan rätt hantering.) *Detta är i sig ett bevis
   på schema-drift-klassen: samma entitet, olika namn på olika ställen i röret.*
2. **valve_map V2 + V4 är approximationer:** V2 (in=682 oförklarligt lågt), V4 (99.6% extremt).
   Kalibreringsblock med exakta print-satser finns i valve_map.py-huvudet — klistra in i
   Fall_Back_Logic.py temporärt vid nästa körning, jämför, uppgradera till EXAKT.
   *Öppen fråga till Jens: har site-modellen verkligen så få produkter med 10+ signifikanta
   sites, eller är V4-approximationen fel?*
3. **window_coherence --via-blob oprövad mot live token:** rättad blint efter token-krasch
   2026-06-26. Verifiera mjuk degradering nästa gång token är färsk.
4. **conservation skarv 2 ej byggd:** kräver replicate_dataprep.py + en familje-CSV.
5. **valve_map skarv 1-3-ventiler ej mätta:** P1/P2 (dataprep), M1 (modellsteg) — kräver
   respektive källa uppladdad. Listade i VALVE_REGISTRY som EJ.
6. **Smoke-test-toleranser (TOL) är initiala gissningar:** kalibrera mot facit-determinism.

---

## Integrationssteg som återstår (additiva, ej gjorda)

Dessa kopplar in verktygen i den löpande pipelinen — gör dem när du är redo:

- **run_step6.preflight** bör anropa, i ordning: `prefilter_unpriced.prefilter_weave_weights()`
  → placera → `pipeline_contracts.validate_all()`. Tre rader, blockerar vid brott.
- **run_after.preflight** bör anropa `window_coherence.check_coherence()` → STOP vid NO-GO.
- **Före varje varm körning:** `dry_run_full_pipeline.py` + `run_smoke_facit.py`.

---

*Sessionen byggde lim, testade det mot frozen facit, och cementerade fynden. BCG-kärnan orörd.*
