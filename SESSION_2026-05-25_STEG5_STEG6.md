# SESSION 2026-05-25 — Steg 5 facit-validerat, steg 6 kartlagt

> Komplett sessionsdokumentation. Skriven av Jens Palmö (utvecklare) med AI-rådgivaren.
> Dra in i `evbcgpricing`-repot. Föregående handoff: `NEXT_SESSION.md` (PoC-2-milstolpen).

---

## TL;DR — vad som hände

1. **Steg 5 (`blended_logic` / fallback) bevisat bit-för-bit mot BCG:s facit.** `fallback_blend.py`
   kördes på BCG:s egen fulla `output_summary.xlsx` (3812 KEY) → **43/43 representanter identiska**
   med `final_model_cluster_granularity.xlsx`, `Significant?`-flagga 43/43, `618/1276` post-blend.
2. **Steg 6 (`Fall_Back_Logic.py`, F1–F7) kartlagt — kontraktet känt, ingen ny blockerande logik.**
3. **Site (folder 3) bekräftad strukturellt identisk med Cluster** — samma pipeline, ingen ombyggnad.
4. **Kritiska vägen omklassad:** nästa milstolpe är en **VM-körning** (Cluster full + Site + Bundle),
   inte mer kodläsning. Steg 6 är blockerat av att dess input (tre `output_summary.xlsx`) inte finns.

---

## 1. STEG 5 — FALLBACK FACIT-VALIDERAD (bit-för-bit)

### Vad det är
`fallback_blend.py` = fristående, verbatim-trogen replikering av `model_output` + `blended_logic`
ur BCG:s `data_prep_after_model_output.py`. Fristående = bär konstanterna explicit (lyfta ur
`constants.py`), kör utan pipelinens import-väv. `xlwings` i BCG:s original är bara utskriftspennan
(`write_df_preserve_named_range`), inte logiken — därför behövs inget Excel för att replikera regeln.

### Beviset
Kört på BCG:s EGEN input (`...\2. Product Cluster Level Models\output\model\output_summary.xlsx`):
```
representatives = 43        (facit: 43)
both = 43  only_facit = 0  only_ours = 0
Significant? agreement = 43/43
representative-set match: PASS
post-blend Significant?=1 = 618/1276   (= exakt NEXT_SESSION:s dokumenterade 618)
New_cluster ∈ {Clinics, Clinics_CH, Hospital, Hospital_CH}  (alla fyra, inga omappade)
```

### Vad steg 5 FAKTISKT gör (korrigerar NEXT_SESSION på två punkter)
- **Fallback = REPRESENTANT-VÄLJARE, inte omklustring.** Ingen ny regression på grövre nivå. Per
  `(Service, big_cluster)`: sortera `[Significant? DESC, TotalNet DESC]`, behåll första, merge:a
  tillbaka på alla fina rader. Svag fin grupp ÄRVER starkaste revenue-grannens representant.
- **`Significant ?` = `RSQ>=0.5 AND PVALUE<=0.2`** (NOT p<0.05, NOT "sig ELLER räddad"). Rescue
  (227→618) sker i blenden FÖRE flaggan räknas — flaggan läses på den BLENDADE ramen.

### Kontraktet (bekräftat ur model.py + constants.py)
- **Fil steg 5 äter:** `output_summary.xlsx` (= `model.py` `output_summary_path`). INTE
  `model_summary.xlsx` (det = multi-sheet-råmaterial från `save_model_summary`, sheet0–4).
- **KEY bär Cluster + ItemCode** (ingen separat kolumn) → `model_output` splittar via regex +
  patchar `'Clinics-nan-0'→'Clinics-NA-0'`, joinar Service från `prod_df` (rank_calc).
- **`SERVICE_OUTPUT_NAME="Service"`** — blenden grupperar på `Service`; vår export döper kolumnen
  `ProductGroupL4Name`. `fallback_blend.py` aliasar/joinar in den (FLAG S, högljutt).
- **`cluster_h_map` komplett** inkl. `Sjukhus A/B/C/Södran → Hospital`.

### Öppna flaggor steg 5
- **FLAG R — `rank_calc`-källa oklar.** BCG:s rank_calc vill ha `Sum_SalesTotal` +
  `ItemDescription English` (Alteryx-matad). `Complete_Product_Data.xlsx` har `SalesTotal` +
  `ItemDescription`. Funkar för Service-join (det enda blenden BEHÖVER); `Rank` är best-effort.
  Pinna exakt rank_calc-källa OM dashboardens Rank behövs nedströms. Logiken opåverkad.
