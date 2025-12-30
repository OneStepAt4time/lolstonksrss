# Deployment Guide - Backend RSS Server

Guida completa per deployare il backend LoL Stonks RSS su un'altra macchina.

---

## Opzioni di Deployment

Hai **3 opzioni** per deployare il backend:

1. **Docker (CONSIGLIATO)** - Portabile, facile, isolato
2. **Windows Server Diretto** - Nativo, più performante
3. **Linux Server** - Produzione, più stabile

---

## OPZIONE 1: Deployment con Docker (CONSIGLIATO)

### Prerequisiti sulla Macchina Target

**Software Necessario:**
```
✅ Docker Desktop (Windows) o Docker Engine (Linux)
✅ Git (opzionale, per clonare il repo)
```

**Download Docker:**
- Windows: https://www.docker.com/products/docker-desktop/
- Linux: `curl -fsSL https://get.docker.com | sh`

### Step 1: Trasferire i File

**Metodo A: Clonare da GitHub (CONSIGLIATO)**
```bash
# Sulla macchina target
git clone https://github.com/OneStepAt4time/lolstonksrss.git
cd lolstonksrss
```

**Metodo B: Trasferire i File Manualmente**
```bash
# Sulla macchina di sviluppo, crea un archivio
tar -czf lolstonksrss.tar.gz --exclude='.git' --exclude='data' --exclude='site' --exclude='.venv' lolstonksrss/

# Oppure su Windows
# Comprimi la cartella lolstonksrss in un file .zip
# Escludi: .git, data, site, .venv, __pycache__
```

**Trasferimento:**
- Via USB/rete condivisa
- Via SCP: `scp lolstonksrss.tar.gz user@server:/path/`
- Via SFTP/FTP
- Via cloud storage (Google Drive, Dropbox)

### Step 2: Configurazione (sulla macchina target)

**Verifica file necessari:**
```bash
cd lolstonksrss
ls -la

# Dovresti vedere:
# ✅ Dockerfile
# ✅ docker-compose.yml
# ✅ pyproject.toml
# ✅ uv.lock
# ✅ src/ (directory con il codice)
```

**Configura parametri (OPZIONALE):**

Edita `docker-compose.yml` se vuoi cambiare:
```yaml
environment:
  # Porta interna (NON modificare)
  - PORT=8000

  # Intervallo aggiornamento (default: 5 minuti)
  - UPDATE_INTERVAL_MINUTES=5

  # URL base per i link RSS
  - BASE_URL=http://YOUR_SERVER_IP:8002

  # Lingue supportate
  - SUPPORTED_LOCALES=en-us,it-it

ports:
  # Porta esterna (modificare se 8002 è occupata)
  - "8002:8000"  # Cambia 8002 con porta libera
```

**Esempio configurazione per server remoto:**
```yaml
environment:
  - BASE_URL=http://192.168.1.100:8002  # IP del server
  - UPDATE_INTERVAL_MINUTES=10  # Ogni 10 minuti invece di 5

ports:
  - "9000:8000"  # Usa porta 9000 invece di 8002
```

### Step 3: Avvio

```bash
# Avvia il container
docker-compose up -d

# Verifica che sia partito
docker-compose ps

# Output atteso:
# NAME              STATUS    PORTS
# lolstonksrss      Up        0.0.0.0:8002->8000/tcp
```

**Visualizza i log:**
```bash
# Log in tempo reale
docker-compose logs -f

# Ultimi 50 log
docker-compose logs --tail=50

# Dovresti vedere:
# ✅ Starting LoL Stonks RSS server...
# ✅ Database initialized
# ✅ Scheduler started successfully
# ✅ Triggering initial update...
# ✅ en-us: 75 fetched, 75 new
# ✅ it-it: 75 fetched, 75 new
# ✅ Server initialized successfully
```

### Step 4: Verifica Funzionamento

```bash
# Test health check
curl http://localhost:8002/health

# Output atteso:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "service": "LoL Stonks RSS",
#   "database": "connected",
#   "cache": "active",
#   "has_articles": true
# }

# Test RSS feed
curl http://localhost:8002/feed.xml | head -30

# Output atteso: XML con tag <rss>, <channel>, <item>
```

