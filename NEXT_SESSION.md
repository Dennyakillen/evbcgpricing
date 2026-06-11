# NEXT_SESSION — F.10 Step 6 + rimlighetsgrind på Cluster+Site (färska affärselasticiteter)

**Projekt:** evbcgpricing (BCG priselasticitet, växande data)
**Branch:** `fas-f-fresh-data`
**Utvecklare:** Jens Palmö
**Beräknad tid:** 2-3 timmar (Step 6 är lokalt/xlwings; rimlighetsgrind är analys, ej tung compute)

> Du agerar som senior teknisk rådgivare för Jens Palmö, Senior Business Analyst
> på Evidensia Djursjukvård AB. Följ `KÄRNPRINCIPER.md` samt relevanta MASTER_*.md.
> PLAYBOOK och ROADMAP styr som TES, inte bokstav — de skrevs före mycket vi lärt oss.
> Målet är FÄRSKA AFFÄRSELASTICITETER på huvudsortimentet (IB.6), inte teknisk replikering.
>
> **Förbättringsloop:** Vid varje korrigering — föreslå omedelbart ny lärdom
> (Symptom → Rotorsak → Regel) och lägg i relevant master-fil vid sessionsslut.

---

## SESSIONEN I EN MENING

Kör fallback-väven (Step 6, `Fall_Back_Logic.py`) på Cluster+Site växande output, och bedöm
resultatet med output-rimlighetsgrinden (facit finns inte på färsk data → döm på "är elasticiteten
negativ, i trovärdigt band, skulle diffen flippa ett prisbeslut"). Detta är vägen till de första
färska affärselasticiteterna på huvudsortimentet.

---

## STATUS VID SESSIONSSTART

**2 av 3 modellfamiljer klara på växande data — och de täcker huvudsortimentet:**
- ✅ **F.7 Cluster** — step 5 fallback-blend körd (4180 KEY, 33.4%→45.2% signifikans).
- ✅ **F.8 Site** — KLAR 2026-06-10. Steg 1-4 på VM (~70 min, 6624 KEY), steg 5 lokalt.
  Slutleverans `Excel_Outputs/Sweden_Sitecode_level_elasticity_summary.xlsx` (83 MB).
- ⏸️ **F.9 Bundle** — DATAPREP KLAR växande (committad `1daf093`), MODELLEN PARKERAD (FD.11).
  Datadrivet beslut: 98 modellerade varukorgar = 526 M (~4,3%), överlappar Cluster/Site.
  Återbesöks-trigger nedan.

**Datafundament klart:**
- `transaction_data.parquet` regenererad till 2026-04-30 (27,4M rader).
- G7-parametrisering komplett (SQL-dataprep + VM constants.py per familj).
- Bundle-dataprep-källan klar och committad (om/när Bundle lyfts tillbaka).

---

## DENNA SESSIONS UPPGIFT — F.10 Step 6 + rimlighetsgrind

### Steg 6 (fallback-väven, lokalt)
`Fall_Back_Logic.py` — multi-modell-blend, väljer per `ProductKey` slutelasticitet via
`combine_first`-prioritet F1→F7 (IB.2). Körs lokalt (Windows/xlwings, som steg 5).

**Viktig nyans (Bundle parkerat):** Väven är designad F1 site → **F2 bundle** → F3 cluster →
**F4 bundle-across** → F5 product-across → F6 service-within → F7 service-across (IB.2). Bundle sitter
alltså på två nivåer (F2, F4). Med Bundle parkerat måste vi avgöra:
- Kan Step 6 köras på Cluster+Site genom att hoppa F2/F4 (combine_first faller bara vidare till nästa
  tillgängliga nivå)? Sannolikt JA — combine_first kräver inte att varje nivå finns, den tar första
  tillgängliga. Men VERIFIERA mot koden innan körning (LB.51-anda: anta inte att den är körklar utan F2/F4).
- ELLER: kör Step 6 med Bundle på FRUSEN output (BCG:s gamla bundle) som platshållare? Mindre rent —
  blandar fruset och växande. Föredra Cluster+Site-only om koden tillåter.

### Rimlighetsgrind (ersätter facit på färsk data, IB.6)
Facit finns inte på växande data. Döm output på:
- Är elasticiteten **negativ** och inom trovärdigt band (jfr IB.9 per-familj-band: Cluster median
  −0,138, Site −0,054; svansar inom rimligt)?
- Faller nya extremvärden utanför (−10, 0) automatiskt ur signifikans (IB.2-flaggan)?
- Skulle diffen mot fruset facit **flippa ett top-line-prisbeslut**? Om nej → rimligt (IB.6).
- Snapshot-drift inom IB.11-bandet (~0,057% revenue, kluster upp till ~1,5%)? Drift utöver det utan
  extra månader = signal på annat (klinik öppnat/stängt, datakvalitet).
- Kvarvarande att utreda: MBAS0703-outlier (−320) + 7 REVIEW-utfall från rationality-suiten
  (`verify_tool/output_rationality/`).

### Bundle återbesöks-trigger (avgörs HÄR)
**Om** Imaging/Anaesthesia/Hospitalisation-KEY:n (Bundles service-mix, FD.11) ofta blir insignifikanta
eller saknar källa i väven → lyft Bundle tillbaka till kritiska vägen (då räddar det dem). **Om** de
redan prissätts väl av Cluster/Site → Bundle förblir parkerat. Detta är den fullare domen FD.11 väntar på.

---

## PRE-FLIGHT

Step 6 + rimlighetsgrind är **lokalt** arbete (xlwings/analys) — **ingen VM behövs** denna session.
(VM är bara för modellsteg 1-4; de är klara för Cluster+Site.)

Om något ändå kräver VM (osannolikt):
```powershell
# KRITISKT: rätt subscription först (LB.46)
az account show --query "{user:user.name, subscription:name}" -o table
az account set --subscription "ev-lz3-ai (SE)"
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
Start-Sleep -Seconds 90; ssh azureuser@172.18.148.4 "hostname && uptime"
# Deallocera när klart: az vm deallocate --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
```

---

## EFTER F.10

- **Drift-visualisering** fruset facit vs växande, alla familjer — knyt till IB.11-bandet.
- **FD.13 sandbox-Excel** — när väven körts växande finns riktiga exempel att grovmodellera kring för
  metodik-förklaring mot beslutsfattare.
- **Bundle (FD.11)** — lyft tillbaka ELLER bekräfta parkering baserat på rimlighetsgrindens utfall ovan.
- **Fas Z** produktionalisering (FD.1-4) + projektavslut (FD.10).

---

## VID SESSIONSSLUT

1. Committa Step 6-arbetet + rimlighetsgrind-resultat.
2. Flytta dagens lärdomar till master-filerna INNAN sessionen stängs.
3. Uppdatera denna NEXT_SESSION.md med Step 6-utfall + Bundle-trigger-domen.
4. Om VM använts: deallocera och bekräfta `VM deallocated`.

---

*Uppdaterad 2026-06-11 efter F.9 Bundle-dataprep körd växande + Bundle-modellen datadrivet PARKERAD (FD.11).
Ersätter föregående NEXT_SESSION (F.9 Bundle-körning) — Bundle-modellen är inte längre denna sessions
uppgift; den är parkerad med återbesöks-trigger. Kritiska vägen ompekas till F.10 Step 6 + rimlighetsgrind
på Cluster+Site, som levererar färska affärselasticiteter på huvudsortimentet (IB.6) snabbare. Bundle lyfts
tillbaka OM rimlighetsgrinden visar att dess sjukhustjänster är tunna i väven.*
