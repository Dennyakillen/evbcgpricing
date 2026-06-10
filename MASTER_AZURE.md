# MASTER_AZURE — Teknisk masterinstruktion

**Gäller:** Alla Azure-relaterade operationer  
**Läses i kombination med:** `KÄRNPRINCIPER.md`, `MASTER_PYTHON.md`  
**Senast uppdaterad:** 2026-05-19

---

## 1. Konton och prenumerationer

### 1.1 Aktiva konton

| Konto | Syfte |
|---|---|
| `adm.jens.palmo@evidensia.se` | Azure CLI, Azure Portal, deployment |
| `jepa02@evidensia.se` | Vardagligt Windows-konto |

### 1.2 Aktiva prenumerationer

| Prenumeration | ID | Tenant |
|---|---|---|
| **ev-lz1-hybrid (SE)** | `3aef512a-c6c1-427a-b9eb-533ce4f93fb1` | Evidensia Djursjukvård AB |
| ev-lz3-ai (SE) | `42f726f8-91ee-44d4-832f-9d9ec412ef8f` | Evidensia (Hemsida-projekt) |

**Default för ProvetDiscount:** `ev-lz1-hybrid (SE)`
**Default för BCG-pricing (evbcgpricing, VM bcg-poc-vm):** `ev-lz3-ai (SE)`

> ⚠️ **Subscription-fälla (LB.46, 2026-06-10):** `az` cachar aktiv subscription mellan sessioner.
> Har du jobbat med ProvetDiscount (`ev-lz1-hybrid`) sitter du kvar där nästa dag → `az vm start`
> på BCG-VM:en ger `AuthorizationFailed` (VM finns ej i fel subscription, INTE utgången token).
> Kör alltid `az account show` FÖRE VM-kommandon och sätt rätt subscription för projektet.

```powershell
# ProvetDiscount:
az account set --subscription "ev-lz1-hybrid (SE)"
# BCG-pricing VM:
az account set --subscription "ev-lz3-ai (SE)"
az account show
```

### 1.3 Tenant-ID

```
151cba74-8bbb-47ff-8beb-10fe15c49e3e
```

---

## 2. Aktiva resurser — ProvetDiscount

### 2.1 Resursgrupper

| Resursgrupp | Region | Jens roll | Status |
|---|---|---|---|
| **ev-vetpris-swce-rg-prod** | Sweden Central | **Owner** | ✅ Aktiv — använd denna |
| ev-pricing-swce-rg-test | Sweden Central | Contributor | Övergiven (AcrPull blockerad) |
| ev-pricing-swce-rg-prod | Sweden Central | Contributor | Övergiven |

> **Viktig lärdom:** Contributor saknar `Microsoft.Authorization/roleAssignments/write`. Owner krävs för att tilldela roller (t.ex. AcrPull till Managed Identity). Använd alltid `ev-vetpris-swce-rg-prod`.

### 2.2 Aktiva resurser i ev-vetpris-swce-rg-prod

| Resurstyp | Namn | SKU/detaljer |
|---|---|---|
| Azure Container Registry | `evvetprisswceprodacr` | Basic, Sweden Central |
| App Service Plan | `ev-vetpris-asp-prod` | B1 Linux |
| Web App | `ev-pricing-app-prod` | Linux container |
| Managed Identity | SystemAssigned på Web App | `principalId: 75763014-a155-43fd-8189-7f10235e2514` |
| ACR-roll | AcrPull → Web App MI | Tilldelad ✅ |
| Storage Account | `evpricingswcergtestac7b` | I gamla test-RG — fortsatt använd |

**Publik URL:** `https://ev-pricing-app-prod.azurewebsites.net`  
**ACR login-server:** `evvetprisswceprodacr.azurecr.io`  
**Image:** `provet-discount:latest`

### 2.3 App Settings i Web App

