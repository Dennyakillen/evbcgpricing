# UBUNTU_AZURE_VM — Linux/bash-handhavande för BCG-projektets Azure-VM

**Syfte:** Hålla isär två världar. Det lokala arbetet sker i **Windows/PowerShell**; den tunga
körningen sker på en **Ubuntu-VM i Azure** som nås via SSH och styrs med **bash**. Den här filen
samlar Linux-sidan så den inte smetar ihop sig med PowerShell-vanan.

**Utvecklare:** Jens Palmö. Skapad 2026-05-21 vid Azure-PoC.

---

## 1. Mental modell — två maskiner, ett fönster

`ssh azureuser@172.18.148.4` öppnar en tunnel in i VM:en. Från det ögonblicket styr ditt
tangentbord **VM:en**, inte din egen dator — allt du skriver körs där och svaret skickas tillbaka.

**Läs alltid prompten innan du klistrar in.** Den talar om vilken maskin du styr:

| Prompt börjar med | Du styr | Språk | Hör hemma här |
|---|---|---|---|
| `PS C:\...>` | Din Windows-dator | PowerShell | `az`, `scp`, `git`, `Get-ChildItem` |
| `azureuser@bcg-poc-vm:~$` | Azure-VM:en | bash | `ls`, `cat`, `python`, `tmux` |
| `(cluster) azureuser@...$` | VM:en, med venv aktiv | bash | körning av pipelinen |

Hamnar ett kommando i fel fönster blir det oftast ett ofarligt `command not found`. Men vänj dig
att läsa prompten först — det är din viktigaste säkerhetskontroll.

**Det finns ingen "bash" på Windows-datorn.** Den bash du jobbar i är *VM:ens*, nådd via ssh.
I VS Code: en terminalflik som kört `ssh ...` är inne i VM:en (bash); en annan flik utan ssh är
lokal PowerShell. "Växla mellan bash och PowerShell" = klicka mellan flikarna.

---

## 2. bash ↔ PowerShell — Rosetta

| Uppgift | PowerShell | bash |
|---|---|---|
| Lista filer | `Get-ChildItem` / `dir` | `ls` (detaljer: `ls -la`) |
| Var är jag? | `Get-Location` / `pwd` | `pwd` |
| Byt mapp | `cd` | `cd` |
| Visa filinnehåll | `Get-Content` | `cat` (början: `head`, slut: `tail`) |
| Skapa mapp | `New-Item -ItemType Directory` | `mkdir -p` |
| Ta bort fil | `Remove-Item` | `rm` (ingen papperskorg!) |
| Byt namn / flytta | `Move-Item` | `mv` |
| Sök i fil | `Select-String` | `grep` (radnr: `grep -n`) |
| Pipe | `\|` | `\|` (samma idé) |

`~` i bash = din hemmapp (`/home/azureuser`). Skriv tilde **utanför** citationstecken — annars
tolkas den bokstavligt.

---

## 3. Python-miljö på VM:en

Systemets Python (`/usr/bin/python3`, 3.10) tillhör operativsystemet — **rör den aldrig**.
Projektets Python (3.11.9) installerades isolerat via `uv`, och venv:en bor i `~/bcg/cluster/.venv`.

```
source ~/bcg/cluster/.venv/bin/activate
```
Aktivering gäller **per skal**. Öppnar du ett nytt skal (t.ex. inne i tmux) måste du aktivera igen.
Kvittensen är `(cluster)` först i prompten. Installera paket med `uv pip install ...` (sekunder).

**PATH:** skalet letar efter kommandon i en lista av mappar (`PATH`). Ett nyinstallerat verktyg som
inte hittas (`command not found`) ligger ofta i en mapp som inte är på listan — lägg till med
`source ~/.local/bin/env` eller starta om skalet. Samma idé som `Path` i Windows.

---

## 4. Filöverföring Windows ↔ VM (scp)

`scp` bär filer genom ssh-tunneln. Körs **från Windows** (där filerna finns), inte från VM:en.

```powershell
scp -r "C:\lokal\sökväg" azureuser@172.18.148.4:~/mål/på/vm/
```
Anatomin: `-r` = rekursivt (mappar). Källa i citationstecken (krävs vid mellanslag i sökväg).
Mål = `användare@ip` + **kolon** + sökväg på VM:en. Kolonet skiljer "vilken maskin" från
"vilken mapp där". Hämta hem = byt plats på källa/mål.

---

## 5. Encoding-fällor (Windows-filer på Linux)

Windows-editorer sparar ibland textfiler som UTF-16 ("Unicode") eller med BOM. På Linux ställer det
till det — t.ex. läser pip `requirements.txt` fel. **Titta på byten innan du fixar:**

