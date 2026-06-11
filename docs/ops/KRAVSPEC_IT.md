# KRAVSPEC_IT — Underlag för dialog med IT (Kent + vidare)

**Status:** Utkast — internt arbetsdokument, ej skickat
**Ägare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB)
**Syfte:** Förbereda en komplett kravlista mot IT så vi kan ta BCG-prismodellen
från VM-PoC till produktionsbar Azure-lösning utan reaktiva följdfrågor.
**Skapad:** 2026-06-05 vid avslut av FAS F.6 (cluster steg 1-4 på växande fönster)

> **Strategiskt sammanhang (FAS 3, 2026-05-22):**
> *"Jag önskar inte be IT om mer då jag dels tror det jag har räcker och dels
> vill ge dem en komplett kravlista framför att reaktivt fråga dem."*
>
> Denna spec är den listan. Den kompletteras kontinuerligt under FAS F till F är
> klar (alla tre modellfamiljer + fallback körda på växande data), då skickas
> den slutgiltiga versionen till Kent + IT-ledning.

---

## 1. Vad är bevisat (status 2026-06-05)

### Pipelinen fungerar end-to-end

| Steg | Status | Bevis |
|---|---|---|
| BCG-replikering bit-för-bit | ✅ Bevisat | Korr 1.0 mot facit på alla 3812 KEY (FAS V) |
| DW-extraktion | ✅ Validerat | 0.057% drift mot facit, växande fönster CSV genererat |
| Cluster steg 1-4 på växande data | ✅ Klart | 1521 KEY × 200 veckor körda 2026-06-05, output arkiverat |
| Cluster fallback (steg 5) på växande | ⏳ Pending (F.7) | Kommande session |
| Site + Bundle på växande | ⏳ Pending (F.8) | Kräver ny VM-körning |
| Multi-modell-väv (steg 6, F1-F7) | ⏳ Pending (F.9) | Kräver Site + Bundle först |

### Infrastruktur som faktiskt används

- **VM:** `bcg-poc-vm`, Standard_E16s_v5 (16 vCPU / 128 GB RAM), Ubuntu 22.04
- **Resursgrupp:** `ev-openai-swce-rg-test` (Jens PIM Contributor)
- **Subscription:** `ev-lz3-ai (SE)`
- **VNet:** `ev-lz3-swce-vnet-prod`, åtkomst via privat IP från kontorsnätet
- **Storage account:** `evbcgpricinginput` (skapad men ej använd p.g.a. rollblockering)
- **Pipeline-venv:** Python 3.11.9 på VM, isolerad via uv

### Kostnad i nuläget

- VM tickar ~9 kr/h **bara när vi kör**. Deallokerad mellan körningar (rutin).
- Per komplett körning (steg 3+4 + fallback + analys): ~25-40 kr
- Per månad (om vi kör 4 gånger/månad för olika tidsfönster): ~150-200 kr

---

## 2. Vad vi behöver av IT (kravlista)

### 2.1 Roller och behörigheter

#### Blockerande nu (ej brådskande, hanteras lokalt)

| Behov | Scope | Varför |
|---|---|---|
| **Storage Blob Data Contributor** | `evbcgpricinginput` | Ladda upp input-data till Blob istället för manuell scp till VM |
| **Alternativt: Owner på RG** | `ev-openai-swce-rg-test` | Lösa all framtida rolltilldelning (Blob + Managed Identity + ACR) i ett |

> **Rekommendation:** Owner på RG. Sandlådan är Jens egna, blast radius noll,
> sparar IT från en serie följdförfrågningar.
> Mejlutkast finns i FAS 1-sessionen och kan återanvändas oförändrat.

#### För produktionssättning (kräver beslut)

| Behov | Beror på beslut om | Anmärkning |
|---|---|---|
| Managed Identity på compute-resurs | Vilken hosting (se 2.2) | För Azure SQL-åtkomst utan delegated token |
| AcrPull till Managed Identity | Om container-baserat | För att pulla image från ACR |
| Azure SQL: läsbehörighet | DW-extraktion | Redan löst via befintlig DefaultAzureCredential |

### 2.2 Hosting-beslut (kräver IT/lednings-input)

Pipelinen är idag manuellt startad på en VM. För produktion behövs ett val:

| Alternativ | Lämplig för | Kostnad/mån (uppskattad) | Komplexitet |
|---|---|---|---|
| **A. Fat VM som idag** (Standard_E16s_v5) | Manuell körning 1-4 ggr/månad | ~150-300 kr (deallocate mellan körningar) | Låg |
| **B. Azure Container Instances** | Schemalagd körning per månad | ~100-200 kr (scale-to-zero) | Medel |
| **C. Container Apps Jobs** | Schemalagd + event-trigger | ~150-300 kr | Medel |
| **D. AKS + KubeRay** | Genuint distribuerat | ~1500-3000 kr + overhead | **Hög** |

**Vår rekommendation (per CZ.1, MASTER_AZURE_COMPUTE):**
Alternativ A eller B. Pipelinen är RAM-bunden, inte distribuerad — en stor VM
löser problemet utan Kubernetes-skuld. Endast om körningsfrekvens överstiger
1/vecka är B mer kostnadseffektivt än A.

Behöver IT-input för:
- Bekräfta att Sweden Central E-serien-quota fortsatt har headroom
- Bekräfta sanktion för ev. Container Apps i `ev-lz3-ai`
- Långsiktig kostnadsmodell — VM-as-needed vs scheduled compute

### 2.3 Data-pipeline (kräver IT-input)

