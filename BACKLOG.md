# BACKLOG — BCG-specifika förbättringskandidater (mogna senare)

> **Vad detta är:** best practice eller förbättring observerad *inom BCG* men ännu inte mogen att
> införa — väntar på verktyg, tid eller PoC. Detta är BCG:s egen fångstyta; den tvärgående,
> projektöverskridande backloggen bor i biblioteket (`Master-Bibliotek/BACKLOG.md`, `B.*`-serien).
>
> **Vad detta INTE är:** nutida lärdomar (→ KÄRNPRINCIPER §7 / LESSONS_BCG) eller att-göra för aktuell
> fas (→ NEXT_SESSION.md / ROADMAP). Här bor bara det som medvetet *väntar* på ett objektivt villkor.
>
> **ID-rymd (`BB.*`) — divergensvakt:** BCG-poster numreras `BB.N`, aldrig `B.N`. Bibliotekets backlogg
> äger `B.*`. Skilda rymder gör att de kan **vävas ihop utan ID-krock** i en dedikerad väv-session
> (VAKTEN trigger 3 / L.38-klassen — samma princip som skyddar `LB.*` mot `MASTER_*`).
>
> **Vävning med biblioteket (egen session):** vid väv-prövning avgörs per post — en `BB`-post som visar
> sig generell (gäller fler projekt) *befordras* till bibliotekets `B.*` (uppflyttning = MASTER_GIT §3,
> två commits); en som är äkta BCG-intern stannar här. Flera poster nedan delar bibliotekets
> Claude-Code-beroende (jfr `B.1`/`B.5`/`B.9`) — de väver troligen rent mot varandra.
>
> **Mognadsprövning** (sessionsslut/kvartal, MASTER_ORCHESTRATION §5b): VÄNTAR→MOGEN (villkor uppfyllt,
> flytta till rätt ägare) · VÄNTAR→DÖD (visade sig fel, arkivera additivt, radera ej — §4.7) · annars
> orörd. Antal poster är inget mått; en backlog som inte krymper vid prövning växer mot brus.
>
> **Developer:** Jens Palmö (Senior Business Analyst)

---

## BB.1 — Probe-konsolidering över fyra verktygsgenerationer
**Sedd:** 2026-07-01, arkitektur-anslutning (STATE §5 visar 6 sonder i `verify_tool/probes/`)
**Kandidat:** Konsolidera den diagnostiska sond-floran — `chain_population`, `model_chain_validator`,
`support_files_check`, `infrastructure_map`, `contract_integrity`, `after_chain_probe` + äldre generationer
— till en sammanhållen svit med tydlig rollindelning mot `all_chain_validator.py`. Idag har verktygen
vuxit reaktivt över fyra generationer utan att den äldre städats.
**Varför ej nu:** Sonderna används aktivt och är billiga (statiska, tokenfria). Refaktorera diagnostik
*mitt i* en pågående motor-validering (FAS A) riskerar att dölja regressioner. P.5-principen säger bygg
sonden när du behöver den — konsolidering är en separat, senare rörelse.
**Mognadsvillkor:** FAS A grön (motor + `run_after.py` validerade) OCH minst en full end-to-end-körning
efter det — då är motorn stabil nog att röra dess diagnostiklager.
**Skulle ersätta/stärka:** MASTER_VALIDATION §5 (additivt valideringslager) — gör sviten överblickbar
i stället för generationsspretig. Rollrelationen sond ↔ `all_chain_validator.py` reds ut här.
**Källa:** Egen observation (STATE §5, minnesnoterad probe-sprawl)
**Status:** VÄNTAR

## BB.2 — MASTER_AZURE 386-raders merge (BCG-rik vs bibliotek) [Claude-Code-beroende]
**Sedd:** 2026-07-01, arkitektur-anslutning (känd divergens, MANIFEST trigger 3)
**Kandidat:** BCG:s `MASTER_AZURE.md` bär 386 unika rader som är rikare än bibliotekets version. Slå
ihop de rikare raderna *in i* bibliotekets master (rätt ägare, §5), låt BCG sedan referera — eliminerar
en känd, medvetet parkerad skugg-kopia/divergens.
**Varför ej nu:** Filen är dubbel-kodad (UTF-8→CP1252→UTF-8-mojikake-risk, LB.86-klassen). En byte-kritisk
merge kräver filsystemsåtkomst och skript-baserad skrivning (UTF-8 utan BOM), inte klipp-och-klistra i en
webbsession. Encoding-mätningen måste ske på byte-sanning (`git hash-object`), inte via PowerShell-pipe.
**Mognadsvillkor:** Claude Code aktiverat (filsystemsåtkomst + skriptbar byte-verifiering).
**Skulle ersätta/stärka:** MASTER_GIT §5 (ägarregeln) + MANIFEST trigger 3 — stänger en namngiven divergens.
**Källa:** Egen observation (minnesnoterad, MANIFEST trigger 3)
**Status:** VÄNTAR

