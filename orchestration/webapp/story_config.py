"""
story_config.py -- Facit-referens + berättartexter för Phase Z-dashboarden
===========================================================================
Statisk konfiguration, medvetet INTE i Blob: BCG:s frysta facit ändras
aldrig, alltså är referensvärden konfiguration -- inte data som hämtas.
Dashboarden väver ihop detta (det frysta) med statusfilen (det levande).

ÄRLIGHETSREGEL (honesty contract): varje tal har en källkommentar.
None betyder "ännu ej verifierat mot kvitto" och renderas som "[fyll i]"
i gränssnittet -- ALDRIG ett påhittat värde. Fyll på här, en plats, när
fler facit-tal verifieras ur valideringskvittona.

STRUKTUR (FD.21 -- frontend speglar flödet): varje fas bär ett 'group'
som placerar den i berättelsen Före (bränsle) -> Motor (Azure) -> Efter
(lokal efterbearbetning + matning). Dashboarden grupperar faserna så att
en kollega ser HELHETEN: var datan kommer in, var den räknas, var den blir
affärsbeslut. Metaforen är Jens egen ("Före-Motor-Efter").

HUR-FÄLT (FD.27): varje fas bär 'how_sv' -- en kollega-vänlig mening om
HUR steget körs (lokalt/VM, vad som triggar det, vilket kommando). Det
förklarar sömmen lokalt<->moln i stället för att dölja den.

DATA-INFO (FD): varje fas kan bära 'data' -- vad steget faktiskt producerar
i konkreta tal (rader, koder, storlek), från färdiga filer/kvitton. Ingen
ny beräkning; avlästa värden. None -> visas ej.

Nycklarna MASTE matcha statuskontraktets phase keys (run_status.py):
extraction, cluster_model, site_model, site_step5, step6, build_r12.

FRAMTID (FD): när runnern skriver KPI:er strukturerat i statusfilen
(metrics-fält i kontraktet, nästa kontraktsversion) försvinner behovet
av "now"-värden här -- då blir denna fil enbart facit + texter.

Utvecklare: Jens Palmö (Senior Business Analyst)
Författare: Claude-rådgivare, Phase Z-session (växer fram iterativt).
"""

# Grupper i berättelsen (FD.21). Ordningen styr renderingen.
GROUPS = {
    "before": {
        "title_sv": "Före  --  bränslet in",
        "blurb_sv": "Färsk transaktionsdata hämtas och tankas till Azure. "
                    "Detta sker lokalt eftersom datalagret (DW) bara nås på kontorsnät/VPN.",
    },
    "engine": {
        "title_sv": "Motor  --  modellen räknar (Azure)",
        "blurb_sv": "De tunga elasticitetsberäkningarna körs på Azure-VM:en -- "
                    "där finns minnet och kraften. Detta är den bevisade motorn.",
    },
    "after": {
        "title_sv": "Efter  --  resultat och affärssignal",
        "blurb_sv": "Modelloutputen efterbearbetas lokalt (Excel/COM, Windows) och "
                    "vävs till EN elasticitet per produkt -- talet som styr prissättningen.",
    },
}