| Variabel | Värde | Syfte |
|---|---|---|
| `WEBSITES_PORT` | `8000` | Gunicorn-port |
| `acrUseManagedIdentityCreds` | `true` | Pull från ACR utan lösenord |
| `CHROME_CONTAINER_MODE` | `1` | Aktiverar headless Chrome-flaggor |
| `AZURE_STORAGE_CONNECTION_STRING` | (satt) | Blob-lagring |
| `FLASK_SECRET_KEY` | (64-char hex) | Sessions persistens vid omstart |

### 2.4 Registrerade Resource Providers (ev-lz1-hybrid)

| Provider | Status |
|---|---|
| `Microsoft.Web` | ✅ |
| `Microsoft.Storage` | ✅ |
| `microsoft.insights` | ✅ |
| `Microsoft.OperationalInsights` | ✅ |
| `Microsoft.ManagedIdentity` | ✅ |
| `Microsoft.KeyVault` | ✅ |
| `Microsoft.ContainerRegistry` | ✅ (registrerad av Kent) |

---

## 3. Deployment-flöde — ACR Tasks

Vi använder **ACR Tasks** (`az acr build`) — ingen lokal Docker krävs.

### 3.1 Standard deploy-sekvens

**Steg 1 — Re-login (var 4:e timme pga Conditional Access):**
```powershell
az login --scope https://management.core.windows.net//.default
```

**Steg 2 — Gå till projektroten:**
```powershell
cd "C:\Projekt\Kampanjmodul\app"
```

**Steg 3 — Bygg och pusha image:**
```powershell
az acr build --registry evvetprisswceprodacr --image provet-discount:latest .
```

**Steg 4 — Starta om Web App:**
```powershell
az webapp restart --name ev-pricing-app-prod --resource-group ev-vetpris-swce-rg-prod
```

**Steg 5 — Vänta och verifiera:**
```powershell
Start-Sleep -Seconds 30
Invoke-WebRequest -Uri "https://ev-pricing-app-prod.azurewebsites.net/healthz" -UseBasicParsing
```
Förväntat: HTTP 200, `{"status":"ok"}`.

### 3.2 Live-loggar under körning

```powershell
az webapp log tail --name ev-pricing-app-prod --resource-group ev-vetpris-swce-rg-prod
```

### 3.3 App Settings — uppdatera

```powershell
az webapp config appsettings set --name ev-pricing-app-prod --resource-group ev-vetpris-swce-rg-prod --settings KEY=VALUE
```

### 3.4 Always On — aktivera (viktigt för B1)

```powershell
az webapp config set --name ev-pricing-app-prod --resource-group ev-vetpris-swce-rg-prod --always-on true
```

---

## 4. Dockerfile — referensimplementation (ProvetDiscount)

```dockerfile
FROM python:3.11-slim

# Installera Chromium och chromedriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kopiera och installera beroenden
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiera källkod
COPY . .

# Non-root user (säkerhetsbest practice)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Starta med Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2",
     "--timeout", "300", "--keep-alive", "75", "wsgi:app"]
```

**.dockerignore (kritiska poster):**
```
.git
.venv
dist/          ← MÅSTE vara med (207MB PyInstaller-artefakter)
build/
*.pyc
__pycache__
*.log
config/.env    ← innehåller secrets
```

> **OBS:** `input/dim_department.xlsx` får **INTE** exkluderas — den är referensdata som behövs i container.

---

## 5. Container-specifika kod-anpassningar

### 5.1 Chrome container-mode (`src/core/browser.py`)

```python
import os

def get_chrome_options():
    options = webdriver.ChromeOptions()
    
    if os.environ.get('CHROME_CONTAINER_MODE') == '1':
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.binary_location = '/usr/bin/chromium'
    
    return options
```

### 5.2 Automatisk Provet Cloud-inloggning

```python
def login_to_provet(driver, username: str, password: str, timeout: int = 30) -> None:
    """Automatisk inloggning via Django-formuläret."""
    driver.get("https://evidensia.provetcloud.com/731/accounts/login/")
    wait = WebDriverWait(driver, timeout)
    
    wait.until(EC.presence_of_element_located((By.ID, 'id_username'))).send_keys(username)
    driver.find_element(By.ID, 'id_password').send_keys(password)
    driver.find_element(By.ID, 'id_btn_login').click()
    
    wait.until(EC.url_contains('/731/'))
```