```
head -1 fil.txt | xxd | head -2
```
- `fffe` / `feff` först = **UTF-16**. Hela filen är 2-byte-kodad (en `00` efter varje ASCII-tecken).
  Konvertera **hela filen**, inte bara BOM:en:
  ```
  iconv -f UTF-16 -t UTF-8 fil.txt -o fil_utf8.txt
  mv fil_utf8.txt fil.txt
  ```
- `efbbbf` först = **UTF-8-BOM**. Räcker att strippa BOM:en (`sed`).
- `0d0a` i radslut = **CRLF** (Windows). Ofarligt för pip — ignorera.

`xxd` visar de råa byten och ljuger aldrig om hur terminalen råkar rendera tecknen.

---

## 6. Filrättigheter (vanlig scp-fälla)

`ls -la` visar rättigheter som `drwxrwxr-x`: `d` = mapp, sedan tre block (ägare / grupp / andra)
med `r`ead, `w`rite, e`x`ecute. Filer som scp:ats från en skrivskyddad Windows-mapp kan landa som
`dr-x---r-x` — ägaren saknar `w`, så `sed -i` m.fl. misslyckas med `Permission denied` (kan inte
skapa temp-fil i mappen).

Fix — ge dig själv skrivrätt på din egen projektmapp:
```
chmod -R u+w ~/bcg/cluster
```
`u+w` = lägg till write för ägaren. **Säkert** när det pekar på din egen avgränsade mapp; farligt
på system-/delade kataloger. Peka aldrig `chmod -R` mot `/` eller systemmappar.

---

## 7. tmux — köra långa jobb frikopplat

Problemet: ett vanligt `python ...` är ett barn till din SSH-session och dör om SSH:n dör.
tmux skapar en session som lever **på VM:en själv**, oberoende av din dator.

```
tmux new -s bcgrun          # skapa namngiven session
```
Inne i sessionen (grön statusrad nederst): aktivera venv, starta körningen med tee:ad logg.
```
source ~/bcg/cluster/.venv/bin/activate
cd ~/bcg/cluster/code
python model.py 2>&1 | tee ~/run_log_PC_full.txt
```
Koppla loss (körningen lever vidare): **`Ctrl+B`, släpp, tryck `D`**. Nu kan du stänga SSH,
till och med stänga av datorn.

Återkomst:
```
tmux ls                     # lista sessioner
tmux attach -t bcgrun       # koppla på igen
```

**Att veta / undvika:**
- Kör **aldrig** `ssh` inifrån tmux — du är redan på VM:en.
- Knapptryck/scroll medan loggen rullar är ofarligt (eko på skärm, hamnar ej i loggfilen).
- tmux-sessioner överlever **inte** en `deallocate` → starta ny efter omstart.
- `Ctrl+C` avbryter körningen — undvik om du inte vill stoppa den.

---

## 8. Loggar och verifiering

Skicka aldrig rådata vidare — filtrera fram strukturrader (token-spar, projektets standard):
```
grep -E "Running|Finished|Shape|\([0-9]+, ?[0-9]+\)|Error|Traceback|Saved|completed|stopping" ~/run_log_PC_full.txt
```
**R7:** lita aldrig på loggraden "Pipeline completed" — verifiera output-**filen** (existens +
storlek + tidsstämpel) med `ls -la`. En klar full körning ger `output_summary.xlsx` mycket större
än ett rökstest (referens: 5 grupper ≈ 5,5 KB; 3812 grupper ≈ 320 KB).

---

## 9. Snabbreferens — denna VM

| Sak | Värde |
|---|---|
| VM | `bcg-poc-vm`, `Standard_E16s_v5` (16 vCPU / 128 GB), Ubuntu 22.04 |
| Privat IP | `172.18.148.4` (ingen publik — kontorsnät via SSH) |
| RG / sub | `ev-openai-swce-rg-test` / `ev-lz3-ai (SE)` |
| Arbetsrot på VM | `~/bcg/cluster/` (`code/`, `data/`, `output/`, `.venv/`) |
| Config | `~/bcg/cluster/code/src/config.yml` (`ray: cpus 14 / memory 32` på 128 GB) |
| Control-fil | `code/control_files/control_file.xlsx` (full = 3812 grupper) |
| Rökstest-fil | `code/control_files/control_file_smoke.xlsx` (5 grupper) |
| Kör från | `~/bcg/cluster/code` → `python model.py` |
| Output | `~/bcg/cluster/output/model/output_summary.xlsx` (m.fl.) |
| Logg | `~/run_log_PC_full.txt` |