# Varje KPI: label, facit (str|None), now (str|None), delta (str|None),
# dir: "pos" (grön uppåt-pil), "neg" (röd nedåt), "neut" (grå =).
STORY = {
    "extraction": {
        "group": "before",
        "title_sv": "Extraktion (dataprep, lokalt)",
        "story": "BCG byggde på data till juni 2025. Vi ser nu till april 2026 -- tio månader till.",
        "why": "Hämtar färsk transaktionsdata och bygger vecko-CSV:n som modellen tränar på. "
               "Körs lokalt eftersom datalagret (DW) bara nås på kontorsnät/VPN -- inte från Azure-VM:en.",
        "use": "Producerar bränslet: CSV och parquet som modellstegen läser.",
        "without": "Modellen kör på fryst data -- nya månader saknas tyst (G7-lärdomen).",
        "how_sv": "Ett kommando lokalt: run_data.py regenererar parqueten ur DW (kräver VPN), "
                  "kör dataprep, och tankar parqueten till Azure Blob. ~2 min för uppladdningen.",
        "data": "27,4 M transaktionsrader -> vecko-CSV:n + parquet (1 091 MB)",
        "kpis": [
            {"label": "Datafönster", "facit": "jun 2025", "now": "apr 2026", "delta": "+10 mån", "dir": "pos"},
            {"label": "Transaktionsrader", "facit": None, "now": "27,4 M", "delta": None, "dir": "pos"},
            {"label": "Storlek", "facit": None, "now": "1 091 MB", "delta": None, "dir": "pos"},
        ],
    },
    "cluster_model": {
        "group": "engine",
        "title_sv": "Cluster-modell steg 1-4 (VM)",
        "story": "Med mer data passerar fler elasticitetsskattningar signifikanströskeln -- modellen blir att lita på.",
        "why": "OLS-elasticitet per produkt x kluster, Ray-parallelliserad på VM:en. "
               "Tung beräkning som kräver VM:ens minne -- därför Azure, inte laptopen.",
        "use": "Ger klusternivå-elasticiteter -- ett av lagren i Step 6-väven.",
        "without": "Step 6 saknar klusternivån i fallback-väven.",
        "how_sv": "Körs på Azure-VM:en (bcg-poc-vm) via run_cluster_model.py. Startar VM:en, "
                  "kör stegen på Linux, och deallokerar när klart så kostnaden stoppas.",
        "data": "3 812 produkt x kluster-grupper (alla, även icke-signifikanta)",
        "kpis": [
            {"label": "Signifikansandel", "facit": "33,4 %", "now": "45,2 %", "delta": "+11,8 pp", "dir": "pos"},
        ],
    },
    "site_model": {
        "group": "engine",
        "title_sv": "Site-modell steg 1-4 (VM)",
        "story": "Motorn bevisad: orchestrator-körningen är bit-för-bit identisk med facit på samma data.",
        "why": "OLS-elasticitet per produkt x site -- modellens finaste granularitet. "
               "Validerad bit-för-bit mot facit-körningen 2026-06-09.",
        "use": "Primär elasticitetssignal -- matar Step 6 och R12-matningen.",
        "without": "Ingen sitenivå-elasticitet; väven faller tillbaka på grövre nivåer.",
        "how_sv": "Körs på Azure-VM:en via run_site_model.py -- samma motor som cluster. "
                  "Rapporterar sin fas live till statusfilen medan den kör.",
        "data": "6 624 unika KEY (produkt x site), 0,6 MB output_summary",
        "kpis": [
            {"label": "Unika KEY", "facit": "6 624", "now": "6 624", "delta": "=facit", "dir": "neut"},
            {"label": "Korrelation", "facit": "1.000000", "now": "1.000000", "delta": "bit-för-bit", "dir": "neut"},
            {"label": "Andel p<0,05", "facit": "11,26 %", "now": "11,26 %", "delta": "=facit", "dir": "neut"},
        ],
    },
    "site_step5": {
        "group": "after",
        "title_sv": "Site steg 5 (Excel, lokalt)",
        "story": "Efterbearbetning: modelloutput blir den Excel verksamheten läser. Körs lokalt -- xlwings styr Excel via COM, som inte finns på Linux.",
        "why": "Bearbetar modelloutputen till BCG:s Excel-format via xlwings. "
               "Måste köras på Windows från Site-roten (CWD-beroende config).",
        "use": "Skapar Excel-sammanställningen (elasticity summary) som verksamheten konsumerar.",
        "without": "Rådata finns men inte i det format prismodellen läser.",
        "how_sv": "Körs lokalt på Windows efter att VM-modellen laddat ner sin output. "
                  "xlwings öppnar Excel via COM -- därför Windows, aldrig Linux-VM:en (LB.44).",
        "data": "Excel-sammanställning (elasticity summary), 83 MB",
        "kpis": [
            {"label": "Excel-storlek", "facit": None, "now": "83 MB", "delta": None, "dir": "neut"},
        ],
    },
    "step6": {
        "group": "after",
        "title_sv": "Step 6 -- fallback-väv (lokalt)",
        "story": "Affärssignalen: kärnelasticiteten har rört sig något uppåt -- kunderna är marginellt mindre priskänsliga än vid BCG:s mätning.",
        "why": "Väver ihop cluster- och sitenivå till EN elasticitet per produkt (F1-F7-fallback). "
               "Ren pandas/openpyxl, körs lokalt.",
        "use": "Producerar den slutliga blandade elasticiteten per ProductKey -- talet som styr prissättningen.",
        "without": "Ingen enhetlig elasticitet -- bara separata nivåer utan vägning.",
        "how_sv": "Körs lokalt på Windows (ren pandas/openpyxl, ingen Excel-COM, ingen VM). "
                  "Läser cluster- och site-output och väver ihop dem till en elasticitet per produkt.",
        "data": "15 128 produkter i väven, en elasticitet per ProductKey",
        "kpis": [
            {"label": "Oms.vägd elasticitet", "facit": "-0,532", "now": "-0,512", "delta": "+0,020", "dir": "pos"},
            {"label": "Median-elasticitet", "facit": None, "now": "-0,497", "delta": None, "dir": "pos"},
            {"label": "Produkter i väven", "facit": None, "now": "15 128", "delta": None, "dir": "pos"},
        ],
    },
    "build_r12": {
        "group": "after",
        "title_sv": "Bygg R12-matning (lokalt)",
        "story": "Sista ledet -- gör färska elasticiteter matbara till prismodellens blå flikar.",
        "why": "Aggregerar R12 volym + omsättning per kod x site och joinar färsk elasticitet, "
               "i copy-paste-format till BCG-prismodellen.",
        "use": "Filen som klistras in i prismodellen för att räkna omsättningseffekt av prisförslag.",
        "without": "Elasticiteterna finns men är inte matbara till prismodellen.",
        "how_sv": "Körs lokalt på Windows (build_r12_for_model.py). Sista steget innan talen "
                  "klistras in i prismodellens flikar -- ingen VM, ingen Excel-COM.",
        "data": "Model_Feed: 22 913 rader (kod x klinik), 896 koder, 59 siter",
        "kpis": [],
    },
}

