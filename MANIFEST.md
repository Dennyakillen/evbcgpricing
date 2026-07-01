# MANIFEST — evbcgpricing (BCG price elasticity)

**Instans** (projektspecifik, inget MASTER-prefix). Enda arkitekturprimitiv som bor i projektet — den
*refererar* bibliotekets delar, bär aldrig en kopia (MASTER_ORCHESTRATION §1, MASTER_GIT §5).
**Developer:** Jens Palmö (Senior Business Analyst)
**Updated:** 2026-07-01 · **Färskvara (SHA, resurs-ID, status):** se STATE.md

> **Vad denna fil är:** BCG:s medvetna *urval* ur biblioteket + de tre VAKTEN-trösklar som är
> specifika för detta projekt. Den definieras lika mycket av vad den *klipper* som av vad den drar in
> (SPINN §2.2 steg 4). **Vad den INTE är:** färskvara (→ STATE.md), kö för nästa session
> (→ NEXT_SESSION.md), eller lärdomar (→ LESSONS_BCG.md). En rad här ska vara stabilt *urval*, inte
> *tillstånd* — MANIFEST/STATE-gränsen är omdömesburen (MASTER_ORCHESTRATION §2.3).

---

## Läge

**Retroaktiv** (MASTER_ORCHESTRATION §2). BCG har djup git-historik och bevisade artefakter — väven
seedas från verifierat läge (STATE.md), aldrig från tom mall (LK.2). Greenfield-scaffold är klippt tråd.

---

## Väven — vad BCG drar in

**Alltid laddad:**
- `KÄRNPRINCIPER.md` — kanonisk tvärs alla projekt, trumfar vid konflikt. Ägs av biblioteket,
  redigeras aldrig lokalt. All uppflyttning av lärdom styrs av dess §7 (eskaleringsflagga) + §6.6.

**Organisatoriska masters** (nya — bor i Master-Bibliotek, `C:\Projekt\masters`, refereras):
- `MASTER_ORCHESTRATION.md` — SPINN / VAKTEN / fångstloop. Levande här: §2′/5′ (retroaktiv seed) + §3 (VAKTEN).
- `MASTER_GIT.md` — nät-topologi (nav + ekrar), §3b leveransverifiering, §4 väv-validering.
- `MASTER_VALIDATION.md` — "mät, gissa inte" som universell princip (teknikerna ägs i domänmasters).
- `MASTER_DOCUMENTATION.md` — två register + README-krav (mapp-README som indirekt scope-vakt).

**Tekniska masters** (befintliga — laddas per domän):
- `MASTER_PYTHON.md` — miljödisciplin (tre venv, korsa aldrig), valideringsmetoder, felsökningsmönster, filhuvuden §4.6.
- `MASTER_SQL.md` — DW-schema, SQL-designprinciper (DW-extraktion via `Business_Analytics`, `01_process.sql`).
- `MASTER_AZURE.md` (+ `MASTER_AZURE_COMPUTE.md`) — moln + compute (VM, Blob, roller, ABAC, felsökning).
- `UBUNTU_AZURE_VM.md` — Linux/bash för VM-operationer (SSH-citeringsdisciplin, Ray-venv).

**Skills:** — (inga än; införs när Claude Code är aktivt).
**Hooks:** — (inga aktiva; `guard-bash.py` finns i ECC-forken, aktiveras när Claude Code är på — bibliotek B.5/B.9).
**Agents:** — (inga).

> Projektets egna styrdokument (STATE, SYSTEMGUIDE, FUNKTIONSKARTA, REPLIKERING_OCH_VALIDERING,
> BLOB_MALSTRUKTUR, README_VALIDERING, LESSONS_BCG, NEXT_SESSION) är **projektkroppen**, inte väven —
> se README/STATE. Väven = bibliotekets delar BCG konsumerar via referens.

---

## Klippta trådar (medvetet utelämnat — obligatoriskt, SPINN §2.2 steg 4)

Urvalet definieras av exklusionerna lika mycket som inklusionerna; utan dem skyddar manifestet inte kontexten.

- **SPINN greenfield-läge** — BCG är retroaktivt; tomma mallar kastar det git redan bevisat (LK.2).
- **Git submodules** (MASTER_GIT §1) — skulle lägga biblioteksreceptet i BCG:s historik. Referens, ej kopia.
- **Kubernetes / container-patterns** (bibliotek B.12) — "inget Kubernetes runt ett månadsjobb". DÖD-trolig.
- **Healthcare CDSS / EMR-patterns** (bibliotek AVFÖRD) — fel domän; arbetet rör djursjukvårdens *data*,
  inte byggande av kliniska beslutsstöds- eller journalsystem.