> **Viktigt:** `login_to_provet` måste re-exporteras i `infrastructure/browser.py` om routes importerar därifrån.

### 5.3 Sessionsbundna filer

```python
import uuid, os
from flask import session

def save_uploaded_file(file):
    """Sparar uppladdad fil i /tmp med session-ID."""
    file_id = str(uuid.uuid4())
    session['file_id'] = file_id
    path = f"/tmp/facit_{file_id}.xlsx"
    file.save(path)
    return path

def get_session_file():
    file_id = session.get('file_id')
    if not file_id:
        return None
    path = f"/tmp/facit_{file_id}.xlsx"
    return path if os.path.exists(path) else None
```

---

## 6. Azure SQL (Business_Analytics)

### 6.1 Anslutning

```python
# data_access.py
import pyodbc
from azure.identity import DefaultAzureCredential
import struct

SERVER = "se-az-we-bi-sql-01.database.windows.net"
DATABASE = "se-az-we-bi-dw-sqldb-01"

def get_connection():
    credential = DefaultAzureCredential()
    token = credential.get_token("https://database.windows.net/.default")
    token_bytes = token.token.encode('utf-16-le')
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"Authentication=ActiveDirectoryServicePrincipal;"
    )
    conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
    return conn

def query_to_df(sql: str) -> pd.DataFrame:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame.from_records(rows, columns=cols)
```

### 6.2 Token-renewal (Evidensia Conditional Access — var 4:e timme)

```powershell
az login --scope https://management.core.windows.net//.default
az login --scope https://database.windows.net/.default
```

> **Regel:** Sätt påminnelse vid långsessioner. `AADSTS70043: The refresh token has expired` bryts alltid vid `az acr build` utan förnyad token.

---

## 7. Rollhantering och behörigheter

### 7.1 Verifiera roller innan deployment

```powershell
az role assignment list --assignee adm.jens.palmo@evidensia.se --resource-group ev-vetpris-swce-rg-prod --output table
```

| Roll | Kan göra |
|---|---|
| Owner | Tilldela roller (AcrPull), allt Contributor kan |
| Contributor | Skapa/ändra resurser, men EJ tilldela roller |

> **Regel:** Verifiera rollnivå *innan* deployment påbörjas. AcrPull-tilldelning kräver Owner-rollen.

### 7.2 AcrPull till Web App Managed Identity

```powershell
az role assignment create \
  --assignee 75763014-a155-43fd-8189-7f10235e2514 \
  --role AcrPull \
  --scope /subscriptions/3aef512a-c6c1-427a-b9eb-533ce4f93fb1/resourceGroups/ev-vetpris-swce-rg-prod/providers/Microsoft.ContainerRegistry/registries/evvetprisswceprodacr
```

---

## 8. Felsökning Azure

### 8.1 Container startar inte

```powershell
az webapp log tail --name ev-pricing-app-prod --resource-group ev-vetpris-swce-rg-prod
```

Vanliga orsaker:
- `WEBSITES_PORT` ej satt → container hör inte på rätt port
- Image misslyckades att byggas → kontrollera ACR-loggar
- Secrets saknas i App Settings → kontrollera `FLASK_SECRET_KEY`, `AZURE_STORAGE_CONNECTION_STRING`

```powershell
az acr task list-runs --registry evvetprisswceprodacr --output table
```

### 8.2 Hälsokontroll

```powershell
Invoke-WebRequest -Uri "https://ev-pricing-app-prod.azurewebsites.net/healthz" -UseBasicParsing
```
Förväntat: `StatusCode: 200`, body: `{"status":"ok"}`.

### 8.3 SSE-problem — diagnos

```powershell
az webapp log tail --name ev-pricing-app-prod --resource-group ev-vetpris-swce-rg-prod
```

Om workern är **aktiv** när UI:t rapporterar "Anslutning bruten" → SSE/proxy-problem (Azure Front Door buffrar).  
Om workern är **tyst** → worker-stall (Selenium exception, Gunicorn timeout).

