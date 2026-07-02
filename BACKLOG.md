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

## BB.6 — Webapp snabb-kosmetik: extraction-plupp + frontend-ordning [återfångad ur FAS 20]
**Sedd:** 2026-06-23 (FAS 20, Jens egna ord: "lyck-fix" resp. "snyggare men inte avgörande"); fångad i fil 2026-07-02
**Kandidat:** Två små, uppmätta UI-fixar som medvetet sköts upp men aldrig fästes i dokumentation:
(a) **Extraction-fasen får grön plupp** när extraktionen bevisligen är klar — uppskjuten 2026-06-23
enbart för att cluster-runnern skrev maj-statusfilen just då (write-konflikt-risk, last-write-wins).
(b) **Frontend-ordning site → cluster → bundle** — UPPMÄTT trivial: renderordningen är STORY-dictens
insättningsordning i `story_config.py` (rad 41: "The order drives the rendering"), rör INTE
statusfil/default_pipeline/runner-matchning. Rent kosmetiskt blockbyte.
**Varför ej nu:** (a) väntar på att statusfilen är fri (cluster-maj-blockaren löst). (b) parkerades
medvetet till samma pass som period-medvetenheten (Leverans 2) — story_config ska röras EN gång,
inte två ("fixa ordningen nu och KPI:erna senare är att röra samma fil två gånger").
**Mognadsvillkor:** (a) cluster-maj stängd + statusfil vilande. (b) periodmedvetna-KPI-passet
(NEXT_SESSION/BLOB_MALSTRUKTUR) — ordningsbytet görs som del av det passet.
**Skulle ersätta/stärka:** FD.32-linsen (appen som förtroende-yta) — små ärlighets-/igenkännings-vinster.
**Källa:** FAS 20-sessionen (Jens inlägg + Select-String-mätning av story_config)
**Status:** VÄNTAR

## BB.7 — Webapp polish-paket (nivå C — ren polering, motorn först) [återfångad ur FAS 15/18/19/24]
**Sedd:** 2026-06-12→2026-06-26 (FAS 15 UX-genomgång, FAS 18/19 "nästa pass"-noteringar,
FAS 24-konsolideringens tredje nivå); fångad i fil 2026-07-02
**Kandidat:** Samlingspost för ren polering som INTE rör motorns sanning. Innehåll ur sessionerna:
- **Infoflik i appen** (FAS 19: "Infofliken noterar vi som nästa pass" — noterades aldrig).
- **FD.18** SEK-kostnadsvisning i körlogg + statusvy (indexrad finns, ingen sektion).
- **FD.23** export per steg + fylligare svenska loggtexter (indexrad finns, ingen sektion).
- **Lager 3 micro-UX** (FAS 15, ej fästa): färg sparsamt och BARA för status (grå/blå/grön/gul);
  "döda knappens artighet" — lås-ikon + cursor-signal FÖRE klick på gråade steg; kör-om-bekräftelse
  med konsekvensvarning. Designvillkor för Lager 3 (FD.19), inte valfria smaker.
**Varför ej nu:** Polering på en app vars motor (FAS A) ännu inte är slutverifierad — fel ordning
(FAS 24-nivålogiken). Lager 3-delarna bryter dessutom "read-only by construction" och är SIST per FD.19.
**Mognadsvillkor:** FAS A grön + periodmedvetna-KPI-passet klart. Lager 3-delarna dessutom: Lager 2 byggt.
**Skulle ersätta/stärka:** FD.18/19/23-indexraderna får verkligt innehåll; FD.32.
**Källa:** FAS 15 (UX-principer), FAS 18/19 (nästa-pass-noteringar), FAS 24 (trenivå-konsolidering)
**Status:** VÄNTAR

## BB.8 — Hosting för kollega: appen nåbar bortom 127.0.0.1 [återfångad ur FD.19-detaljblock]
**Sedd:** 2026-06-12 (FD.19-detaljtext i sessionsfil, aldrig infogad som sektion); fångad i fil 2026-07-02
**Kandidat:** Appen binder `127.0.0.1` — en kollega kan inte se den. "Kollega-vänlig dashboard"
(FD.19:s hela poäng) kräver nåbar värd: eget steg med IT-dimension (nät, ev. intern server, inte
publik IP per tenant-policy).
**Varför ej nu:** Fel ordning att exponera en app vars innehåll ännu inte stämmer — en förtroende-app
som visar fel siffror underminerar förtroendet (FAS 20-lärdomen). Kräver IT-dialog (FAS T-klass).
**Mognadsvillkor:** Appen visar sant per period + IT-samtal om intern värd.
**Skulle ersätta/stärka:** FD.19 (kollega-dashboarden blir faktiskt kollega-nåbar).
**Källa:** FD.19-detaljblock (sessionsfil 2026-06-12), FAS 20
**Status:** VÄNTAR