| Behov | Status | Anmärkning |
|---|---|---|
| Azure SQL DW-läsbehörighet | ✅ Fungerar | DefaultAzureCredential, scope `database.windows.net` |
| Token-livslängd > 4h | ❌ Conditional Access begränsar | E.3 — accepteras som arbetspremiss, ej blockerande |
| Schemalagd DW-extraktion | ⏳ Inte byggt | Beslut: orchestration-verktyg (Azure Data Factory? Logic App? Pipeline-skript med Managed Identity?) |
| Färsk-data-frekvens | ⏳ Inte beslutad | Affärsbeslut: månadsvis räcker för prisbeslut |

### 2.4 Backup, säkerhet, governance

| Behov | Status |
|---|---|
| Git som "source of truth" för all kod | ✅ Två repon på Dennyakillen-orgens GitHub (privata) |
| Säkerhetskopia av modelloutput | ⏳ Inte adresserat — behövs blob-versionering eller liknande |
| Audit log på vem som kör modellen | ⏳ Inte adresserat |
| GDPR — innehåller modellen personuppgifter? | ✅ Nej (KEY = Cluster × ItemCode, inga patient-/kundnamn) |

---

## 3. Tekniska skulder att stänga (egen lista, ej IT-blockerande men värd att deklarera)

### 3.1 Klar / parametriserad

| Skuld | Status | Åtgärd |
|---|---|---|
| Hårdkodade datum i `constants.py` (START/END_DATE, SPECIAL_WEEKS) | ✅ G7-parametriserat 2026-05-28 | Env-overridable via `BCG_END_DATE` |
| Hårdkodade datum i `export_b4b_for_model.py` | ✅ G7-parametriserat 2026-05-29 | Env-overridable |
| Dead config i config.yml (`InScope Mapping`, `competitor_data`) | ⏳ Dokumenterad i L.39 | Bör tas bort vid förvaltningsöverlämning |

### 3.2 Aktiva skulder (klassificerade)

| Skuld | Klass | Plan |
|---|---|---|
| Hårdkodad `C:\ray_spill` i lokal `feature_selection.py` | Plattformskuld | G7-mönstret — env-overridable path. **Hör adresseras i FAS T innan IT-överlämning.** |
| Två kodbaser för samma fil (lokal Windows-version vs VM Linux-version, divergerande hashar) | Plattformskuld | Konsolidera till en kodbas med env-overrides. **FAS T.** |
| Output-mappar i pipelinen skapas inte automatiskt (CZ.5 manifesterad LB.43-stil) | Robusthet | `mkdir -p` i alla skript som skriver, eller pre-flight i check_env. **FAS T.** |
| `Significant ?`-kolumnnamn med mellanslag | Konsultarvet | Bevara — inte värt risken att bryta jämförbarhet med BCG |
| `Pipeline\02. Elasticity\` mappnamn med mellanslag och punkter | Konsultarvet | Bevara — för djupt rotat i kodbasens config-sökvägar |
| Inga unit-tester på modellkod | Förvaltbarhet | Acceptera — modellen valideras mot facit istället |
| `check_env.ps1` ej signerad → kräver `-ExecutionPolicy Bypass` per körning | Onboarding | Engångs-`Set-ExecutionPolicy -CurrentUser RemoteSigned` per maskin |

### 3.3 Skulder som väntar på IT-beslut

| Skuld | Beror på |
|---|---|
| Manuell scp av input-filer till VM | Storage Blob role (se 2.1) |
| Manuell `az vm start/deallocate` | Hosting-modell (se 2.2) |
| Delegated CLI-token i pipeline | Managed Identity (se 2.2 + CZ.3) |

---

## 4. Beslut som krävs (för produktionssättning)

| Beslut | Vem | Tidshorisont |
|---|---|---|
| Hosting-modell A/B/C/D (se 2.2) | IT + Jens + chef | När FAS F är klar |
| Körningsfrekvens (månadsvis/kvartalsvis) | Affärsverksamhet | Innan hosting-val |
| Kostnadsbudget | Chef | Innan hosting-val |
| Vem är förvaltare av modellen efter Jens? | Chef + IT | Innan överlämning |
| Vem äger output-filerna affärsmässigt? | Affärsverksamhet | Innan första prisbeslut |

---

## 5. Tidslinje (preliminär)

| Milstolpe | När |
|---|---|
| **NU (2026-06-05):** F.6 klar, denna spec utkastad | Klar |
| F.7: Fallback på cluster växande | Nästa session (~2h) |
| F.8: Site + Bundle på VM | Sessioner senare (~3-4h, kräver VM-tid) |
| F.9: Steg 6 multi-modell-väv | Session efter F.8 (~2h) |
| FAS T: Tekniska skulder stängda | Parallellt med F eller efter |
| **Spec finaliserad och skickad till Kent** | När F är komplett |
| FAS A: Azure-produktionssättning | Efter Kent-dialog + beslut |

---

## 6. Bilagor (referensmaterial)

- `ROADMAP.md` — fasplan V→T→F→A
- `BCG_PRICING_PLAYBOOK.md` — operationell playbook
- `LESSONS_BCG.md` — projektspecifika tekniska lärdomar
- `INSIGHTS_BCG.md` — affärs-/domäninsikter
- `MASTER_AZURE.md` — Azure-mönster, web/long-running
- `MASTER_AZURE_COMPUTE.md` — Azure compute-mönster, batch
- `UBUNTU_AZURE_VM.md` — VM-drift, Linux/bash
- Mejlutkast till Kent (FAS 1-session, "Owner på RG:n"-varianten) — kan
  återanvändas oförändrat när det är dags att skicka

---

## 7. Senaste uppdateringar

| Datum | Vad |
|---|---|
| 2026-06-05 | Utkast skapat vid avslut av FAS F.6 |

*Denna fil uppdateras varje session medan FAS F pågår. När F.9 är klar
finaliseras specen och skickas som komplett kravlista — inte stegvis.*