BAGE_SV = ("Bågen: mer data gör modellen säkrare, vilket skärper affärssignalen "
           "som styr prissättningen. Facit (BCG, fryst jun 2025) är nollpunkten -- "
           "allt mäts som rörelse därifrån.")


# ---------------------------------------------------------------------
# VALIDATOR-förklaringar (etapp 3). Per validator: vad den kollar (kort),
# och varför PASS/REVIEW är väntat. KPI:erna kommer MÄTTA ur kvittona i
# appen; detta är den kuraterade tolkningen (Jens röst) -- åtskilt så det
# är tydligt vad som är mätning och vad som är bedömning.
#
# Top-management-princip: en rad key insight per validator. Vill man gräva
# -> exportera kvittot. Förklaringen säger om REVIEW är "väntat/hanterat"
# eller en verklig flagga, så sju REVIEW inte skapar onödig oro.
# ---------------------------------------------------------------------
VALIDATORS = {
    "extraction_coverage": "Kontrollerar att all förväntad transaktionsdata kom med i extraktionen. PASS = inga tysta tapp.",
    "cluster_seed":        "Verifierar att klusterindelningen är deterministisk (samma seed ger samma kluster). PASS = reproducerbart.",
    "facit_selection":     "Bekräftar att rätt facit-period valdes som referens. PASS = jämför mot rätt nollpunkt.",
    "fte_coverage":        "Kollar FTE-täckning per period. PASS = ingen lucka som tyst skulle snedvrida normaliseringen.",
    "dropped_rows":        "Forensisk genomgång av vilka rader som filtrerades bort och varför. INFO = ingen pass/fail-grind, bara spårbarhet.",
    "cluster_distribution":"Kontrollerar att kliniker fördelas rimligt över kluster. PASS = ingen degenererad klusterstruktur.",
    "volume_quantity":     "Verifierar volym- och kvantitetssummor mot väntat. PASS = inga skaltappade fält.",
    "baseline_replication":"Jämför mot BCG:s baslinje bit-för-bit. PASS = extraktionen replikerar exakt.",

    # output_rationality (cluster/site) -- flera REVIEW, var och en VÄNTAD:
    "distribution": "Formen på elasticiteterna (median, andel negativa, spridning) mot BCG:s referens. PASS = fördelningen ser ut som den ska.",
    "outliers":     "Fångar extremvärden (|elast|>5). REVIEW är meningen: 0,77% extremvärden flaggas för mänsklig blick (t.ex. MBAS0703 −320) -- forensisk fångst, inte modellfel.",
    "drift_vs_bcg": "Mäter hur den växande datan rört sig från fryst facit. REVIEW på medeldrift, MEN beslutsrelevant drift bara 2,8% -- rörelsen sitter i svaga tail-grupper, inte i de prissättande. Detta ÄR affärssignalen.",
    "sign_flips":   "Elasticiteter som bytt tecken mot facit. REVIEW på totalen (13,9%), MEN bara 0,69% med båda signifikanta -- resten är svag-signal-brus, väntat (IB.10).",
    "per_cluster":  "Rimlighet per kluster (median, %neg, %sig). REVIEW för att ett litet kluster (Södran) ligger under signifikansgrinden -- konservativ tröskel, inte fel.",
    "per_itemcode_family": "Rimlighet per produktfamilj. REVIEW för att 3 av 173 familjer har svagt positiv median -- små familjer, ingen prispåverkan.",
    "top_leverage": "Identifierar KEY med störst omsättningshävstång (de som faktiskt styr pris). PASS = top 50 fångar 38% av all hävstång, alltid manuellt granskade.",
    "significance_consistency": "Jämför signifikansgrad mot BCG. REVIEW för att BCG-recovery är 70,6% mot grind 80% -- men agreement 82% och sig-grad inom 7pp. Grinden är hårt satt.",
    "review_required": "Aggregatet: den samlade manuella granskningslistan (outliers + drift + sign-flips + top-leverage). REVIEW = 9,1% av KEY flaggas för chefsblick innan prisbeslut -- precis det granskningssteget ska göra.",

    # provenance (step6):
    "step6_provenance":      "Spårar att Step 6-väven byggdes på färsk modelloutput, inte gammal. PASS = rätt input.",
    "fallback_freshness":    "Kontrollerar att fallback-routningen är aktuell mot växande data. PASS = ingen fryst routning.",
}

