# NEXT_SESSION_TEMPLATE — hur en NEXT_SESSION skrivs

**Syfte:** Definiera hur en `NEXT_SESSION.md` skapas. `NEXT_SESSION` svarar på *vad nästa session
ska göra* — kö, prioriteringar, konkret första leverans. Den ändras varje session.

**Skild från STATE.md:** `STATE.md` bär det stabila nuläget (resurs-ID, VM-status, roller, SHA — ändras
sällan). `NEXT_SESSION` bär det session-snabba (vad härnäst, i vilken ordning, varför). Olika ändringstakt
→ olika fil. NEXT_SESSION *pekar* på STATE för aktuella värden i stället för att upprepa dem.

**Avsikt:** AI:n ska kunna läsa STATE + NEXT_SESSION och omedelbart veta var projektet står och vad som
ska göras — utan att rekonstruera ur gissning.

---

## 1. Princip: pekare, inte upprepning

NEXT_SESSION ska vara **kort och hög-signal** (samma budget som alla laddade filer — se KÄRNPRINCIPER).
Upprepa inte resurs-ID, miljötabeller eller status som redan står i STATE — *peka* dit. Det som hör hemma
här är bara: dagens mål, kön, och de få snubbeltrådar som är akuta just nu.

---

## 2. Obligatoriska block

### Block 1 — Rollrad (1 rad)
```markdown
Du agerar som senior teknisk rådgivare för Jens Palmö (Senior Business Analyst).
Följ KÄRNPRINCIPER.md samt relevanta MASTER_*.md. Aktuellt nuläge i STATE.md.
```
*(Inget bolagsnamn — det bor i projektets README och i STATE, inte i rollraden.)*

### Block 2 — Läs detta först (pekare, inte innehåll)
```markdown
> Läs FÖRE start: STATE.md (nuläge), KÄRNPRINCIPER.md (router för dagens mål),
> samt [projektfiler relevanta för målet]. Slå upp dagens mål i KÄRNPRINCIPER-routern
> och aktivera de triggers som gäller innan första handling.
```

### Block 3 — Mål för sessionen (konkret leverans, inte "jobba med fas X")
```markdown
## Mål

### Primärt: <etapp> — <namn>
**Levererar:** <konkret fil/funktion/validering — vad som ska finnas efteråt>
**Verifieras med:** <kommando + förväntat utfall>
**Datakälla / berör:** <modul/vy/fil>
```

### Block 4 — Kö (prioriterad, lägst risk/högst värde först)
```markdown
## Kö (efter primärt mål)
1. <nästa sak> — <en rad varför / vilken risk>
2. <...>
```

### Block 5 — Akuta snubbeltrådar för just detta mål (pekare för resten)
```markdown
## Snubbeltrådar denna session
- <bara de 2-4 som är akuta för dagens mål>
- Resten: se STATE §7 och LESSONS_BCG (tier-a).
```

### Block 6 — Pre-flight (copy-paste-klart, bara det målet kräver)
```markdown
## Pre-flight
```powershell
cd "C:\Projekt\<mapp>"
.\.venv\Scripts\Activate.ps1
```
```powershell
git log --oneline -5
git status
```
Förväntat: senaste commit <SHA från STATE>, working tree clean.
<ev. token-renewal, env-verifiering — bara om målet rör Azure/DW>
```

---

## 3. Sessionsslut (compaction — maximera recall först, beskär mot precision sen)

Vid sessionsslut, kör i ordning (detta är compaction: destillera sessionen till nästa start utan att
tappa subtil men kritisk kontext):

```markdown
## Vid sessionsslut
- [ ] git status → clean; git log --oneline -3 → arbetet committat och pushat
- [ ] Inga zombieprocesser
- [ ] Fånga sessionens lärdomar BRETT (recall) → pröva sedan var mot KÄRNPRINCIPER §6.6:
      instans av befintlig princip → avslå; generell mekanism → MASTER/KÄRN; projektspecifik → LESSONS.
      Noll nya lärdomar är ofta rätt.
- [ ] Eskaleringskontroll: passerade någon lärdom (a) mekanism + (b) korsar projektgräns? → flagga till Jens.
- [ ] Ny term/strukturyta införd? → pröva mot KÄRNPRINCIPER kanoniska ordlista (drift-spärr).
- [ ] STATE.md uppdaterad: ny SHA, VM-status, ev. ändrade resurs-/roll-rader (med datum).
- [ ] NEXT_SESSION.md uppdaterad: nästa mål + kö + vilka router-triggers som gäller det målet.
```

> **Compaction-ordningen är medveten:** fånga allt relevant först (recall), beskär sedan superflöd
> (precision). Omvänd ordning tappar det subtila vars vikt visar sig först senare.

---

## 4. Kvalitetskrav på en färdig NEXT_SESSION

- [ ] Pekar på STATE för nuläge i stället för att upprepa det
- [ ] Mål är konkret leverans + verifieringskommando — inte "jobba med fas X"
- [ ] Kön är prioriterad (risk/värde-motiverad), inte en hög
- [ ] Pre-flight är copy-paste-klar och begränsad till vad målet kräver
- [ ] Kort — om den växer förbi en skärm, fråga vad som borde pekas på i stället för upprepas

---

## 5. Mall — komplett NEXT_SESSION.md (kopiera och fyll i)

```markdown
# NEXT_SESSION — <fas/etapp>

Du agerar som senior teknisk rådgivare för Jens Palmö (Senior Business Analyst).
Följ KÄRNPRINCIPER.md samt relevanta MASTER_*.md. Aktuellt nuläge i STATE.md.

> Läs FÖRE start: STATE.md, KÄRNPRINCIPER.md (slå upp dagens mål i routern), <projektfiler>.

## Mål
### Primärt: <etapp> — <namn>
**Levererar:** <konkret>
**Verifieras med:** <kommando → förväntat>
**Berör:** <modul/vy/fil>

## Kö
1. <nästa> — <varför/risk>
2. <...>

## Snubbeltrådar denna session
- <2-4 akuta för målet; resten → STATE §7 + LESSONS tier-a>

## Pre-flight
```powershell
cd "C:\Projekt\<mapp>"
git log --oneline -5
git status
```
Förväntat: commit <SHA>, clean.

## Vid sessionsslut
- [ ] committat + pushat; git status clean
- [ ] lärdomar fångade brett → §6.6-prövning → rätt fil (eller avslag)
- [ ] eskaleringskontroll (mekanism + korsar projektgräns → flagga)
- [ ] ny term → ordlist-prövning
- [ ] STATE uppdaterad (SHA, VM-status, datum)
- [ ] NEXT_SESSION uppdaterad (nästa mål + kö + router-triggers)
```

---

*Mall förvaltad av Jens Palmö (Senior Business Analyst). NEXT_SESSION är den session-snabba
färskvarufilen; STATE är den stabilare nulägesfilen. Båda uppdateras vid sessionsslut enligt
compaction-ordningen ovan.*