## BB.3 — Bibliotekstriage ~80 filer → Master-Bibliotek [Claude-Code-beroende, väv-kandidat]
**Sedd:** 2026-07-01, arkitektur-anslutning
**Kandidat:** ~80 filer i det gamla `Bibliotek` ska granskas och migreras till `Master-Bibliotek`
(behåll levande, arkivera dött additivt). Mekanisk mängd som kräver filsystemsåtkomst.
**Varför ej nu:** Claude Code ej autentiserat (STATE: väntar IT). Manuell triage av 80 filer i en
webbsession vore ineffektivt och felkänsligt.
**Mognadsvillkor:** Claude Code aktiverat.
**Skulle ersätta/stärka:** Oklart per fil tills granskad. **Väv-not:** detta är troligen inte BCG-internt
utan en biblioteks-koncern — vid vävning befordras posten sannolikt till bibliotekets `B.*` snarare än
stannar som `BB`. Fångad här så den inte tappas; ägarskapet avgörs vid väv-prövning.
**Källa:** Egen observation (minnesnoterad bibliotekstriage)
**Status:** VÄNTAR

## BB.4 — Städa död kod: `succeed()` efter finalize [snabbfångad]
**Sedd:** 2026-07-01, arkitektur-anslutning (STATE §5: "succeed() föråldrad (städas)")
**Kandidat:** `RunStatus.succeed()` är föråldrad sedan `finalize()` härleder run-nivån ur faserna
(heartbeat-spöket dött, LB.59). Ta bort den döda vägen så statusmodellen har *en* sanning.
**Varför ej nu:** Ta inte bort den gamla vägen förrän ersättaren (`finalize()`) är bevisad i en skarp
produktionskörning — inte bara i syntetisk statusfil. Att städa för tidigt tar bort fallback innan den nya
logiken är stridstestad.
**Mognadsvillkor:** `finalize()` verifierad i minst en skarp end-to-end-körning (ej syntetisk).
**Skulle ersätta/stärka:** Statusmodellen (run_id = datafönster) — en väg, inte två.
**Källa:** STATE §5 / §5-tabellen
**Status:** VÄNTAR

## BB.5 — `delivery_probe` EXPECTED-kalibrering [snabbfångad]
**Sedd:** 2026-07-01, arkitektur-anslutning
**Kandidat:** `delivery_probe` (az-CLI-baserad, offline-testläge) behöver kalibreras mot en verklig
leverans-körnings faktiska EXPECTED-värden för att bli en skarp grind i stället för en placeholder.
**Varför ej nu:** Det finns ännu ingen skarp leverans-körning att kalibrera EXPECTED mot. Att sätta
värden på gissning motsäger "mät, gissa inte" (§8.4) — grinden vore falsk precision.
**Mognadsvillkor:** En första skarp leverans-körning genomförd (facit för EXPECTED existerar).
**Skulle ersätta/stärka:** Probe-arkitekturens lager 3 (delivery_probe) + MASTER_VALIDATION §4
(output-rimlighet när facit finns).
**Källa:** Egen observation (minnesnoterad probe-arkitektur, lager 3)
**Status:** VÄNTAR

---

> **Medvetet EJ backlogg (för disciplinens skull):**
> - **Minnes-/governance-skuld (~12 poster avklarat historiskt tillstånd)** — hör i sessionshygien
>   (flytta till LESSONS_BCG/STATE per KÄRNPRINCIPER §4.7), inte här. Den *väntar inte* på ett villkor;
>   den *ska göras*. Backloggen är inte en att-göra-lista (annars blir den kyrkogård).
> - **MBAS0703-elasticitetsutliggare** (Clinics, -320,609) — data-kvalitets-*åtgärd* före affärsbruk,
>   hör i NEXT_SESSION/ROADMAP, inte backlogg. Väntar på analys, inte på verktyg/PoC.
> - **`run_after.py` / `run_data.py` saknar `resolve_window_end`** — öppen *defekt* (tyst datumlås-risk),
>   inte en mogna-senare-kandidat. Hör i NEXT_SESSION som aktiv bugg.
>
> Noterat så de inte återupptäcks och fångas av misstag som backlogg-poster.