# proof_chain: bit-för-bit mot fryst facit -- FÖRTROENDELAGRET. Mätta tal ur
# verify_receipt (2026-05-28). Detta är det starkaste beviset: motorn
# replikerar BCG exakt. Skilt från rationality (som granskar växande output).
PROOF_CHAIN = {
    "intro": "Bit-för-bit mot BCG:s frysta facit. Detta bevisar att motorn replikerar BCG exakt på samma data -- "
             "nollpunkten allt växande mäts från. 6 av 6 milstolpar PASS.",
    "items": [
        {"fr": "FR-1", "name": "Dataprep (rader/omsättning/volym)", "kpi": "485 248 rader, korr 1.000000, diff 0,000%"},
        {"fr": "FR-4", "name": "Cluster-modell", "kpi": "population 3 812/3 812, beslutsrel. 1 118/1 118 (100%)"},
        {"fr": "FR-5", "name": "Site-modell", "kpi": "population 4 673/4 673, rank-korr 0,9108, beslutsrel. 113/144"},
        {"fr": "FR-6", "name": "Bundle-modell", "kpi": "population 125/125, beslutsrel. 57/70 (81%)"},
        {"fr": "FR-3", "name": "Cluster-blend / steg 5", "kpi": "43/43 representanter matchar BCG"},
        {"fr": "FR-7", "name": "Fallback-väv / steg 6", "kpi": "108 979 rader, korr 1.000000, nivå-match 100%"},
    ],
    "overall": "6/6 PASS",
    "receipt_file": "verify_tool/receipts/verify_receipt_2026-05-28.xlsx",
}