- **Validerat mot BCG:s output, inte vår DW-körning.** LOGIKEN är trogen. Att köra på VÅR fulla
  Cluster-output kräver full VM-körning först.

---

## 2. STEG 6 — `Fall_Back_Logic.py` KARTLAGT (F1–F7 multi-model-blend)

### Arkitektur (ur `__main__`, rad 623–708)
Steg 6 väver ihop FYRA källor till sju elasticitetsnivåer (F1–F7), och `np.select` väljer finaste
tillgängliga signifikanta nivå per rad (fallback-hierarki):

| Källa | Fil | Roll |
|---|---|---|
| Vår steg 5-output | `blended_output_path` (`final_model_cluster_granularity`) | F3/F5–F7 cluster/service-nivåer |
| Blendad cluster | `blended_model_path` (`output_summary_ready.xlsx`) | dfcluster |
| **Site-modell** | `prod_site_level_path` (folder 3 `output_summary.xlsx`) | **F1 site level** |
| **Bundle-modell** | `bundle_cluster_level_path` (folder 5 `output_summary.xlsx`) | **F2/F4 bundle** |

Rad 634 döper om vår steg 5-output: `Service→ProductGroupL4Name`, `New_cluster→Service_Granularity`,
`big_cluster→New_Cluster`. Site har egen signifikansregel (rad 656–661): site signifikant endast om
`SigSites_Sum>=10` per produkt. Bundle "explodes" (rad 664). Allt vävs i `creating_one_df` (rad 676).

F-prioritet (rad 528–531, `elasticity_level_labels`):
F1 site → F2 bundle → F3 cluster → F4 bundle across → F5 product across → F6 service within → F7 service across.

### KÄND insikt: Site/Bundle kräver INGEN ny kod
Site (folder 3) bekräftad strukturellt identisk med Cluster (samma 7 pipeline-filer:
`regular_price → data_prepration → feature_selection → model → data_prep_after_model_output`).
De producerar `output_summary.xlsx` i SAMMA format som Cluster. Steg 6 läser dem via
`column_rename_dict_df_site/_bundle` (bara `ELASTICITY_*→ELASTICITY_PRICE`-omdöpning).
→ **Inget nytt att bygga för Site/Bundle. Kör dem som Cluster, de matar steg 6.**

### Inte läst i detalj (medvetet — A.9)
`creating_one_df` + F1–F7-vävfunktionerna (rad 183–527) lästes EJ i kropp. Skäl: att läsa dem nu
vore att förbereda ett bygge vars input (Site+Bundle `output_summary.xlsx`) inte finns. Läses när
input existerar (efter VM-körning).

---

## 3. KRITISKA VÄGEN HÄRIFRÅN (omklassad)

| # | Steg | Status | Var |
|---|---|---|---|
| 5 (logik) | `blended_logic` replikerad | ✅ **KLAR — facit-validerad** | Lokalt |
| — | **Full Cluster-körning (1311+ grupper)** | 🔴 **NÄSTA** | **VM** (lokalt OOM) |
| — | **Site-modell (folder 3) körning** | 🔴 | **VM** (input 130 MB) |
| — | **Bundle-modell (folder 5) körning** | 🔴 | **VM** |
| 6 | `Fall_Back_Logic.py` F1–F7-blend | 🔴 Blockerad av ovan | Lokalt (läser 3 output_summary) |
| sist | Output-rimlighetsgrind | 🔴 Byggs SIST, mot färdig baslinje | Lokalt |
| sist+1 | Färsk data: parametrisera G7 | 🔴 | — |

**Nästa konkreta steg: VM-körningspass.** Starta `bcg-poc-vm`, kör Cluster full + Site + Bundle,
hämta hem tre `output_summary.xlsx`. FÖRST då har steg 6 sin input. Läs `creating_one_df` i detalj
DÅ, inte före. (Driftkort i README + `UBUNTU_AZURE_VM.md`.)

---

## 4. NYA LÄRDOMAR (lägg i MASTER_PYTHON / KÄRNPRINCIPER)

### A.9 (skärpt, höll nästan på att upprepas 4× denna session) — fråga inte runt källan, LÄS den
**Symptom:** Bad upprepat användaren välja hur Service skulle hanteras / vilken fil blenden äter /
vilket band rimlighetsgrinden ska ha — istället för att läsa `model.py` +
`data_prep_after_model_output.py` som DEFINIERAR svaret. Föreslog även diagnoskommandon som GISSADE
vilken fil som bar elasticiteterna.
**Rotorsak:** Otålighet — ville bygga/fråga före hela kedjan lästs. Varje gissning kostade en runda
(model_summary vs output_summary; service-källa; KEY-format testat på fel fil).
**Regel:** När en fil-/kolumn-/sekvensfråga uppstår OCH källkoden finns — läs källan FÖRST.
`ask_user_input` på designval som koden redan avgjort = förtäckt gissning. Default: begär källfil/
kör läs-script. Användarens "se instruktionerna, kolla facit" var rätt varje gång.

