## CLUSTER-MAJ BLOCKERAD (2026-06-23) — config col_type saknar 2 maj-CSV-kolumner

KOMPLETT DIAGNOS (mätt, ej gissad — diff_csv_config_cols.py):
feature_selection.py:532 loopar df:s kolumner, slår upp config['col_type'][col].
KEY 4180 byggde RENT 17/6 (april) men maj kraschar för att MAJ-CSV:n har en ANNAN
kolumnuppsättning än april-CSV:n. Två kolumner i maj-CSV saknas i config col_type:

  1. No_of_Sites (understreck)  -- config har "No of Sites" (MELLANSLAG). Namn-drift
     (FAS 3 / G12). April-CSV hade mellanslag, maj-CSV (SQL-prep) har understreck.
  2. ProductGroupL4Name          -- saknas HELT i config. Ny kolumn i maj-CSV som
     april-vägen ej hade. Trolig typ 'str' (BEKRÄFTA genom att läsa kolumnen).

ROT: maj-data_prep-vägen producerar annan kolumnuppsättning än vad som matade
april-körningen. INTE bara namn — en hel kolumn till. config.yml skriven för
april-varianten. FÖRSTÅ varför CSV:erna skiljer innan cluster byggs på maj-CSV
(kan finnas fler nedströms-skillnader som biter i model.py / Step 6).

FIX (additiv, men gör RÄTT — i repot, ej bara VM):
  config.yml ~/bcg/cluster/code/src/config.yml col_type-sektion (rad 57+):
    No_of_Sites : 'float64'        # NY (understreck-variant, behåll mellanslag med)
    ProductGroupL4Name : 'str'     # NY (bekräfta typ först)
  Fixa i REPOTS config.yml -> committa -> scp/tillämpa VM (annars dator-unikt,
  mot survival-tesen). Config tål då BÅDA namnvarianterna (härdar mot drift).

NÄSTA STEG:
1. Läs ProductGroupL4Name-kolumnens innehåll -> bekräfta 'str'.
2. Kolumn-sond: jämför HELA april-CSV-arkivet (.pre_maj_*) vs maj-CSV kolumnuppsättning
   -> finns fler skillnader än dessa två? Förstå data_prep-divergensen.
3. Fixa config additivt i repot, committa, tillämpa VM.
4. Relauncha cluster (~50 min motor). Med allt förstått lyckas den första gången.

LÄGE: maj-cluster-CSV på VM (~/bcg/cluster/data/0828_..._P_C.csv, 617651 rader).
April-CSV arkiverad på VM (.pre_maj_*). control_file.xlsx finns (377K, 17/6, giltig).
Site-maj validerad, april-fönster komplett, tre fönster i appen, all kod pushad.

SPÖKE: cluster_model fast "running" i maj-statusfilen. Patcha vid nästa körning.

VARNING (process): diagnosen bytte FYRA gånger idag (two-pass->alias->config saknar->
config fel variant+extra kol). Varje mätning vände bilden. Agera EJ trött -- mät klart,
fixa piggt. Verktyg: tools/diff_csv_config_cols.py (byggt idag, jämför CSV vs config).

RUNNER-BUGGAR (runner-fix-pass): (a) two-pass-relaunch ej automatisk; (b) krasch ->
ingen finalize -> spöke.
