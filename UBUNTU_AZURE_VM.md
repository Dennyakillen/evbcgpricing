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