### Validering: kör VÅR kod på KONSULTENS input, matcha KONSULTENS output (billig logik-grind)
**Symptom:** Frestelse att vänta på full VM-körning för att facit-validera steg 5.
**Rotorsak:** Förväxlade "kör på vår data" med "räknar rätt" — två olika frågor.
**Regel:** Logik-trohet bevisas billigast genom att köra repliken på konsultens EGEN input och matcha
deras output bit-för-bit (kräver ingen ny körning). Samma princip som B.1 golden reference. "Kör på
vår data" är en SEPARAT, senare fråga (kräver VM).

### Läs KONSUMENTEN för kontraktet, inte hela producenten
**Symptom:** Frestelse att läsa Site/Bundle-pipelinekoden rad-för-rad.
**Rotorsak:** De är samma beprövade pipeline som Cluster — låg risk för gömd nyhet.
**Regel:** För att veta vad ett uppströmssteg måste LEVERERA, läs nedströmssteget (konsumenten) som
definierar kontraktet. `Fall_Back_Logic.py`:s `__main__` avslöjade att Site/Bundle bara behöver
producera `output_summary.xlsx` i Cluster-format — utan att läsa deras pipeline alls.

### Bygg ALDRIG mot input som inte finns (FTE-fällan, generaliserad)
**Symptom:** Frestelse att läsa/bygga steg 6:s F1–F7-väv innan Site/Bundle körts.
**Rotorsak:** Samma mönster som FTE-pipelinen (byggd på hypotes innan facit lästs).
**Regel:** Ett steg vars input inte existerar ännu är inte "nästa steg" — det är blockerat. Identifiera
blockeraren (här: tre oskörda modeller) och kör DEN först. Detaljläsning av det blockerade steget
väntar tills input finns.

### Windows-konsol-encoding: tvinga stdout UTF-8 i script som dumpar källkod
**Symptom:** `map_bcg_source.py` dog på `UnicodeEncodeError '\u2192'` (pil i docstring) i PS 5.1.
**Rotorsak:** Default konsol-encoder = cp1252; kan inte encoda Unicode i BCG-källan (pilar, å/ä/ö).
**Regel:** Script som skriver godtycklig källkod till stdout ska ha
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` överst + per-rad ascii-fallback i log().
PS-sidan: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` före körning.

### Format-List när Get-ChildItem-kolumner trunkeras
**Symptom:** `Select-Object FullName, Length` klippte både sökväg och Length i smal konsol → kunde
inte se om en output-fil var en OneDrive-stub.
**Regel:** För fullständiga sökvägar + storlek: `| Format-List FullName, Length` (en rad per fält,
ingen trunkering). Length liten (<~10 KB) på en output-fil = OneDrive on-demand-stub → "Behåll alltid
på den här enheten" före läsning, annars läser pandas en tom platshållare.

### Ett kartläggningsscript > tio fil-frågor
**Symptom:** Bad om "en fil till" upprepade gånger ur originalfoldern.
**Regel:** När flera filer ur en stor folder behövs, bygg ETT read-only script (`map_bcg_source.py`)
som dumpar all kod i sin helhet + spreadsheet-STRUKTUR (ej rådata), med skip-logik för genererade
mappar. `--subdir` + `--code-only` håller utskriften hanterbar. Sparar rundor för båda.

---

## 5. ARTEFAKTER DENNA SESSION

| Fil | Mål-sökväg | Roll |
|---|---|---|
| `fallback_blend.py` | `C:\Projekt\BCG\` | Steg 5-replikering, facit-validerad. Versionsstyrs |
| `map_bcg_source.py` | `C:\Projekt\Business_Analytics\` | Read-only källkartläggning (kod full, xlsx struktur) |
| `inspect_fallback_source.py` | `C:\Projekt\Business_Analytics\` | Read-only dump av step5-källa + dashboard |
| `SESSION_2026-05-25_*.md` | repo | Denna |

Genererade (gitignore): `blended_output.csv`, `bcg_replication_blend*.csv`, `blend*_log.txt`,
`bcg_map_*.txt`.

---

*Skapad 2026-05-25 vid steg 5-milstolpe + steg 6-kartläggning.*
