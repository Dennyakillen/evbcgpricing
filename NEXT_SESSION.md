# NEXT_SESSION — BCG Pricing PoC (validering mot facit)

Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst på
Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md`, `MASTER_AZURE.md`,
`MASTER_AZURE_COMPUTE.md`. Linux/bash-handhavande: `UBUNTU_AZURE_VM.md`.

> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant MASTER_*.md.

---

## Aktuellt projekt

- **Repo:** https://github.com/Dennyakillen/evbcgpricing.git
- **Lokal arbetsrot:** `C:\Projekt\BCG`
- **Azure-VM:** `bcg-poc-vm` i `ev-openai-swce-rg-test` (sub `ev-lz3-ai`), privat IP `172.18.148.4`
- **Status:** VM **deallocated** (kostar inget). Allt arbete består på disken.
- **Azure-resultat hämtat lokalt:**
  `...\2. Product Cluster Level Models\output\azure_run_model\` (`output_summary.xlsx` ~320 KB,
  `model_summary.xlsx` ~28 MB, `model_results.csv` ~261 MB).

---

## Status vid sessionsstart

**Modellsteget är validerat på Azure — full körning, alla 3812 grupper, output hämtad lokalt.**

- ✅ Fas 0–3, 8: miljö byggd på VM (Python 3.11.9 via uv, 45 paket), `data_for_model.csv` uppe,
  `model.py` kört hela vägen i tmux. `output_summary.xlsx` producerad och hämtad.
- ✅ OOM avskriven: 128 GB → minnet pegades aldrig (124 GB available, 0 swap). RAM-tak, ej kluster.
- ✅ Rökstest-mekanik bevisad: `make_smoke_control.py` + control-filens `RUN=YES`-spak.
- ⛔ **Blockerat:** hela launcher-kedjan kräver `InScope Mapping.xlsx` (O3 bekräftad — saknas
  lokalt, kommer från Kent/BCG-källan). `regular_price.py` kan inte köra utan den.
- ❌ **Inte gjort:** jämförelse mot BCG:s frusna facit. Det är denna sessions mål.

**Referensvärden:**
- Full körning: 3812 grupper, ~35 min på VM (08:32→09:06). `output_summary.xlsx` ≈ 320 KB.
- Rökstest: 5 grupper, ≈ 5,5 KB — referens för att se att alla grupper körts.
- Facit: BCG:s frusna `output\model\output_summary.xlsx` i V2_New-källan.

---

## Mål för denna session

### Primärt: Fas 7 — validera vårt resultat mot BCG:s facit (KAN GÖRAS LOKALT)

**Insikt:** Detta kräver **ingen VM** — vi har vår `output_summary.xlsx` lokalt och BCG:s facit i
källan. Jämförelsen körs i Python på Windows. **Starta inte VM:en för detta** (ingen kostnad).

**Leveranser:**
1. Lokalisera BCG:s frusna facit-`output_summary.xlsx` i V2_New-källan.
2. Litet jämförelsescript: population (antal KEY-grupper), kolumnuppsättning, summor, och
   nyckel-KPI:t `ELASTICITY_Regular_Price_fwbw_max_6` per grupp (diff/korrelation).
3. Rapport: matchar vårt resultat facit? Var skiljer det, och varför (datumfilter? `cp1252`/
   `encoding_errors='ignore'`-teckenförlust? populationsskillnad pga 3812 vs förväntat antal?).

**Datakälla:** `azure_run_model\output_summary.xlsx` (vårt) vs BCG:s frusna facit (deras).

### Sekundärt (om tid / om facit matchar): planera hela kedjan

- Skaffa `InScope Mapping.xlsx` från Kent/BCG-källan → möjliggör `regular_price.py`.
- Då först kan hela launcher-kedjan köras (kräver VM igen, tmux, samma mönster som 2026-05-21).

---

## Om VM behövs igen (kall start)

Se `README.md` → "Daglig drift". Kort: `az login` → `az account set` → PIM → `az vm start` →
`ssh` → `source .venv/bin/activate`. tmux-sessioner är borta efter deallocate — starta ny.
**Deallokera efter användning.**

---

## Standarder särskilt relevanta nu

- **R7:** lita aldrig på "Pipeline completed" — verifiera filen (storlek/tidsstämpel).
- **Kostnad:** fas 7 är lokal — ingen VM, ingen debitering. Starta bara VM om kedjan ska köras.
- **L.14:** läs källan, verifiera filversion/encoding (`xxd`) innan fix.
- **Token (E.3):** `az`-token dör efter 4 h; logga in igen vid behov.

---

## Öppna beslut / blockerare in i nästa pass

| # | Fråga | Behöver |
|---|---|---|
| O1 | Owner på `ev-openai-swce-rg-test`? | Kent — för dataroller/Blob/ACR (ej för VM-PoC) |
| O3 | `InScope Mapping.xlsx` | ✅ Bekräftad krävs — saknas lokalt, hämta från källa |
| O4 | Blob + DW-vyer (drift) | Efter validering |

*Skapad 2026-05-21 vid avslut av Azure-modellkörningssessionen.*