**Test da browser:**
```
http://SERVER_IP:8002/health
http://SERVER_IP:8002/feed.xml
```

### Step 5: Gestione Container

```bash
# Fermare il container
docker-compose down

# Riavviare il container
docker-compose restart

# Vedere i log
docker-compose logs -f

# Aggiornare il codice
git pull  # Se hai clonato da GitHub
docker-compose down
docker-compose up -d --build

# Backup del database
cp data/articles.db data/articles.db.backup

# Restore del database
cp data/articles.db.backup data/articles.db
docker-compose restart
```

---

## OPZIONE 2: Deployment Diretto su Windows Server

### Prerequisiti

**Software Necessario:**
```
✅ Python 3.11 o superiore
✅ UV package manager
✅ Git (opzionale)
```

**Installazione:**

**1. Python 3.11:**
```powershell
# Scarica da: https://www.python.org/downloads/
# Durante installazione, seleziona "Add Python to PATH"

# Verifica
python --version
# Output: Python 3.11.x
```

**2. UV Package Manager:**
```powershell
# Metodo 1: PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Metodo 2: pip
pip install uv

# Verifica
uv --version
```

### Step 1: Trasferire i File

Stessi metodi dell'Opzione 1 (Git clone o trasferimento manuale).

### Step 2: Installazione Dipendenze

```powershell
# Entra nella directory
cd lolstonksrss

# Installa dipendenze con UV
uv sync

# Verifica installazione
uv run python --version
```

### Step 3: Configurazione

**Crea file `.env` (OPZIONALE):**
```powershell
# Crea file .env nella root del progetto
notepad .env
```

**Contenuto `.env`:**
```env
# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Database
DATABASE_PATH=data/articles.db

# Update
UPDATE_INTERVAL_MINUTES=5

# RSS
RSS_FEED_TITLE=League of Legends News
RSS_MAX_ITEMS=50
BASE_URL=http://localhost:8000

# Locali supportati
SUPPORTED_LOCALES=en-us,it-it
```

### Step 4: Avvio Manuale

```powershell
# Crea directory per il database
mkdir data -ErrorAction SilentlyContinue

# Avvia il server
uv run python main.py

# Output atteso:
# Starting server on 0.0.0.0:8000
# Starting LoL Stonks RSS server...
# Database initialized at data/articles.db
# Scheduler started successfully
# Server initialized successfully
```

**Test:**
```powershell
# In un altro terminale
curl http://localhost:8000/health
```

### Step 5: Configurare come Servizio Windows

**Opzione A: NSSM (Non-Sucking Service Manager)**

```powershell
# Download NSSM
# https://nssm.cc/download

# Estrai e copia nssm.exe in C:\Windows\System32

# Installa servizio
nssm install LolRssService "C:\Path\To\Python\Scripts\uv.exe" "run python main.py"
nssm set LolRssService AppDirectory "D:\lolstonksrss"
nssm set LolRssService DisplayName "LoL RSS Feed Service"
nssm set LolRssService Description "League of Legends RSS Feed Generator"
nssm set LolRssService Start SERVICE_AUTO_START

# Avvia servizio
nssm start LolRssService

# Verifica
nssm status LolRssService
```

**Opzione B: Task Scheduler**

```powershell
# Crea script di avvio
notepad start_lolrss.bat
```

**Contenuto `start_lolrss.bat`:**
```batch
@echo off
cd /d D:\lolstonksrss
uv run python main.py
```

Poi in Task Scheduler:
1. Crea nuova task
2. Trigger: "At startup"
3. Action: "Start a program" → `D:\lolstonksrss\start_lolrss.bat`
4. Settings: "If task fails, restart every 1 minute"

---

## OPZIONE 3: Deployment su Linux Server

### Prerequisiti

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv git curl -y

# CentOS/RHEL
sudo yum install python311 git curl -y

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### Step 1: Setup