Driftrutin (start/stopp/kostnad) finns i `README.md` → "Daglig drift".

---

## 10. PowerShell → SSH → bash quote-helvete (känd fälla, fastnat 5+ ggr)

Det enklast skrivna inline-kommandot kan vara det mest tidskrävande att felsöka när tre
språk-tolkar (PowerShell, SSH-klient, bash på VM) ska enas om var citationstecken slutar
och börjar. Den här regeln slipper genvägar:

**Aldrig:** flerradiga `ssh "..."` med `\$()`, `\"`, escape-tecken eller nestade quotes.
PowerShell tolkar `\$()` lokalt **innan** kommandot skickas till SSH, vilket nästan alltid
trasar sönder det avsedda bash-uttrycket.

**Alltid en av:**

**(a) Enrads-kommandon utan escapes (för snabba kontroller):**
```powershell
ssh azureuser@172.18.148.4 "tail -5 ~/run_log_step3.txt"
ssh azureuser@172.18.148.4 "tmux ls"
ssh azureuser@172.18.148.4 "wc -l ~/run_log_step3.txt"
```
Inga `$()`. Inga `\"`. Inga radslut. Tre separata kommandon är alltid bättre än ett komplicerat.

**(b) Bygg .sh lokalt, scp över, kör:**
```powershell
$scriptContent = @'
#!/bin/bash
cd ~/bcg/cluster
source .venv/bin/activate
echo "Running with date: $(date)"
python code/script.py 2>&1 | tee ~/log.txt
'@

# CRLF -> LF (kritiskt på Linux)
$scriptContent = $scriptContent -replace "`r`n", "`n"
[System.IO.File]::WriteAllText("$env:USERPROFILE\Downloads\run.sh", $scriptContent)

scp "$env:USERPROFILE\Downloads\run.sh" azureuser@172.18.148.4:~/run.sh
ssh azureuser@172.18.148.4 "bash ~/run.sh"
```

**(c) Multi-step status:** Lista 3-4 enkla enrads-ssh-kommandon istället för ett komplext
chained-kommando.

**Hang >30 sek = avbryt med Ctrl+C, det är ALDRIG VM:n som hänger.** Det är alltid quote-tolkningen
som blivit galen. Om SSH-klienten själv blockerar är det din lokala terminal som tappat tråden,
inte VM:ens process. Avbryt och försök igen med (a) eller (b).

---

## 11. scp och paths — tre snubblestenar

### 11.1 Trailing backslash escaper citationstecken
```powershell
$archive = "C:\Projekt\BCG\..."
scp "azureuser@vm:~/file.xlsx" "$archive\"   # ❌ trasig
scp "azureuser@vm:~/file.xlsx" $archive       # ✅ fungerar
```
`\` precis före `"` blir en escape-sekvens i scp:s argument-parser. PowerShell-variabler **utan
trailing slash** och **utan citationstecken** runt destinationen är robust.

### 11.2 Pathvariabler i SSH-kommandon behöver inte escape
```powershell
ssh azureuser@vm "ls -la ~/bcg/cluster/output/"   # ✅
ssh azureuser@vm 'ls -la ~/bcg/cluster/output/'   # ✅ också OK
```
`~` expanderas av bash på VM:n, inte av PowerShell. Båda citerings-stilar fungerar lika bra för
enkla kommandon.

### 11.3 Stora filer (>300 MB) via VPN tar tid
För `model_results.csv` (~338 MB): cirka 10-15 sekunder över Evidensia-VPN. För `data_original.csv`
(~177 MB): cirka 5-8 sekunder. Acceptabelt — vänta ut det, avbryt inte.

---

## 12. tmux mönster för pipelinekörning (säkert mönster)

Föredra **enkellinje-anrop** till färdigt sparade .sh-filer framför inline-kommandon:

```powershell
# 1) Bygg .sh lokalt (se §10b)
# 2) scp över
# 3) Starta i tmux med ett rent enkelradigt kommando:
ssh azureuser@vm "tmux new-session -d -s NAMN 'bash ~/run.sh' && sleep 3 && tmux ls"
```

**Kritiska tmux-detaljer:**
- `-d` = detached (sessionen körs utan att din SSH attachar)
- `-s NAMN` = namnge sessionen (kort, unikt: `fs`, `m4`, `prep`)
- Kommandot inom `' '` körs **i** sessionen. Måste vara EN sträng (kan vara `bash ~/x.sh`).
- `sleep 3` ger Python tid att starta innan vi pollar (annars `run_log` är fortfarande 0 bytes)
- `tmux ls` direkt efter bekräftar att sessionen lever

