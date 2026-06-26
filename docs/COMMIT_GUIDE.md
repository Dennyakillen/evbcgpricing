# Commit-guide — session 2026-06-26 valideringslager

> Följer din git-disciplin: status/remote/branch FÖRST, verifiera remote före commit,
> push vid mogen milstolpe. Allt nedan antar repo-roten `C:\Projekt\BCG`.

---

## Steg 0 — flytta filerna till rätt plats (om de ligger kvar i Downloads)

```powershell
cd C:\Projekt\BCG
$dl = "$env:USERPROFILE\Downloads"

# Verktyg -> verify_tool\
foreach ($f in "valve_map.py","conservation.py","window_coherence.py",
                "dry_run_full_pipeline.py","run_smoke_facit.py",
                "pipeline_contracts.py","prefilter_unpriced.py") {
    if (Test-Path "$dl\$f") { Move-Item "$dl\$f" ".\verify_tool\$f" -Force }
}

# Dokumentation -> docs\ (skapa om saknas)
if (-not (Test-Path .\docs)) { New-Item -ItemType Directory .\docs | Out-Null }
foreach ($f in "SESSION_2026-06-26_valideringslager.md","README_VALIDERING.md",
                "ARKITEKTUR_MOGNADSANALYS.md","PROMPT_hitta_validera_cementera.md",
                "TILLAGG_governing_docs.md") {
    if (Test-Path "$dl\$f") { Move-Item "$dl\$f" ".\docs\$f" -Force }
}
```

---

## Steg 1 — DISCIPLIN: verifiera var du står FÖRE något annat

```powershell
git status
git remote -v          # bekräfta att 'origin' pekar på rätt repo (Dennyakillen/evbcgpricing)
git branch             # bekräfta att du står på 'main'
git log --oneline -5   # matchar HEAD det STATE.md säger? (annars uppdatera STATE först)
```

**STOPP om:** remote inte är evbcgpricing, eller branch inte är main, eller HEAD inte matchar
STATE.md. Åtgärda innan du fortsätter (sessionsstartsprotokollet, KÄRNPRINCIPER §6.1).

---

## Steg 2 — FÖRST: fäst lärdomarna i governing docs (manuellt)

Innan du committar verktygen — klistra in blocken ur `docs\TILLAGG_governing_docs.md` i
respektive master-fil och sätt rätt LB/KÄRN-nummer:
- KÄRNPRINCIPER.md  (fyra nya principer)
- LESSONS_BCG.md    (tre nya LB)
- STATE.md          (verktygsinventarie-rad)
- NEXT_SESSION.md   (kö)

Detta görs FÖRST därför att din disciplin säger att lärdomar fästs före sessionsslut, inte
nämns i efterhand. TILLAGG-filen är råmaterialet; master-filerna är sanningen.

---

## Steg 3 — granska vad som faktiskt ändrats

```powershell
git add -A
git status             # läs listan: är allt väntat? något oväntat med?
git diff --cached --stat   # överblick: vilka filer, hur många rader
```

**Kontrollera särskilt:** att inga känsliga filer följer med (Excel-data, statusfiler med
resurs-ID). `frozen_facit_reference.json` och `conservation_snapshot.json` innehåller bara
aggregat (radantal/median) — ofarligt — men bekräfta. Om STATE.md är .gitignore:ad enligt din
not, se till att den inte råkar stageras.

---

## Steg 4 — commit (separata, läsbara commits — din branch-disciplin)

Hellre tre tydliga commits än en klump:

```powershell
# Commit 1: valideringslagrets verktyg
git add verify_tool\pipeline_contracts.py verify_tool\prefilter_unpriced.py `
        verify_tool\window_coherence.py verify_tool\dry_run_full_pipeline.py `
        verify_tool\run_smoke_facit.py verify_tool\conservation.py verify_tool\valve_map.py
git commit -m "Add validation layer around BCG engine (Phase Z): contracts, coherence gate, smoke test, valve map

Additive only, BCG core untouched. Boundary contracts for Step 6 (form/volume/
invariant, blocking), cross-family coherence gate before EFTER, offline frozen-facit
smoke test, and valve map quantifying intentional drop-off per valve (V1/V3 exact,
V2/V4 approx pending calibration). Verified: dry-run 24 OK/0 FAIL, coherence GO,
facit reference blessed (108979 rows / 15128 keys / median -0.4968)."

# Commit 2: dokumentation
git add docs\SESSION_2026-06-26_valideringslager.md docs\README_VALIDERING.md `
        docs\ARKITEKTUR_MOGNADSANALYS.md docs\PROMPT_hitta_validera_cementera.md
git commit -m "Doc: validation-layer session 2026-06-26 (what, why, open threads, reusable pattern)"

# Commit 3: governing docs (efter att du klistrat in tilläggen + satt nummer)
git add KÄRNPRINCIPER.md LESSONS_BCG.md STATE.md NEXT_SESSION.md
git commit -m "Lessons from validation session: validator fault-tolerance, approximation honesty, expected-vs-leak, fragile-correct-outcome (KÄRN + LB)"
```

---

## Steg 5 — push (mogen milstolpe nådd)

```powershell
git log --oneline -5   # sista koll: ser commit-historiken rätt ut?
git push origin main
```

Verifiera efteråt att push gick igenom (inga rejected/non-fast-forward). Om någon annan pushat
emellan: `git pull --rebase origin main`, lös ev. konflikt, push igen.

---

## Vad som INTE ska committas

- Genererade artefakter: `verify_tool\valve_map\*.xlsx`, `*.md` (tidsstämplade kartor),
  `workspace\validation_receipts\*` — de är output, inte källa. Lägg i .gitignore om de inte
  redan täcks.
- `probe_null_itemcode.py` är en engångssond — committa den gärna som dokumentation av HUR
  Natrium Catalyst-fyndet gjordes (probe-to-invariant-spåret), eller arkivera. Ditt val.
- Excel-källfiler (Final_Fallback, output_summary, Complete_Product_Data) — aldrig i git.

---

*Disciplinen är poängen: verifiera var du står, fäst lärdomar först, granska före commit,
push vid mogen milstolpe — inte ackumulerat.*