---

> **BB.9–BB.13 nedan — Claudes egna sidoförslag tvärs sessioner som aldrig plockades upp**
> (återfångade 2026-07-02). Var och en bär en **HYPOTES-rad**: en ärlig gissning om posten
> möjligen redan är delvis åtgärdad i kod/sessionsfil jag inte kunnat läsa. Korskörning mot
> bifogad dokumentation (BACKLOG/STATE/NEXT_SESSION/BLOB_MALSTRUKTUR/FUTURE_DEVELOPMENT/README)
> gav noll eller partiell träff — mät i kod före du litar på att posten är öppen. "Mät, gissa inte"
> tillämpad på mina egna förslag.
>
> **Prövning 2026-07-02:** samtliga HYPOTES-rader mätta mot källkod på disk (runners, azure_vm,
> blob, app) i granskningssessionen — se **MÄTT**-rad per post. BB.12 kunde ej mätas fullt
> (story_config ej i kontext) och bär kvar sitt verifieringskommando.

## BB.9 — `fetch_all_outputs`: tar + enkel-scp i stället för per-fil-scp [BEVISAD — mogen, ej ren väntan]
**Sedd:** 2026-06-24/25 (FAS 21, bevisad live); fångad i fil 2026-07-02
**Kandidat:** Runnernas output-hämtning scp:ar en fil per KEY (4181 individuella överföringar) genom
tunneln. Bytet till ett `tar czf` på VM:en + EN scp är dramatiskt snabbare OCH immunt mot en
encoding-bugg. **Bevis (FAS 21):** per-fil-scp malde 11+ min och failade ändå på svenska filnamn
(dubbel-UTF-8 → "No such file"); tar-varianten hämtade 190 MB på 10 sek i en överföring, filnamn
bytebevarade. **Horisontell skuld:** `run_cluster/site/bundle` är copy-adapt — bristen finns
nästan säkert i alla tre (jfr BB.13).
**Varför ej nu (svag motivering — nästan mogen):** Inte "väntar på villkor" — den är bevisad och redo.
Ligger i backlogg bara för att den inte hann fästas; bör egentligen till FD/LESSONS som mogen post.
**Mognadsvillkor:** Ingen äkta gate — nästa gång en runner rörs, eller ett dedikerat robusthetspass.
**HYPOTES (kanske delvis stängd):** Sannolikt EJ åtgärd — noll träff på "fetch_all_outputs"/"tar czf"
i bifogat. Men FAS 21 producerade LB.78-81 + tools; verifiera att tar-fixen inte redan committades
som patch (`grep -rn "tar czf\|fetch_all_outputs" orchestration\`).
**MÄTT 2026-07-02 (källkod på disk):** EJ implementerad — `tar`=0 träffar i alla tre runners;
per-fil-loopen kvar (`run_cluster_model.py:385 for rf in remote_files:` → `scp_from_vm` per fil;
3 anropsplatser per runner, symmetriskt = horisontell skuld bekräftad). Delvis MILDRAD:
`azure_vm.scp_from_vm` fick keepalive + 3-retry (B-fix 2026-06-24) — mindre tunnel-känslig, men
4181-överföringsproblemet och per-fil-encodingexponeringen kvarstår. Hypotesen stängd: posten är öppen.
**Skulle ersätta/stärka:** `azure_vm.py`/runnernas output-hämtning; LB-serien (output-arkitektur).
**Källa:** FAS 21 (Claude-observation P.4, bevisad i skarpt läge)
**Status:** MOGEN — flyttas till FD/robusthetspass vid nästa FD-redigering. **SPÄRR:** byggs INTE
före cluster-maj-relaunchen är grön (en variabel i taget — relaunchen ska bevisa config-fixen,
inte config + ny hämtningsväg samtidigt).

## BB.10 — `ssh_launch_selftest` testar realistisk sekvens, inte launch i isolering [snabbfångad]
**Sedd:** 2026-06-24 (FAS 21); fångad i fil 2026-07-02
**Kandidat:** Selftesten kör launch i vakuum → gav PASS trots att skarp körning dog vid launch efter
en serie SSH-anrop i tät följd (tunnel-blink). Om selftesten körde preflight-liknande serie + launch
skulle den fångat felet FÖRE en 50-min-körning. Skärper AZ.7 till att gälla launch fullt ut.
**Varför ej nu:** Sond 6 (`after_chain_probe.py`) byggdes och tar en annan roll (efter-kedjans ordning,
FUTURE_DEVELOPMENT rad 698); denna specifika selftest-skärpning är separat och obevisad ännu.
**Mognadsvillkor:** Nästa robusthetspass på launch-vägen (ihop med BB.9, samma delade `azure_vm.py`).
**HYPOTES (kanske delvis stängd):** DELVIS — sond 6 finns men i annan roll. Selftest-skärpningen
sannolikt ej gjord. Verifiera vad `ssh_launch_selftest` faktiskt kör i dag före bygge.
**MÄTT 2026-07-02 (azure_vm.py:241–257):** Selftesten kör fortfarande `sleep 90` i vakuum —
skärpningen obyggd. MEN skarpa launch-vägen bär A2-fixen (2026-06-24): `ssh_launch_detached`
pgrep-verifierar + relaunchar en gång, vilket täcker just halv-launch-luckan i produktion.
Kvarvarande värde: selftesten som FÖRE-körning-grind är fortfarande naiv. Hypotesen stängd: delvis mildrad.
**Skulle ersätta/stärka:** `azure_vm.py:ssh_launch_selftest`; AZ.7-tillämpning.
**Källa:** FAS 21 (Claude-rekommendation, lager 3)
**Status:** VÄNTAR

## BB.11 — Blob `MANIFEST.json` per körning (självdokumenterande output) [snabbfångad]
**Sedd:** 2026-06-22 (FAS 18); fångad i fil 2026-07-02
**Kandidat:** Bygg 2 laddar upp ALLA filer oavsett storlek (medvetet val). En `MANIFEST.json` per
körning i Blob som listar uppladdade filer + storlek + slutprodukt-vs-mellandata låter läs-sidan av
syfte B (nästa familj läser föregående output) veta vad som är värt att läsa utan att gissa.
**Varför ej nu:** Hänger på Blob-strukturen (FD.33/BLOB_MALSTRUKTUR) — manifestets sökvägar måste
matcha den slutliga container-strukturen, annars skrivs det om vid migreringen.
**Mognadsvillkor:** Blob-målstrukturen (FD.33) beslutad/påbörjad — manifestet byggs mot den.
**HYPOTES (kanske delvis stängd):** Sannolikt EJ — noll träff på "MANIFEST.json" i bifogat.
BLOB_MALSTRUKTUR nämner status-filer men inte per-körnings-manifest. Verifiera i Blob/blob.py.
**MÄTT 2026-07-02 (blob.py på disk):** 0 träffar på "manifest" — EJ byggd. Hypotesen stängd: posten öppen.
**Beroende-not:** FD.33 kräver i sin tur att de två Blob-designerna förenas först
(BLOB_MALSTRUKTUR familj-yttre vs FD.28 BCG-prefix) — BB.11 ligger alltså TVÅ steg nedströms.
**Skulle ersätta/stärka:** FD.33 (Blob-struktur) + syfte B:s läs-sida.
**Källa:** FAS 18 (Claude-rekommendation punkt 5)
**Status:** VÄNTAR

## BB.12 — Hjälte-KPI per fas: en huvudtråd + 2–3 stödjande [snabbfångad, front end]
**Sedd:** 2026-06-12 (FAS 15); fångad i fil 2026-07-02
**Kandidat:** Designregel för KPI-korten mot "statistik-tapet": varje fas har EN hjälte-KPI (bär
storyn, nästan alltid en facit→nu-rörelse) + 2–3 stödjande i kontext man kan öppna. Enades om men
fästes aldrig som regel. Nära FD.32 (rimlighet/liv-linsen) men den *specifika* en-hjälte-regeln saknas.
**Varför ej nu:** Del av periodmedvetna-KPI-passet (samma story_config-rörelse som BB.6b) — görs där,
inte isolerat.
**Mognadsvillkor:** Periodmedvetna-KPI-passet (NEXT_SESSION Leverans 2).
**HYPOTES (kanske delvis stängd):** Möjligen delvis levd i praktiken — FUNNEL-modellen (FAS 18) har
redan lager-struktur. Men "en hjälte-KPI"-regeln som explicit designval: noll träff. Verifiera i
story_config/dashboard.html om FUNNEL redan begränsar till en huvud-KPI per fas.
**MÄTT 2026-07-02:** story_config.py ej läsbar i granskningssessionen — hypotesen KVARSTÅR öppen.
Verifiera före KPI-passet: `Select-String orchestration\webapp\story_config.py -Pattern "FUNNEL" -Context 2,6`.
**Skulle ersätta/stärka:** FD.32 + FUNNEL-renderingen (story_config).
**Källa:** FAS 15 (Claude UX-utmaning)
**Status:** VÄNTAR

## BB.13 — Horisontell validering som metod [KÄRN-kandidat, ej BCG-intern — väv-kandidat]
**Sedd:** 2026-06-24/25 (FAS 21, flaggad KÄRN-kandidat två gånger); fångad i fil 2026-07-02
**Kandidat:** Sökstrategin: när en asymmetri/brist hittas i cluster, finns den nästan säkert
identiskt i site + bundle (de är copy-adapt, FD.34). En fix i DELAD infrastruktur (`azure_vm.py`)
träffar alla tre; en brist i en runner bör omedelbart granskas i de andra två. Detta är en *metod*
som fångar hela buggklasser (BB.9 och launch-asymmetrin är båda instanser), värd mer än en enskild
FD-post. **Väv-not:** troligen generell (gäller alla copy-adapt-familjer, inte bara BCG) → vid
väv-prövning befordras den sannolikt till bibliotekets KÄRN/MASTER, inte kvar som BB.
**Varför ej nu:** Princip-fästning hör i sessionshygien/väv-session, inte mitt i FAS A. Prövas mot
befintliga principer (P.4? egen?) innan den fästs — undvik lärdoms-inflation (§6.6).
**Mognadsvillkor:** Väv-/sessionshygien-pass; prövad mot KÄRNPRINCIPER §6.6-nivåerna.
**HYPOTES (kanske delvis stängd):** Sannolikt EJ fäst — noll träff på "horisontell" i bifogat.
FAS 21 flaggade den som kandidat men fäste den inte ("fäster ingenting nu"). Verifiera i
KÄRNPRINCIPER/MANIFEST-triggers om den smugit in under annat namn.
**MÄTT 2026-07-02:** BB.9-mätningen bekräftade metodens prediktion i praktiken (identisk brist i
alla tre runners, symmetrisk anropsstruktur). Ingen befintlig princip-ägare känd; §6.6-prövningen
vid väv-sessionen står kvar som gate.
**Skulle ersätta/stärka:** KÄRNPRINCIPER §6/§8 (sökstrategi) eller MASTER_VALIDATION; MANIFEST trigger 3.
**Källa:** FAS 21 (Claude-metod, flaggad KÄRN-kandidat)
**Status:** VÄNTAR

---

> **Medvetet EJ backlogg (för disciplinens skull):**
> - **Minnes-/governance-skuld (~12 poster avklarat historiskt tillstånd)** — hör i sessionshygien
>   (flytta till LESSONS_BCG/STATE per KÄRNPRINCIPER §4.7), inte här. Den *väntar inte* på ett villkor;
>   den *ska göras*. Backloggen är inte en att-göra-lista (annars blir den kyrkogård).
> - **MBAS0703-elasticitetsutliggare** (Clinics, -320,609) — data-kvalitets-*åtgärd* före affärsbruk,
>   hör i NEXT_SESSION/ROADMAP, inte backlogg. Väntar på analys, inte på verktyg/PoC.
> - **STÄNGD 2026-07-01:** ~~`run_after.py` / `run_data.py` saknar `resolve_window_end`~~ — löst i
>   commit `6cda4da` (`orchestration/shared/window.py` + båda runners patchade: `--end` default None
>   → auto-resolve senast stängda månad, explicit `--end` vinner). Kvar av raden: inget.
> - **FD.22-indexraden är STALE** — live-tickande körtid är BYGGD (dashboard.html, FAS 18) men
>   indexet säger "Önskad". Dok-hygien: rätta indexraden, inte en backlogg-post.
> - **Engelsk frontend-översättning (FAS 19-beslutet)** — tre engelska appfiler var "ej committade"
>   vid sessionsslut 2026-06-23. *Verifieringspunkt* (`git log` + grep dashboard.html efter svenska
>   strängar), inte backlogg — väntar inte på villkor, ska kontrolleras.
>   **Delmätt 2026-07-02:** `app.py` (på disk) bär 16 å/ä/ö-rader men träffarna är docstrings/
>   kommentarer (husstil), ej UI-strängar. Kvar att verifiera: `dashboard.html` —
>   `Select-String orchestration\webapp\templates\dashboard.html -Pattern "[åäö]"` + `git log --oneline -3 -- orchestration/webapp/`.
> - **Atomära skrivningar (P.9) i de långa stegen** — **KORRIGERAD 2026-07-02:** delvis plockad, inte
>   orörd. `io_safe.py` + `idempotens_audit.py` är byggda och committade (`cdd02d3`: "164→~3-4
>   relevanta skrivningar, P.9-triage"; verifierat i `git ls-files`). Kvarvarande skuld = koppla
>   `io_safe` i de ~3–4 utpekade skrivningarna — hör i robusthetspasset (ihop med BB.9/BB.10).
> - **`dry_run_pipeline.py` som BLOCKERANDE preflight-grind** — verktyget finns (19 kontroller, STATE
>   rad 164) men körs manuellt, ej wired som spärr. Överlappar det öppna itemet "wire validation into
>   blocking preflight" (NEXT_SESSION/FAS 24) — hör där som aktiv uppgift, inte backlogg. Notera:
>   BLOB_MALSTRUKTUR flaggar att de 19 kontrollerna måste uppdateras till nya Blob-strukturen först.
>   **Beroende (mätt 2026-07-01):** dry_run:s kontroll 4 hävdar `EXPECTED_KEYS==4180/6624/125` medan
>   `run_cluster_model.py:102` satt `None` (Leverans 2-fixen) — grinden FELAR strukturellt idag och
>   måste rättas ("härled, hävda inte") INNAN den kan wiras som spärr. En grind som alltid felar
>   blockerar allt.
> - **NY verifierings-/beslutspunkt (E.8, mätt 2026-07-01):** `regenerate_transaction_parquet_chunked.py`
>   finns på disk i Business_Analytics men är OTRACKAD (endast `_v2.py` i `git ls-files`) —
>   `patch_window_resolve` mätte och lämnade `REGEN_SCRIPT` orörd. Beslut krävs: committa v1 (E.8)
>   ELLER migrera medvetet till `_v2` + arkivera v1. OBS: commit-meddelandet `6cda4da` överlovar
>   ("REGEN repointed to _v2") — ompekningen utfördes EJ; denna rad är den ärliga sanningen.
>
> Noterat så de inte återupptäcks och fångas av misstag som backlogg-poster.
>
> **Proveniens BB.6–BB.13 (varför de återfångas 2026-07-02):** FD.16–25 finns endast som en-raders
> indexrader i FUTURE_DEVELOPMENT.md; webapp-detaljerna + Claudes egna sidoförslag levde i
> sessionschattar/AI-minne, och minnet beskars (KÄRNPRINCIPER §4.7). **BB.6–8** = webapp-kosmetik
> (FAS 15–24). **BB.9–13** = Claudes egna rekommendationer som aldrig plockades upp; var och en bär
> en HYPOTES-rad då de kan vara delvis åtgärdade i kod jag ej kunnat läsa. **Två poster (BB.9, BB.13)
> är egentligen mogna, ej väntande** — de har bevis/metodvärde och bör vid nästa prövning befordras
> till FD/LESSONS resp. KÄRN/MASTER snarare än ligga kvar som BB.
>
> **Prövningslogg:** 2026-07-02 — BB.1–5 diffade identiska mot committad version (`7becbd7`), ren
> utökning. HYPOTES-raderna BB.9/10/11/13 stängda med källkodsmätning (BB.12 kvarstår, story_config
> ej läsbar). BB.9 → MOGEN med bygg-spärr till efter cluster-maj-relaunch. EJ-listan: en post STÄNGD
> (`6cda4da`), en KORRIGERAD (P.9/`cdd02d3`), en delmätt (frontend-språk), två beroenden tillagda
> (dry_run EXPECTED-fix före wiring; FD.33-designförening före BB.11), en ny E.8-beslutspunkt (regen v1/v2).