**Status-poll utan att attacha (skadar inte körningen):**
```powershell
ssh azureuser@vm "tmux ls"
ssh azureuser@vm "tail -10 ~/run_log_stepX.txt"
ssh azureuser@vm "ps -eo etime,pcpu,args | grep python.*scriptnamn | grep -v grep"
```

**Tre signaler på att jobbet är klart:**
1. `tmux ls` returnerar `no server running on /tmp/tmux-1000/default`
2. `tail` visar `Exit code: 0` eller motsvarande slut-rad
3. Förväntad output-fil finns (`ls -la /sökväg/till/output.xlsx`)

Lita inte enbart på (2) — `tee` buffrar sista raderna ibland och `End:` syns inte alltid även när
skriptet exited normalt.

---

## 13. `tee` buffrar ofta sista raderna i lång körning

**Symptom:** Skriptet exited (tmux dör, output-fil finns), men `tail -10 ~/run_log_stepX.txt`
visar inte slutraderna (t.ex. `Exit code: 0` eller `End: $(date)`) som skriptet borde ha skrivit.

**Rotorsak:** `tee` använder line-buffered I/O som default. Om scriptet exitar utan en final
newline-flush kan de sista 1-3 raderna ligga kvar i bufferten och förloras när processen dör.

**Regel:** Verifiera klart-status genom **två oberoende signaler**:
1. Tmux-sessionen är borta (`tmux ls` returnerar tomt)
2. Förväntad output-fil finns på rätt path med rimlig storlek

Använd inte "Exit code: 0 i log" som ENDA bevis. Om du behöver explicit "Exit code" i loggen,
skriv den efter `python ...` med en `echo "Exit code: $?" 2>&1 | tee -a log.txt` (tee-append),
inte i en pipeline efter `tee`.

---

## 14. VM startar långsammare än check_env väntar

**Symptom:** `check_env.ps1 -StartVm` startar VM, väntar 15 sekunder, försöker SSH, får timeout,
loggar FAIL och deallokerar automatiskt. VM hinner inte boot:a klart innan SSH testas.

**Rotorsak:** Kall start av Standard_E16s_v5 tar 60-120 sekunder för komplett OS-init + SSH-daemon-
start. check_env:s 15-sekunders-vänta är inte tillräckligt vid första boot efter deallokering.

**Regel:** För riktiga körningar (inte bara koll), starta VM manuellt och polla SSH i loop:
```powershell
az vm start --resource-group ev-openai-swce-rg-test --name bcg-poc-vm
# Vänta 60 sek, försök sedan SSH manuellt:
ssh azureuser@172.18.148.4 "hostname && uptime"
```
Om SSH svarar = klar att gå vidare. För automation: bygg en explicit poll-loop med 10s mellanrum,
max 3 min, **utan** `BatchMode=yes` (det blockerar password fallback och kan hänga obegränsat).

---

## 15. f-strings i `python -c` kraschar på backslash

**Symptom:** `python -c "import pandas as pd; df = pd.read_excel(r'$path'); print(f'KEY: {df[\"KEY\"].count()}')"`
returnerar `SyntaxError: f-string expression part cannot include a backslash`.

**Rotorsak:** Python f-strings (`f"..."`) tillåter inte `\` inom uttrycks-delen (`{...}`). PowerShell
escape-sekvenser av citationstecken (`\"`) blir backslash i den slutgiltiga Python-koden, vilket
bryter f-string-parsern.

**Regel:** Använd **inte** `python -c "..."` för någonting med f-strings + dataaccess. Bygg en .py-fil
lokalt och kör direkt:
```powershell
$content = @'
import pandas as pd
from pathlib import Path
df = pd.read_excel(Path(r"C:\path\to\file.xlsx"))
print(f"KEY count: {len(df)}")
'@
$content = $content -replace "`r`n", "`n"
[System.IO.File]::WriteAllText("$env:USERPROFILE\Downloads\inspect.py", $content)
python "$env:USERPROFILE\Downloads\inspect.py"
```
Samma princip som §10b för .sh-filer: bygg lokalt, kör direkt. Inga escapes.

---

*§10-15 tillagda 2026-06-08 efter VM-körning av cluster pipeline med pg4-fix. Återkommande
PowerShell→SSH-quote-problem (fastnat 5+ ggr under en enda session) konsoliderade till §10
för att en gång för alla etablera mönstret. §11-15 är följder av samma kärnproblem: när tre
språk-tolkar (PowerShell, SSH, bash) ska enas om escape-tecken är det säkrare att bygga
artefakten lokalt och scp:a över.*