- **Bibliotekets tvärgående BACKLOG (`B.*`)** — dras INTE in i BCG:s dagliga kontext. BCG bär egen
  `BB.*`-backlogg som vävs ihop med bibliotekets i en dedikerad session (se BACKLOG.md-huvudet).

---

## Triggers (VAKTEN — §3, laddas per session)

Tre triggers, inget annat övervakas. Liten av design → ständigt i kontext. Trösklarna nedan är
BCG-specifika; mekaniken ägs i MASTER_ORCHESTRATION §3. De mappar mot tre felklasser: dyraste
tidsförlust, dyraste körningsförlust, dyraste tysta fel.

### 1 — Scope-glidning *(dyraste tidsförlust)*
Arbete kräver del utanför Väven ovan — ny master/skill, eller ännu en probe-generation som dubblerar
befintligt (t.ex. ett verktyg som överlappar `all_chain_validator.py`).
→ **Stoppa:** *"Utanför väven — lägg till medvetet, eller avvisa?"* (A.9, §6.4).

Detta är grinden mot den ackumulering som redan syns i projektet: probe-spretning över fyra
verktygsgenerationer, ~12 minnesposter av avklarat historiskt tillstånd, ~80-filers bibliotekstriage.
Det är *denna* trigger som adresserar scope-glidningen mellan sessioner.

### 2 — Bruten förutsättning *(dyraste körningsförlust)*
Ett villkor för körning håller inte. BCG:s konkreta villkor (aktuella värden i STATE §3/§7):

- **KRITISKT — AAD-token < 4h** (E.3): `az login --scope https://management.core.windows.net//.default`
  före varje Blob/VM-pass. Dör var 4:e h.
- **KRITISKT — rätt subscription aktiv** (LB.46): `az account show` = `ev-lz3-ai (SE)` före VM-kommandon.
  Fel subscription ger `AuthorizationFailed` (VM "finns inte"), inte token-fel.
- **KRITISKT — `transaction_data.parquet` regenererad för målperioden FÖRST** (LB.50 / G7-klassen):
  annars filtreras ny data tyst bort.
- **BRA PRAXIS — `dry_run_pipeline.py` (19 rör-kontroller) gröna** före varm körning: fångar fel kallt,
  inte mitt i en flertimmars körning.
- **KRITISKT — operation mot BCG:s originalkod: endast additivt** (env-override, patch före merge-punkt).
  Rör aldrig nedströmslogiken (LB.73-76). Fil märkt `FLYTTA ALDRIG` / `REGRESSIONSVAKT` eller med hög
  import-fan-in → stopp *före* ändring.

→ **Stoppa före körning, åtgärda, kör sedan** (§6.5, E.3).
→ **Efter VM-arbete:** `az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm`
  (LB.68 — ingen auto-shutdown; `deallocate`, inte `stop`; ~9 kr/h running).

### 3 — Divergens *(dyraste tysta fel)*
Samma ID / regel / schema på två ändringsbara ställen. BCG:s ID-rymder och kända divergensklasser:

- **Lärdoms-ID:** `LB.*` / `LF.*` / `LK.*` (LESSONS_BCG) får ej krocka med `MASTER_*`-lärdoms-ID (L.38-klassen).
- **Backlogg-ID:** BCG:s `BB.*` får ej krocka med bibliotekets `B.*` vid vävning.
- **Två prep-vägar, samma sak, olika schema** — kanonisk BCG-divergensklass: `No_of_Sites` vs
  `No_of Sites` (understreck/mellanslag), `TotalNetXVat` finns/saknas mellan `export_b4b_for_model.py`
  och SQL-prep `01_process.sql`. Ett schema, en ägare.
- **`MASTER_AZURE` i BCG (386 rikare rader) vs bibliotekets** — känd, parkerad divergens (BB.2, väntar Claude Code).
- **En master kopierad in i BCG = skugg-kopia** (MASTER_GIT §3b/§5) — divergenskälla. Precis det denna
  anslutning undviker: masters *refereras*, kopieras aldrig.

→ **Lös enligt §6.6:** en ägare, övriga refererar med ID.

---

## Färskvara → STATE.md

Resurs-ID, VM-status, aktiv subscription, roller, Blob-läge, senaste commit/SHA, fas-status — allt sådant
bor i STATE.md, aldrig här (STATE-regeln: en sanning, en plats).

---

*Spunnen som del av arkitektur-anslutningen 2026-07-01. Förvaltas av Jens Palmö (Senior Business
Analyst). Urval, inte tillstånd — färskvara bor i STATE.md, kön i NEXT_SESSION.md, lärdomar i
LESSONS_BCG.md.*
