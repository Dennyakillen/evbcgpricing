# OFFBOARDING_KRITISKT — det som inte följer med när utvecklarens dator och konton avvecklas

*Utvecklare: Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB). Läge 2026-10-21. Status: **täckt** = ersatt och verifierat ·
**IT** = kräver beslut eller åtgärd av IT · **öppen** = inte mätt eller inte åtgärdat.*

Koden finns i Azure DevOps, datan i Azure Blob (`docs/ops/DATA_PLACERING.md`). Det här är det som ändå hänger på en person, en dator
eller ett konto.

| # | Det här försvinner | Ersätts av | Status |
|---|---|---|---|
| 1 | **Värdena i `tools/dw/.env`** (DW-server och databas för REGEN) | `tools/dw/.env.example` + värden från DW-förvaltaren. Behövs bara för REGEN; PREP och modellerna kan köras på bränslet i Blob (`input/parquet/`) | **IT** |
| 2 | **Lokal data** (indata, mallar, utdata) | spegeln `spegel/bcg_2026-10-20/` (22 009 filer, sha256-verifierade 2026-10-20) + `tools/spegel/spegel_fran_blob.py` | **täckt** |
| 3 | **Facit i utvecklarens OneDrive** (BCG-originalet) | de nio filer validatorerna använder, byte-exakt i `pipeline/00_frozen_facit/bcg_original/`; resten dokumenterat i `docs/BCG_ORIGINAL_REFERENSER.md`. Bevis: `proof_chain` gav identiskt resultat mot OneDrive-originalet och mot Azure-kopian (2026-10-21) | **täckt** (arkivplats för hela originalet: se referensfilen) |
| 4 | **Git-historiken** (174 commits). DevOps-importen är en enda commit utan historik, och originalrepot avvecklas med utvecklaren | `spegel/historik/evbcgpricing_2026-10-21.bundle` (2 680 243 B, sha256 i blob-metadata, börjar `AAAF54451B6F6FE8`). Återläst ur Blob och klonad 2026-10-21: samma `main`, 174 commits. Återskapa: ladda ner bundlen och kör `git clone <bundle> <mapp>` | **täckt** |
| 5 | **Behörigheter knutna till utvecklaren:** roll på lagringskontot som ger nyckelåtkomst (PIM), DW-läsning via AAD + VPN, åtkomst till VM:en (VPN till dess privata nät + roll som får starta/stoppa den via `az vm`), Azure DevOps-repot | motsvarande roller för förvaltaren. Resurserna ligger i resursgruppen `ev-openai-swce-rg-test`, subscription `ev-lz3-ai (SE)` | **IT** |
| 6 | **SSH-nyckeln till VM:en.** `orchestration/infrastructure/azure_vm.py` (`VmConfig`) ansluter som `azureuser` till VM:en `bcg-poc-vm` (privat IP, kräver VPN) med `ssh -o BatchMode=yes` och standardnyckeln i `%USERPROFILE%\.ssh\`. Mätt 2026-10-21: VM:en skapades med **en** nyckel — utvecklarens personliga (RSA 2048, utan lösenfras, fingeravtryck `SHA256:9uGpVIe9vBlYFCVmOTBCNsyRWs4grvGPzOXUFoo8rdA`) | förvaltarens egen nyckel inlagd på VM:en och utvecklarens borttagen — se *SSH: byte av nyckel* nedan | **IT** |
| 7 | **Arbetsmiljön** (Python 3.11, Excel för steg 5/6 via xlwings, ODBC Driver 17, Azure CLI) | `install.py` + `verify_setup.py` (kontrollerar allt utom Excel-licensen) | **täckt** |
| 8 | **Förvaltaransvaret** | KRAVSPEC_IT §4: "Vem är förvaltare av modellen efter Jens?" | **beslut: chef + IT** |
| 9 | **Utvecklarens arbetsmetodik** (sessionsverktyg, beslutsfiler, metodfiler) | behövs inte för drift — följer medvetet inte med till DevOps (beslut 2026-10-21) | — |
| 10 | **Utvecklarens dator som säkerhetsnät** — i dag finns datan också lokalt; efter avvecklingen är Blob enda kopian. Mätt 2026-10-21: mjuk borttagning (soft delete) för blobbar och containrar och versionshantering är **avstängda** — en blob som raderas eller skrivs över är borta direkt | mjuk borttagning för blobbar och containrar (Microsoft rekommenderar minst 7 dagar); överväg Azure Backup. Kostnaden ökar med kedjans överskrivningar — IT väljer antal dagar | **IT** |
| 11 | **GitHub-repot** (privat, på utvecklarens personliga konto) — hela historiken, däribland företagsdata och klustringens mappningsfil med anställdas namn och e-post | historiken finns i Blob (rad 4), så repot kan raderas eller lämnas över utan att något går förlorat. Se `docs/ops/KANSLIGHETSREGISTER.md` F4 | **beslut: chef + IT**; utvecklaren genomför |

## Ordning för den som tar över

1. IT ger rollerna i rad 5 (och rad 1 om REGEN ska köras), byter SSH-nyckel enligt rad 6 och beslutar om rad 10.
2. Ny dator: `README.md`, avsnittet *Ny dator — en gång* (klona → `install.py` → `spegel_fran_blob.py` → `verify_setup.py`).
3. Första körningen: `DRIFT.md`.

## SSH: byte av nyckel (rad 6) — för IT

Enligt Microsoft **lägger** `az vm user update --ssh-key-value` **till** en nyckel i `authorized_keys` och tar inte bort någon.
Utvecklarens nyckel fortsätter alltså att fungera tills den tas bort uttryckligen.

1. Förvaltaren skapar en egen nyckel på sin dator, t.ex. `ssh-keygen -t ed25519`. Koden kör `BatchMode=yes` (ingen fråga om
   lösenfras), så nyckeln behöver laddas i ssh-agent (Windows-tjänsten *OpenSSH Authentication Agent*) eller sakna lösenfras —
   det första är att föredra.
2. IT lägger in förvaltarens publika nyckel och tar bort tidigare nycklar i samma steg, med VMAccess-tillägget (VM:en ska vara
   startad):
   `az vm extension set -g ev-openai-swce-rg-test --vm-name bcg-poc-vm --name VMAccessForLinux --publisher Microsoft.OSTCExtensions --version 1.5 --protected-settings <fil.json>`
   där `<fil.json>` innehåller `{"username": "azureuser", "ssh_key": "<förvaltarens publika nyckel>", "remove_prior_keys": true}`.
   Alternativ: `az vm user update -g ev-openai-swce-rg-test -n bcg-poc-vm -u azureuser --ssh-key-value <fil.pub>` och därefter
   ta bort utvecklarens rad ur `~azureuser/.ssh/authorized_keys` (fingeravtrycket står i rad 6).
3. Kontroll från förvaltarens dator: `ssh -o BatchMode=yes azureuser@<IP i VmConfig> hostname` svarar; med utvecklarens nyckel
   ska samma kommando nekas.

Kontot `azureuser` delas. Ett personligt konto per förvaltare är spårbarare, men då ska `vm_user` i `VmConfig` ändras.

## Ändringar

| Datum | Ändring |
|---|---|
| 2026-10-21 | Första versionen. |
| 2026-10-21 | Rad 4 täckt (bundlen uppladdad och återläst). Rad 5: VPN och VM-roll. Rad 6 mätt (en nyckel, utvecklarens) → IT. Ny rad 10 (skydd mot radering). Avsnittet *SSH: byte av nyckel*. |
| 2026-10-21 | Ny rad 11 (GitHub-repot). |
