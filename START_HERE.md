# START HERE — var börjar jag?

Du har öppnat ett system som **replikerar och kör BCG:s priselasticitetsmodell
på Evidensias växande data** — i en miljö Evidensia själv äger och förvaltar,
oberoende av BCG:s hårdvara och leveranstakt.

Det mesta du undrar finns redan dokumenterat. Den här sidan är bara kartan dit.

---

## Vill du… → läs

| Vill du… | Läs |
|---|---|
| …köra modellen på ny data, end-to-end? | `DRIFT.md` (operativ körhandbok) |
| …förstå vad systemet är och varför det är trovärdigt? | `README.md` (arkitektur) |
| …veta var projektet står just nu (resurser, VM, senaste körning)? | `STATE.md` (färskvara) |
| …veta vad som är säkert vs osäkert/fruset? | `docs/governance/LOCKED_ASSUMPTIONS.md` |
| …se vägen från replikering till drift? | `ROADMAP.md` |
| …förstå tekniska val och fällor vi lärt oss? | `docs/knowledge/LESSONS_BCG.md` |
| …se analytiska insikter om modellen och datan? | `docs/knowledge/INSIGHTS_BCG.md` |
| …se vad som planeras och vad som är medvetet uppskjutet? | `docs/governance/FUTURE_DEVELOPMENT.md` |
| …köra modellen steg för steg (operativ playbook)? | `docs/governance/BCG_PRICING_PLAYBOOK.md` |
| …förstå Azure-orkestreringen (motorn)? | `orchestration/README.md` |

---

## Kärnan i en mening

Modellen är **bit-för-bit-validerad mot BCG** på det frusna fönstret (vi bevisar
att vi förstår och äger metoden), **körs på växande data** (själva produkten —
färska elasticiteter), och **allt är versionhanterat**. Replikeringen är grunden;
drift på färsk data är produkten.

## Tre saker en ny förvaltare bör veta direkt

1. **Det mesta hindret löstes genom att lita på källan, inte anteckningarna.**
   Originalkoden (`BCG_orginal_V2_New`) är facit — våra anteckningar har haft fel
   oftare än BCG:s kod. Mät, gissa inte (`README.md`, arbetsprinciper).

2. **En dokumenterad andel av utfallet vilar på frusna 2025-värden** (väv-vikter,
   steg-5-routning, bundle-gren). Kärnsignalen — elasticiteterna som styr
   prissättningen — är färsk. Se `LOCKED_ASSUMPTIONS.md` (LF.9) för vad som är
   fruset och i vilken ordning det tinas.

3. **Tunga modellsteg körs på en Azure-VM; Excel-stegen körs lokalt** (de kräver
   Windows/Excel-COM och kan inte köras i molnet). Före varje körning:
   `py -3.11 orchestration\dry_run_pipeline.py` bekräftar att alla rör pekar rätt.

---

*Utvecklare: Jens Palmö (Senior Business Analyst). Detta är ingångskartan — den
pekar på dokumentationen, ersätter den inte. När en fil flyttas, uppdatera raden här.*
