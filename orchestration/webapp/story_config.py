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