```bash
# Clone o trasferisci files
git clone https://github.com/OneStepAt4time/lolstonksrss.git
cd lolstonksrss

# Installa dipendenze
uv sync

# Crea directory
mkdir -p data
```

### Step 2: Configurare come Systemd Service

**Crea file servizio:**
```bash
sudo nano /etc/systemd/system/lolrss.service
```

**Contenuto:**
```ini
[Unit]
Description=LoL RSS Feed Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/lolstonksrss
Environment="PATH=/home/your_username/.cargo/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/your_username/.cargo/bin/uv run python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Avvia servizio:**
```bash
# Ricarica systemd
sudo systemctl daemon-reload

# Abilita avvio automatico
sudo systemctl enable lolrss

# Avvia servizio
sudo systemctl start lolrss

# Verifica status
sudo systemctl status lolrss

# Visualizza log
sudo journalctl -u lolrss -f
```

---

## Configurazione Firewall

### Windows Firewall

```powershell
# Apri porta 8002 (o porta configurata)
New-NetFirewallRule -DisplayName "LoL RSS Feed" -Direction Inbound -LocalPort 8002 -Protocol TCP -Action Allow

# Verifica regola
Get-NetFirewallRule -DisplayName "LoL RSS Feed"
```

### Linux Firewall (UFW)

```bash
# Abilita porta
sudo ufw allow 8002/tcp

# Verifica
sudo ufw status
```

---

## Accesso da Altri Dispositivi

Una volta deployato, il feed RSS sarà accessibile da:

**Rete Locale:**
```
http://SERVER_IP:8002/feed.xml
http://192.168.1.100:8002/feed.xml  # Esempio
```

**Internet Pubblico (richiede port forwarding sul router):**
```
1. Configura port forwarding sul router:
   Porta esterna 8002 → IP_SERVER:8002

2. Trova IP pubblico: https://whatismyipaddress.com/

3. Feed accessibile via:
   http://YOUR_PUBLIC_IP:8002/feed.xml
```

**Con Domain Name (opzionale):**
```
1. Registra dominio (es. Cloudflare, GoDaddy)
2. Crea record A: rss.tuodominio.com → YOUR_PUBLIC_IP
3. Feed accessibile via:
   http://rss.tuodominio.com:8002/feed.xml
```

---

## Endpoints Disponibili

Una volta deployato, questi endpoint sono disponibili:

```
# Health Check
GET http://SERVER_IP:8002/health

# Feed RSS Completo
GET http://SERVER_IP:8002/feed.xml

# Feed Solo Inglese
GET http://SERVER_IP:8002/feed/en-us.xml

# Feed Solo Italiano
GET http://SERVER_IP:8002/feed/it-it.xml

# Feed per Categoria
GET http://SERVER_IP:8002/feed/category/Champions.xml
GET http://SERVER_IP:8002/feed/category/Esports.xml

# Status Scheduler
GET http://SERVER_IP:8002/admin/scheduler/status

# Trigger Manuale Update
POST http://SERVER_IP:8002/admin/scheduler/trigger

# API JSON (per frontend)
GET http://SERVER_IP:8002/api/articles?limit=50&source=en-us
```

---

## Monitoraggio e Manutenzione

### Verifiche Periodiche

```bash
# Docker
docker-compose ps
docker-compose logs --tail=100

# Diretto
# Windows
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Linux
sudo systemctl status lolrss
ps aux | grep python
```

### Log Files

**Docker:**
```bash
# Log applicazione
docker-compose logs -f lolstonksrss

# Log persistenti (se configurati)
tail -f logs/lolrss.log
```

**Diretto:**
```bash
# I log vanno in stdout, redireziona se necessario
uv run python main.py > logs/lolrss.log 2>&1
```

### Backup

```bash
# Backup database
cp data/articles.db backups/articles_$(date +%Y%m%d).db

# Backup automatico (crontab Linux)
0 3 * * * cp /path/to/data/articles.db /path/to/backups/articles_$(date +\%Y\%m\%d).db

# Windows Task Scheduler
xcopy D:\lolstonksrss\data\articles.db D:\backups\ /Y
```

---

## Troubleshooting

### Problema: Container non parte

```bash
# Verifica errori
docker-compose logs

