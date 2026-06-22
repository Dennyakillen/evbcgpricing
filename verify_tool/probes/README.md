# verify_tool/probes — diagnostiska sonder

**Utvecklare:** Jens Palmö (Senior Business Analyst, Evidensia Djursjukvård AB), med AI-rådgivare.

Sonder är **diagnostiska verktyg**, åtskilda från `verify_tool`:s validerare. En validerare svarar
"stämmer utfallet mot facit/rimlighet?". En sond svarar "VAR i kedjan/koden går något fel, och varför?"
— den följer data eller kod steg för steg, mäter efter varje transformation, och testar flera hypoteser
parallellt i samma körning (metodiken: KÄRNPRINCIPER P.5 / LESSONS_BCG LB.76).

**Princip (LB.76, utvidgad 2026-06-22):** när en pipeline ELLER ett kodlager ger fel/tomt/oklart utan
att krascha — bygg en sond som instrumenterar en kopia, mäter population/tillstånd efter varje steg, och
testar hypoteser parallellt, i stället för reaktiv lager-för-lager-felsökning. Gäller även egen
infrastruktur (statiska sonder mot orkestrering/kontrakt), inte bara datapipelinen.

## Sonderna (sex)

### Datapipeline-sonder (FD.36, 2026-06-17)
- **`chain_population_probe.py`** — följer population (radantal/unika nycklar) genom en transformations-
  kedja och visar var rader tappas. För "output blev tomt men inget kraschade".
- **`model_chain_validator.py`** — validerar att en modellkedjas länkar (input→steg→output) hänger ihop.
- **`support_files_check.py`** — kontrollerar att stödfiler (config, mappningar) finns och är icke-tomma
  före en körning.

### Infrastruktur-/kontrakts-sonder (2026-06-22, tokenfria statiska)
- **`infrastructure_map.py`** — statisk AST-karta över orkestreringslagret: importgraf, kontrakts-
  mutationsspår (vilka RunStatus-metoder rör run-nivå vs fasnivå), avslutsvägs-asymmetri. Fann att alla
  tre modell-runners läckte run-nivån (finish_success anropade bara finish_phase, aldrig en run-stängare).
- **`contract_integrity.py`** — tre klasser: (A) livscykel — död kod + terminala tillstånd; (B)
  kontraktsdrift — fas-nycklar identiska tvärs default_pipeline/STORY/PHASE_RECEIPT; (C) svalda fel.
  Fann succeed() död, utelämnade PHASE_RECEIPT-nycklar, 24+ nakna except. Grunden för LB.77.
- **`after_chain_probe.py`** — kartlägger "Efter"-kedjan (run/-filerna): klassificerar produktionssteg
  vs valideringsverktyg, extraherar in/ut per steg, klassar input live vs fryst, bygger beroendekedjan
  med binär dom. Spec:en för run_after.py (FD.37) — noll gissning.

## Körning (global Python 3.11, sonderna är tokenfria)

```powershell
py -3.11 verify_tool\probes\infrastructure_map.py
py -3.11 verify_tool\probes\contract_integrity.py --root "C:\Projekt\BCG\orchestration" --lifecycle
py -3.11 verify_tool\probes\after_chain_probe.py --root "C:\Projekt\BCG\verify_tool\run"
```

De statiska sonderna kör ingen kod och kräver ingen Azure-token — de läser källkod (AST + mönster).

*Uppdaterad 2026-06-22: tre infrastruktur-sonder tillagda; sond-metodiken (LB.76) utvidgad till att
gälla egen infrastruktur/kontrakt, inte bara datapipeline.*
