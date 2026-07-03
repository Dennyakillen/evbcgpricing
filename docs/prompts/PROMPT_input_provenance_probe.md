# PROMPT till nästa session — bygg färskhets-/placeringssonden (input_provenance_probe)

*Utvecklare: Jens Palmö. Skriven 2026-07-03 efter en session där EFTER-kedjan bevisades
end-to-end men till priset av FEM körningar och TRE tysta kontamineringar. Denna prompt
beskriver den sond som hade gett hela lösningen i ETT svar. Klistra den, eller läs den som
kravspec och be Claude bygga sonden.*

---

## Till Claude: kontext och uppgift

Förra sessionen körde vi EFTER-kedjan (FD.37: PULL → step6 → build_r12 → PUSH) skarpt för
första gången på maj-fönstret `2022-07-01_2026-05-31`. Kedjans MEKANIK fungerade direkt.
Men vi fick fem körningar och tre kontamineringar innan väven blev ärlig, ALLA av samma
grundorsak: **en input-fil som koden läste var inte den fönstret krävde, och inget mätte
det förrän step6 redan vävt på fel material.** Konkret, i tur och ordning:

1. **Cluster-stub:** `output_summary_ready.xlsx` var en 5 889-byte-stub (kan inte bära 3 791
   KEY) som legat i ready-kanalen sedan ≥2026-06-01. Blobben PULL läste från var 06-17-daterad,
   fem dygn före cluster-relaunchen. Väven fick tom cluster-gren bakom en grön fas.
2. **Site-stale:** samma väv fick en site-`output_summary` daterad 06-17 (pre-maj) för att
   blob-källan aldrig uppdaterats efter site-maj-körningen 06-22.
3. **Pre-maj model_summary:** step5:s p-värdesfil live var 06-10 (april); maj-versionen (52 MB,
   06-22) hade selektivt INTE fetchats från VM och fanns bara på VM-diskens `~/bcg/site/output/`.

Varje fel var i efterhand en MÄTBAR egenskap av filsystemet FÖRE körning. Vi upptäckte dem
bakvänt, en fil i taget, efter körning. **Det här är gapet du ska stänga med en sond.**

## Den bärande insikten (mönstret, inte bara uppgiften)

En pipeline är bara så färsk som sin STALASTE input. En grön statusfas bevisar att PROCESSEN
kördes — inte att rätt MATERIAL gick in. Vi har validerat process i månader (`all_chain_validator`,
`dry_run_pipeline`, provenance/rationality-kvitton) men aldrig validerat input-färskhet per
fönster. Sonden ska mäta exakt det, på TRE axlar per nyckelfil:

1. **Lokal-axeln:** finns filen på den EXAKTA sökväg koden läser? (ur `Constant.py`,
   `config.yml`, `_AFTER_INPUTS` i `blob.py` — INTE i en `azure_run_*`-spegel eller ett arkiv)
2. **Blob-axeln:** finns filen i Blob på run_id-sökvägen? (robusthetsmålet: överlever Jens dator)
3. **Fönster-axeln:** ligger filens tidsstämpel/innehåll i målfönstret? (maj, inte kvarliggande april)

En fil är GRÖN bara om alla tre stämmer. Gul om axel 3 är tvetydig (t.ex. deterministiskt
regenererbar som `ivc_sweden_price.csv` — samma bytes oavsett fönster, gammalt datum men färskt
innehåll). RÖD om någon axel fallerar.

## Vad sonden ska göra (kravspec)

**Namn:** `input_provenance_probe.py`. **Placering:** `verify_tool/probes/`. Den ska INTE bli en
femte probe-generation — den är den SAKNADE AXELN i den befintliga `dry_run_e2e.py` (som redan
täcker MOTOR-drift + SURVIVALTEST-läckor men INTE input-färskhet). Bygg den fristående men
designa den så `dry_run_e2e --stage fore` kan anropa den. Rör inte sondfloran; konsolidering är BB.1.

**Input-registret (härled, deklarera inte två gånger):** läs de faktiska sökvägarna ur källan —
`Constant.py` (blended_model_path=ready, prod_site_level_path, bundle_cluster_level_path,
blended_output_path), varje familjs `config.yml` (`output_summary_path`, `model_summary_save_path`,
`raw_input_data`, item_description), och `blob.py:_AFTER_INPUTS`. Om du hårdkodar en sökväg har du
byggt nästa divergens (LB.85). Läs dem, mappa dem, mät dem.