# Ricostruisci immagine
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verifica porte libere
netstat -ano | findstr :8002  # Windows
netstat -tulpn | grep :8002   # Linux
```

### Problema: Database locked

```bash
# Ferma container
docker-compose down

# Rimuovi database (PERDI I DATI)
rm data/articles.db

# Riavvia
docker-compose up -d

# Restore da backup
cp data/articles.db.backup data/articles.db
docker-compose restart
```

### Problema: Scheduler non aggiorna

```bash
# Verifica status
curl http://localhost:8002/admin/scheduler/status

# Trigger manuale
curl -X POST http://localhost:8002/admin/scheduler/trigger

# Verifica log
docker-compose logs -f | grep "Update"
```

### Problema: Porta già in uso

**Errore:**
```
Error: bind: address already in use
```

**Fix:**
```yaml
# Cambia porta in docker-compose.yml
ports:
  - "9000:8000"  # Usa 9000 invece di 8002
```

---

## Checklist Deployment

### Pre-Deployment
- [ ] Macchina target ha Docker/Python installato
- [ ] File progetto trasferiti
- [ ] Porte firewall configurate (8002 o custom)
- [ ] Spazio disco sufficiente (minimo 1GB)

### Durante Deployment
- [ ] Docker container parte senza errori
- [ ] Database inizializzato correttamente
- [ ] Scheduler avviato e funzionante
- [ ] Initial update completato (75+ articoli)

### Post-Deployment
- [ ] Health check risponde OK
- [ ] Feed RSS valido e accessibile
- [ ] Feed aggiorna ogni 5 minuti
- [ ] Accessibile da rete locale
- [ ] Backup configurato (opzionale)
- [ ] Servizio/container parte automaticamente al boot

---

## Performance e Scalabilità

### Risorse Minime

```
CPU: 1 core
RAM: 512 MB
Disco: 1 GB
Rete: 10 Mbps
```

### Risorse Raccomandate

```
CPU: 2 cores
RAM: 2 GB
Disco: 5 GB (per log e backup)
Rete: 100 Mbps
```

### Ottimizzazioni

**Per ridurre carico API:**
```yaml
# Aumenta intervallo aggiornamento
environment:
  - UPDATE_INTERVAL_MINUTES=15  # Ogni 15 min invece di 5
```

**Per ridurre memoria:**
```yaml
# Limita articoli in memoria
environment:
  - RSS_MAX_ITEMS=25  # 25 invece di 50
```

**Per database SQLite:**
```python
# Già ottimizzato nel codice con:
# - WAL mode
# - Connection pooling
# - Async I/O
```

---

## Sicurezza

### Best Practices

1. **Non esporre pubblicamente senza autenticazione**
   ```yaml
   # Usa reverse proxy con auth se esponi su internet
   ```

2. **Aggiorna regolarmente**
   ```bash
   git pull
   docker-compose up -d --build
   ```

3. **Backup database**
   ```bash
   # Automatizza backup giornalieri
   ```

4. **Monitora log per errori**
   ```bash
   docker-compose logs | grep ERROR
   ```

5. **Limita rate limiting**
   ```python
   # Già configurato in src/api/app.py
   # 5 richieste/minuto per endpoint admin
   ```

---

## Riepilogo Comandi Rapidi

### Docker Deployment (Quick Start)

```bash
# 1. Clone
git clone https://github.com/OneStepAt4time/lolstonksrss.git
cd lolstonksrss

# 2. Start
docker-compose up -d

# 3. Verify
curl http://localhost:8002/health
curl http://localhost:8002/feed.xml | head -30

# 4. View logs
docker-compose logs -f

# 5. Stop
docker-compose down
```

### Gestione Quotidiana

```bash
# Restart
docker-compose restart

# Update code
git pull && docker-compose up -d --build

# Backup DB
cp data/articles.db data/articles.db.$(date +%Y%m%d)

# View status
docker-compose ps
docker-compose logs --tail=50
```

---

**Deployment completato!** Il tuo backend RSS è ora operativo sulla nuova macchina.