# =====================================================================
# FUNNEL (etapp 4) -- trattmodellen per familj. Tre lager:
#   topp    : bit-för-bit mot facit (brett förtroende, grönt, korrekt PASS)
#   facit_nu: "vad BCG hade -> vad det blev nu" (berättelsen, ingen dom)
#   prov    : proveniens/nyans (vad är färskt vs fryst) -- ärlighet
# Alla tal MÄTTA ur verify_tool-kvittona. Stora matchande belopp bygger
# förtroende i sig (1151 koder, 0 only-ours, 0 only-facit). Spot-on, inte
# drunkning i detaljer: få starka tal per familj.
# =====================================================================
FUNNEL = {
    "extraction": {
        "proof": {"label": "Dataprep bit-för-bit mot BCG facit", "kpi": "485 248 rader · korr 1.000000 · diff 0,000%", "ok": True},
        "facit_nu": [
            {"metric": "Rader (fryst fönster)", "facit": "485 248", "now": "482 955", "note": "−0,17% aggregerad drift"},
            {"metric": "ItemCodes i båda", "facit": "1 151", "now": "1 151", "note": "0 bara hos oss · 0 bara hos BCG"},
            {"metric": "Per-kod median-drift", "facit": "—", "now": "+0,000%", "note": "typisk kod är bit-identisk"},
        ],
        "prov": None,
        "receipt": "verify_tool/receipts/2026-06-08/00_master_summary_2026-06-08_105839.xlsx",
    },
    "cluster_model": {
        "proof": {"label": "Cluster-modell bit-för-bit (FR-4)", "kpi": "population 3 812/3 812 · beslutsrelevanta 1 118/1 118 (100%) · rank-korr 1.0000", "ok": True},
        "facit_nu": [
            {"metric": "Median-elasticitet", "facit": "−0,137", "now": "−0,113", "note": "samma form, något mindre priskänsligt"},
            {"metric": "Negativ andel", "facit": "76,5 %", "now": "73,7 %", "note": "IB.9-referens håller"},
            {"metric": "Signifikansgrad", "facit": "18 %", "now": "33,4 %", "note": "mer data → fler skattningar håller"},
            {"metric": "Antal KEY", "facit": "3 812", "now": "4 180", "note": "+368 nya från växande fönster"},
        ],
        "prov": None,
        "receipt": "verify_tool/receipts/2026-06-08/rationality/00_rationality_master_2026-06-08_130847.xlsx",
    },
    "site_model": {
        "proof": {"label": "Site-modell bit-för-bit (FR-5)", "kpi": "population 4 673/4 673 · rank-korr 0,9108 · beslutsrelevanta 113/144", "ok": True},
        "facit_nu": [
            {"metric": "Unika KEY", "facit": "6 624", "now": "6 624", "note": "identisk population mot referens"},
            {"metric": "Korrelation", "facit": "1.000000", "now": "1.000000", "note": "bit-för-bit på samma data"},
            {"metric": "Median-elasticitet", "facit": "−0,062", "now": "−0,054", "note": "finaste granulariteten"},
        ],
        "prov": None,
        "receipt": "verify_tool/receipts/verify_receipt_2026-05-28.xlsx",
    },
    "step6": {
        "proof": {"label": "Fallback-väv bit-för-bit (FR-7)", "kpi": "108 979 rader · korr 1.000000 · nivå-match 100,00%", "ok": True},
        "facit_nu": [
            {"metric": "Median blandad elasticitet", "facit": "−0,532", "now": "−0,497", "note": "100% negativ, 100% i (−10,0)-band → beslutsduglig"},
            {"metric": "Inom band (|Δ|<0,5)", "facit": "—", "now": "95,0 %", "note": "beslutsrelevant drift bara 1,6%"},
            {"metric": "Produkter i väven", "facit": "15 128", "now": "15 128", "note": "identisk population"},
        ],
        # Proveniens-nyansen (ärlig): vad är färskt vs fryst i väven.
        "prov": {
            "headline": "Väven blandar färska och frusna inddata — ärlig nyans, inte fel.",
            "fresh": 2, "frozen": 3, "total": 5,
            "rows": [
                {"part": "Site-elasticiteter (F1)", "state": "FÄRSK", "reach": "2026-06-10"},
                {"part": "Cluster-elasticiteter (F3/F5/F6/F7)", "state": "FÄRSK", "reach": "2026-06-08"},
                {"part": "Cluster steg-5-routning (43 rep)", "state": "FRUSEN", "reach": "2025-12 (FD.15)"},
                {"part": "Bundle-modell (F2/F4)", "state": "FRUSEN", "reach": "2025-12 (FD.11)"},
                {"part": "Omsättningsvikter", "state": "FRUSEN", "reach": "2025 (FD.14)"},
            ],
            "bundle_reliance": "Bundle-andel i väven: 2,2% (frusen via FD.11)",
        },
        "receipt": "verify_tool/receipts/2026-06-11/provenance/00_provenance_master_2026-06-11_181714.xlsx",
    },
}
