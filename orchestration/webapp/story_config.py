"""
story_config.py -- Facit-referens + berattartexter for Phase Z-dashboarden
===========================================================================
Statisk konfiguration, medvetet INTE i Blob: BCG:s frysta facit andras
aldrig, alltsa ar referensvarden konfiguration -- inte data som hamtas.
Dashboarden vaver ihop detta (det frysta) med statusfilen (det levande).

ARLIGHETSREGEL (honesty contract): varje tal har en kallkommentar.
None betyder "annu ej verifierat mot kvitto" och renderas som "[fyll i]"
i gransnittet -- ALDRIG ett pahittat varde. Fyll pa har, en plats, nar
fler facit-tal verifieras ur valideringskvittona.

FRAMTID (FD): nar runnern skriver KPI:er strukturerat i statusfilen
(metrics-falt i kontraktet, nasta kontraktsversion) forsvinner behovet
av "now"-varden har -- da blir denna fil enbart facit + texter.

Nycklarna MASTE matcha statuskontraktets phase keys (run_status.py):
extraction, cluster_model, site_model, site_step5, step6, build_r12.

Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
Forfattare: Claude-radgivare, Phase Z-session 2026-06-12.
"""

# Varje KPI: label, facit (str|None), now (str|None), delta (str|None),
# dir: "pos" (gron uppat-pil), "neg" (rod nedat), "neut" (gra =).
STORY = {
    "extraction": {
        "title_sv": "Extraktion (dataprep, lokalt)",
        "story": "BCG byggde pa data till juni 2025. Vi ser nu till april 2026 -- tio manader till.",
        "why": "Hamtar farsk transaktionsdata och bygger vecko-CSV:n som modellen tranar pa. "
               "Kors lokalt eftersom datalagret (DW) bara nas pa kontorsnat/VPN -- inte fran Azure-VM:en.",
        "use": "Producerar branslet: CSV och parquet som modellstegen laser.",
        "without": "Modellen kor pa fryst data -- nya manader saknas tyst (G7-lardomen).",
        "kpis": [
            # Datafonster: frozen facit = transaction_data_frozen_facit_2025-06; growing = 2026-04-30 (regenererad parquet, session 2026-06-10/12)
            {"label": "Datafonster", "facit": "jun 2025", "now": "apr 2026", "delta": "+10 man", "dir": "pos"},
            # Growing-rader: 27 435 679 (parquet-regenerering, verifierad). Facit-parquetens radantal: ej avlast -> None.
            {"label": "Transaktionsrader", "facit": None, "now": "27,4 M", "delta": None, "dir": "pos"},
            # Growing-storlek ~1 091 MB (verifierad). Facit-storlek: ej avlast -> None.
            {"label": "Storlek", "facit": None, "now": "1 091 MB", "delta": None, "dir": "pos"},
        ],
    },
    "cluster_model": {
        "title_sv": "Cluster-modell steg 1-4 (VM)",
        "story": "Med mer data passerar fler elasticitetsskattningar signifikanstroskeln -- modellen blir att lita pa.",
        "why": "OLS-elasticitet per produkt x kluster, Ray-parallelliserad pa VM:en. "
               "Tung berakning som kraver VM:ens minne -- darfor Azure, inte laptopen.",
        "use": "Ger klusterniva-elasticiteter -- ett av lagren i Step 6-vaven.",
        "without": "Step 6 saknar klusternivan i fallback-vaven.",
        "kpis": [
            # Signifikansandel facit vs growing: 33,4 % -> 45,2 % (F.7-jamforelsen, sessionsdokumenterad)
            {"label": "Signifikansandel", "facit": "33,4 %", "now": "45,2 %", "delta": "+11,8 pp", "dir": "pos"},
        ],
    },
    "site_model": {
        "title_sv": "Site-modell steg 1-4 (VM)",
        "story": "Motorn bevisad: orchestrator-korningen ar bit-for-bit identisk med facit pa samma data.",
        "why": "OLS-elasticitet per produkt x site -- modellens finaste granularitet. "
               "Validerad bit-for-bit mot facit-korningen 2026-06-09.",
        "use": "Primar elasticitetssignal -- matar Step 6 och R12-matningen.",
        "without": "Ingen siteniva-elasticitet; vaven faller tillbaka pa grovre nivaer.",
        "kpis": [
            # Orchestrator-korning 2026-06-12 vs facit 2026-06-09: 6624 KEY identiskt (valideringskvitto PASS)
            {"label": "Unika KEY", "facit": "6 624", "now": "6 624", "delta": "=facit", "dir": "neut"},
            # Korrelation 1.000000, max_abs_diff 0.00e+00 (kvitto 20260612_172632_PASS)
            {"label": "Korrelation", "facit": "1.000000", "now": "1.000000", "delta": "bit-for-bit", "dir": "neut"},
            # Andel p<0.05: 11,26 % identisk i bada (samma kvitto)
            {"label": "Andel p<0,05", "facit": "11,26 %", "now": "11,26 %", "delta": "=facit", "dir": "neut"},
        ],
    },
    "site_step5": {
        "title_sv": "Site steg 5 (Excel, lokalt)",
        "story": "Efterbearbetning: modelloutput blir den Excel verksamheten laser. Kors lokalt -- xlwings styr Excel via COM, som inte finns pa Linux.",
        "why": "Bearbetar modelloutputen till BCG:s Excel-format via xlwings. "
               "Maste koras pa Windows fran Site-roten (CWD-beroende config).",
        "use": "Skapar Excel-sammanstallningen (elasticity summary) som verksamheten konsumerar.",
        "without": "Radata finns men inte i det format prismodellen laser.",
        "kpis": [
            # F.8 Step 5 pa growing gav 83 MB Excel (2026-06-10). Facit-storlek: ej avlast -> None.
            {"label": "Excel-storlek", "facit": None, "now": "83 MB", "delta": None, "dir": "neut"},
        ],
    },
    "step6": {
        "title_sv": "Step 6 -- fallback-vav (lokalt)",
        "story": "Affarssignalen: karnelasticiteten har rort sig nagot uppat -- kunderna ar marginellt mindre priskansliga an vid BCG:s matning.",
        "why": "Vaver ihop cluster- och siteniva till EN elasticitet per produkt (F1-F7-fallback). "
               "Ren pandas/openpyxl, kors lokalt.",
        "use": "Producerar den slutliga blandade elasticiteten per ProductKey -- talet som styr prissattningen.",
        "without": "Ingen enhetlig elasticitet -- bara separata nivaer utan vagning.",
        "kpis": [
            # Omsattningsvagd elasticitet facit -0,532 -> growing -0,512 (driftanalys, sessionsdokumenterad)
            {"label": "Oms.vagd elasticitet", "facit": "-0,532", "now": "-0,512", "delta": "+0,020", "dir": "pos"},
            # Growing-median -0,497 (Step6 pa growing). Facit-median: ej avlast ur facit-korningen -> None.
            {"label": "Median-elasticitet", "facit": None, "now": "-0,497", "delta": None, "dir": "pos"},
            # Produkter i vaven (growing): 15 128. Facit-antal: ej avlast -> None.
            {"label": "Produkter i vaven", "facit": None, "now": "15 128", "delta": None, "dir": "pos"},
        ],
    },
    "build_r12": {
        "title_sv": "Bygg R12-matning (lokalt)",
        "story": "Sista ledet -- gor farska elasticiteter matbara till prismodellens bla flikar.",
        "why": "Aggregerar R12 volym + omsattning per kod x site och joinar farsk elasticitet, "
               "i copy-paste-format till BCG-prismodellen.",
        "use": "Filen som klistras in i prismodellen for att rakna omsattningseffekt av prisforslag.",
        "without": "Elasticiteterna finns men ar inte matbara till prismodellen.",
        "kpis": [],
    },
}

BAGE_SV = ("Bagen: mer data gor modellen sakrare, vilket skarper affarssignalen "
           "som styr prissattningen. Facit (BCG, fryst jun 2025) ar nollpunkten -- "
           "allt mats som rorelse darifran.")