**Per fil, rapportera de tre axlarna:**
```
FIL                          LOKAL              BLOB               FÖNSTER      DOM
output_summary_ready (clu)   368KB 07-03 ✓      325KB 07-03 ✓      maj ✓        GRÖN
model_summary (site)         52MB 06-22 ✓       52MB 07-03 ✓       maj ✓        GRÖN
ivc_sweden_price (site)      149MB 06-10 ✓      saknas ✗           regen ~       GUL (regenererbar)
```

**Kritiska gate-krav (lärdomar från sessionen, ALLA som throwing kod — inte kommentarer):**
- **Storleks-sanity, inte bara existens:** en 5 889-byte xlsx kan inte bära tusentals KEY.
  Sätt per-filklass en min-byte-tröskel. (LB.86-familjen: stub-detektering.)
- **Position, inte namn:** verifiera filen på sökvägen KODEN läser, inte i en spegel. Cluster-stub
  och site-stale kom båda av att rätt-namngiven fil låg på fel/gammal position.
- **VM-axeln som fallback:** om en fil saknas lokalt OCH i Blob, föreslå `ssh ls ~/bcg/<fam>/output/`
  — VM-disken överlever `deallocate` och var sista räddningen (LB.90). Sonden ska inte starta VM
  själv (kostar pengar) men ska SÄGA att VM-disken är nästa ställe att leta.
- **Regenererbar vs nyckelfil:** skilj filer med fönster-DNA (modellartefakter) från deterministiskt
  regenererbara (regular-price ur statisk rådata). De senare får vara gamla på disk.

**Utdata:** konsol med `[GATE]/[GRÖN]/[GUL]/[RÖD]`-rader + Excel-kvitto i
`workspace/validation_receipts/` (openpyxl, engelska kolumner, UTC-tidsstämpel i filnamn —
följ `dry_run_e2e`-mönstret). Exit 0 om inga RÖDA, 1 annars.

**Auth:** använd `blob.py`:s egen env-hantering (`PRICINGMODEL_AUTH=key`), och hämta nyckeln via
`az ... keys list --resource-group ev-openai-swce-rg-test` (LB.88: sub-bred lookup kräver rätt
utanför scopad PIM). Verifiera aldrig med utskrift-att-läsa — gate:a i kod.

## Hur sonden HADE löst hela förra sessionen i ett svar

Körd FÖRE första run_after mot maj-fönstret hade den skrivit:
```
output_summary_ready (cluster)  LOKAL: 5889B ✗ (stub!)   → RÖD
output_summary (site)           BLOB: 06-17 ✗ (pre-maj)  → RÖD
model_summary (site)            LOKAL: 06-10 ✗ saknas i Blob → RÖD (VM-disk: kolla ~/bcg/site/)
```
Tre röda rader, upptäckta på 20 sekunder, före en enda väv. I stället för fem körningar och tre
kontamineringar hade det blivit: läs sondens tre röda → reparera de tre filerna → kör en gång → grönt.

## Din uppgift, konkret

1. Be om de filer du behöver DIREKT (A.9b — källa före hypotes; förra sessionen kostade fyra
   sökvägsgissningar för att jag INTE bad om filernas faktiska placering upfront). Minimum:
   `Constant.py`, de tre familjernas `config.yml` + `constants.py`, `blob.py`. Be om dem först.
2. Bygg `input_provenance_probe.py` per kravspec ovan. Testa den offline mot syntetiska
   status/fil-lägen (inkl. ett stub-scenario och ett stale-scenario) innan leverans.
3. Leverera som nedladdningsbar fil, committa i `verify_tool/probes/`, och lägg en rad i
   `dry_run_e2e.py`:s FÖRE-stage som anropar den.
4. Peka ut var den ansluter till Jens robusthets-slutmål (3-axel-validatorn) och till BB.5/BB.11.

Detta är inte en ny idé — det är kravspecen nattens ärr redan skrivit. Bygg den, så blir nästa
månadskörning ett körblock i stället för en utgrävning.