```
Gunicorn-parametrar att justera vid worker-stall:
--keep-alive 75      (Azure-rekommendation för SSE)
--timeout 300        (Selenium-jobb tar upp till 2 min)
```

### 8.4 PowerShell-quoting-problem med Azure CLI

**Aldrig:** `az resource update --set 'properties.key=value'` (bryter i PowerShell)  
**Istället:** `az webapp config appsettings set --settings KEY=VALUE`  
**Eller:** `az resource update --set` med korrekt JSON-escaping — testa alltid i liten skala.

---

## 9. Snabbreferens — Azure-kommandon

```powershell
az login --scope https://management.core.windows.net//.default
```

```powershell
az account show
```

```powershell
az account set --subscription "ev-lz1-hybrid (SE)"
```

```powershell
cd "C:\Projekt\Kampanjmodul\app"
az acr build --registry evvetprisswceprodacr --image provet-discount:latest .
```

```powershell
az webapp restart --name ev-pricing-app-prod --resource-group ev-vetpris-swce-rg-prod
```

```powershell
az webapp log tail --name ev-pricing-app-prod --resource-group ev-vetpris-swce-rg-prod
```

```powershell
Invoke-WebRequest -Uri "https://ev-pricing-app-prod.azurewebsites.net/healthz" -UseBasicParsing
```

---

## 10. Kumulativa lärdomar — Azure

### E.3 — Azure CLI-token går ut var 4:e timme
**Symptom:** `AADSTS70043: The refresh token has expired`  
**Rotorsak:** Evidensias Conditional Access begränsar token-livslängd.  
**Regel:** Re-login med scope-specificering. Sätt påminnelse vid långa sessioner.

### E.4 — Owner-roll krävs för rolltilldelning, inte Contributor
**Symptom:** `Microsoft.Authorization/roleAssignments/write: AuthorizationFailed`  
**Rotorsak:** Contributor saknar rätt att tilldela roller.  
**Regel:** Verifiera rollnivå **innan** deployment påbörjas. Byt RG eller eskalera rollnivå tidigt.

### E.10 — SSE-problem: kontrollera worker-aktivitet, inte bara heartbeat
**Symptom:** SSE-anslutning bryts trots heartbeat-fix.  
**Regel:** Verifiera med `az webapp log tail` om workern är aktiv. Heartbeat-fix är sista steget, inte första.

### AZ.1 — Gamla RG med fel roll blockerar rolltilldelning
**Symptom:** Hela arbetsflödet förutsatte att Jens kunde tilldela AcrPull från test-RG.  
**Rotorsak:** Contributor i ev-pricing-swce-rg-test saknar `Microsoft.Authorization/roleAssignments/write`.  
**Regel:** Kontrollera roll i den faktiska RG:n som ska användas. Byt till RG där Owner-rollen finns (`ev-vetpris-swce-rg-prod`).

### AZ.2 — F1 App Service Plan stödjer inte custom containers
**Regel:** SKU B1 eller högre krävs för Web App for Containers. F1 Free är inte tillräckligt.

### AZ.3 — `dist/` MÅSTE exkluderas i .dockerignore, `dim_department.xlsx` får INTE exkluderas
**Rotorsak:** `dist/` innehåller 207MB PyInstaller-artefakter som inte behövs i container. `dim_department.xlsx` är referensdata som faktiskt behövs.  
**Regel:** Verifiera .dockerignore mot projektspecifik filstruktur — generiska mallar missar projektspecifika filbehov.

### AZ.4 — Always On måste aktiveras på B1 för att undvika kallstarter
**Symptom:** Långsam respons mellan körningar.  
**Regel:** `az webapp config set --always-on true` direkt efter Web App-skapande.

### AZ.5 — Kontextkomprimering raderar lokala outputs
**Symptom:** str_replace-leverans på filer som inte längre finns i sandbox.  
**Regel:** Vid sessionspaus eller kontextkomprimering — be om `Get-Content` innan ändringar appliceras. Filer i `/outputs/` överlever inte komprimering.
