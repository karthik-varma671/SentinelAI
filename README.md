<<<<<<< HEAD
```
###############################################################################################
##                                                                                           ##
##   ######  ######## ##    ## ######## #### ##    ## ######## ##                             ##
##  ##    ## ##       ###   ##    ##     ##  ###   ## ##       ##                             ##
##  ##       ##       ####  ##    ##     ##  ####  ## ##       ##                             ##
##   ######  ######   ## ## ##    ##     ##  ## ## ## ######   ##                             ##
##        ## ##       ##  ####    ##     ##  ##  #### ##       ##                             ##
##  ##    ## ##       ##   ###    ##     ##  ##   ### ##       ##                             ##
##   ######  ######## ##    ##    ##    #### ##    ## ######## ########                       ##
##                                                                                           ##
##        ###    ####                                                                        ##
##       ## ##    ##                                                                         ##
##      ##   ##   ##                                                                         ##
##     ##     ##  ##                                                                         ##
##     #########  ##                                                                         ##
##     ##     ##  ##                                                                         ##
##     ##     ## ####                                                                        ##
##                                                                                           ##
##            AUTONOMOUS ENDPOINT SECURITY & THREAT RESPONSE PLATFORM                        ##
##                                                                                           ##
###############################################################################################
```

# SentinelAI

Real-time endpoint security platform that monitors Windows machines, detects threats autonomously, enforces organizational policies, and performs automated incident response — all controlled from a centralized web dashboard.

## Overview

SentinelAI protects Windows endpoints in an organizational network using a three-component architecture:

- a **bot agent** deployed on each endpoint for continuous monitoring and enforcement
- a **central server** (FastAPI + WebSocket) managing all bots, authentication, data, and lockdown decisions
- a **web dashboard** providing admins with real-time visibility, control, and policy management

The bot agent continuously scans running processes, calculates threat scores, enforces admin-defined policies, and can automatically lock down compromised machines. Forensic snapshots are captured on lockdown events and uploaded for analyst review.

## Features

- real-time process scanning with name-based and behavioral threat detection
- autonomous endpoint lockdown (overlay, input block, network isolation, forensics)
- centralized policy engine with process blocking, required process compliance, USB control, and folder RBAC
- policy versioning and one-click rollback
- TOTP-based multi-factor authentication (Google Authenticator, Authy compatible)
- role-based access control (Admin > Analyst > Viewer)
- live network traffic monitoring with per-connection process attribution
- comprehensive forensic snapshots (processes, connections, services, scheduled tasks, installed software, autoruns, event logs)
- full audit trail of all system actions
- time-based policy scheduling
- groups and organizational units for scalable targeting
- lockdown persistence across reboots and reconnections
- emergency unlock hotkey (`Ctrl+Alt+Shift+U`)
- WebSocket-based persistent communication with auto-reconnect

## Repository Layout

```
.
├── README.md                       # project documentation
├── .gitignore                      # git ignore rules
│
├── bot/                            # ENDPOINT AGENT
│   └── bot_end.py                  # main bot script (742 lines)
│       ├── Configuration           # server URL, thresholds, scan intervals
│       ├── Persistent Identity     # UUID generation, username storage
│       ├── Windows API             # BlockInput, UAC elevation
│       ├── Overlay System          # tkinter full-screen lockdown UI
│       ├── Emergency Hotkey        # Ctrl+Alt+Shift+U unlock
│       ├── Firewall Management     # netsh rules for network isolation
│       ├── Forensics Capture       # deep system snapshot
│       ├── Lockdown Engine         # lock/unlock orchestration
│       ├── Policy Enforcement      # process blocking, USB, folder RBAC
│       ├── Monitoring Loops        # process scanner, session, network
│       └── Main Connection Loop    # WebSocket with auto-reconnect
│
├── server/                         # CENTRAL SERVER
│   └── server.py                   # FastAPI server (1163 lines)
│       ├── Security Layer          # JWT, bcrypt, TOTP
│       ├── Database Schema         # 9 SQLite tables
│       ├── Pydantic Models         # request/response validation
│       ├── WebSocket Manager       # bot connection tracking
│       ├── Auth Endpoints          # register, login, MFA
│       ├── Bot Control             # lockdown, unlock, computer mgmt
│       ├── Policy CRUD             # create, read, update, delete, rollback
│       ├── User/Group/OU Mgmt     # full CRUD with RBAC
│       ├── Audit & Monitoring      # logs, network traffic, forensics
│       └── Server Startup          # DB init, admin creation
│
└── dashboard/                      # WEB DASHBOARD
    └── dashboard.html              # single-page application (866 lines)
        ├── Login (with MFA)        # two-step authentication UI
        ├── Bots Tab                # live bot cards with lock/unlock
        ├── System Tab              # all computers table with search
        ├── User Admin Tab          # user management + group assignment
        ├── Groups Tab              # group CRUD
        ├── Policies Tab            # policy editor with schedule UI
        ├── Audit Logs Tab          # searchable audit trail
        ├── Network Traffic Tab     # live connection monitoring
        └── MFA Setup Modal         # QR code provisioning
```

## Requirements

- Python 3.9+
- Windows 10/11 for the bot agent (uses Windows-specific APIs)
- Windows or Linux for the server (cross-platform Python)
- Administrator privileges for the bot agent
- All endpoints must reach the server on port 8000

Core Python dependencies:

```
fastapi, uvicorn, websockets, psutil, bcrypt, python-jose[cryptography], pyotp, pydantic, watchdog
```

Optional:

```
keyboard    # for emergency unlock hotkey
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/karthik-varma671/SentinelAI.git
cd SentinelAI
```

### 2. Install Dependencies

```bash
pip install fastapi uvicorn websockets psutil bcrypt python-jose[cryptography] pyotp pydantic watchdog
```

Optional emergency hotkey support:

```bash
pip install keyboard
```

## Quick Start

### Start the Server

```bash
cd server
python server.py
```

Default behavior:

- creates SQLite database with all tables
- creates default admin account (`admin` / `admin123`)
- creates default "Unassigned" organizational unit
- listens on `0.0.0.0:8000` for HTTP and WebSocket connections

### Deploy the Bot Agent

On each Windows endpoint:

1. Copy the `bot/` folder to the target machine

2. Edit `bot_end.py` and set your server address:

```python
SERVER_URL = "ws://YOUR_SERVER_IP:8000/ws"
BACKDOOR_IP = "YOUR_SERVER_IP"
```

3. Run as Administrator:

```bash
cd bot
python bot_end.py
```

4. Enter a username when prompted on first run

### Open the Dashboard

1. Open `dashboard/dashboard.html` in any browser

2. If the server is not on localhost, edit the API base URL:

```javascript
const API_BASE = 'http://YOUR_SERVER_IP:8000';
```

3. Log in with `admin` / `admin123`

## Configuration

### Bot Agent (`bot_end.py`)

```python
SERVER_URL = "ws://10.165.201.130:8000/ws"   # server WebSocket URL
ALERT_THRESHOLD = 0.5                         # score to send alert (0.0–1.0)
SCAN_INTERVAL = 5                             # seconds between scans
COMPLIANCE_GRACE_PERIOD = 30                  # seconds before compliance alert
BACKDOOR_IP = "10.165.201.130"               # IP allowed during isolation
```

Suspicious process name patterns can be modified in the `SUSPICIOUS_NAMES` list.

### Server (`server.py`)

```python
SECRET_KEY = "change-this-in-production-please-use-a-long-random-string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
AUTOLOCK_THRESHOLD = 0.6    # threat score for automatic lockdown
DB_FILE = "sentinelai.db"
```

Generate a production secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Dashboard (`dashboard.html`)

```javascript
const API_BASE = 'http://localhost:8000';
```

## Threat Detection

The bot scans all running processes every 5 seconds:

- **Name-based:** matches against known malicious patterns (ransomware, miners, torrents, etc.)
- **Behavioral:** flags processes consuming >50% CPU

Scoring:

```
Each suspicious name match   →  +0.3
Each high-CPU process (>50%) →  +0.3
Maximum score                →  1.0 (capped)

Score ≥ 0.5  →  alert sent to server
Score ≥ 0.6  →  server triggers automatic lockdown
```

## Lockdown System

When lockdown is triggered (automatically or manually):

1. **Full-screen overlay** — black screen with red lockdown message, cannot be closed or alt-tabbed
2. **Input blocked** — keyboard and mouse disabled via Windows `BlockInput` API
3. **Network isolated** — all outbound traffic blocked except DNS, DHCP, and server communication
4. **Forensics captured** — complete system snapshot taken and uploaded to server

Properties:

- persists across reboots (state saved to `locked_state.json`)
- survives WebSocket reconnections
- emergency unlock via `Ctrl+Alt+Shift+U`
- remote unlock from dashboard

## Policy System

Policies are rules created by admins and automatically pushed to bots via WebSocket.

### Targeting

| Target Type | Example         | Matches                              |
|-------------|-----------------|--------------------------------------|
| `all`       | `*`             | every connected endpoint             |
| `user`      | `john`          | endpoint where user `john` is active |
| `group`     | `developers`    | all endpoints in the group           |
| `machine`   | `<bot-id>`      | a specific machine                   |
| `ou`        | `Finance`       | all machines in the OU               |

### Rule Types

**Block processes:**
```json
{ "block_processes": ["notepad.exe", "steam.exe"] }
```

**Require processes:**
```json
{ "required_processes": ["MsMpEng.exe"] }
```

**Block USB storage:**
```json
{ "block_usb": true }
```

**Folder access control:**
```json
{
  "folder_rules": [
    { "path": "C:\\Data", "target": "user", "target_value": "intern", "permission": "R" }
  ]
}
```

**Time-based scheduling:**
```json
{ "schedule": { "days": [0,1,2,3,4], "start": "09:00", "end": "17:00" } }
```

Policies support versioning. Every update saves the previous version, and admins can rollback to any prior version.

## API Usage

The server exposes a REST API on port 8000. All authenticated endpoints require a JWT bearer token.

### Authentication

| Method | Endpoint        | Description                          |
|--------|-----------------|--------------------------------------|
| `POST` | `/register`     | create a new user account            |
| `POST` | `/login`        | authenticate and receive JWT         |
| `POST` | `/login-mfa`    | complete MFA authentication          |
| `POST` | `/mfa/enable`   | enable TOTP MFA for current user     |
| `POST` | `/mfa/disable`  | disable MFA for current user         |
| `POST` | `/mfa/verify`   | verify a TOTP code                   |

### Bot Control

| Method | Endpoint                        | Description                    | Min Role |
|--------|---------------------------------|--------------------------------|----------|
| `POST` | `/lockdown/{bot_id}`            | send lockdown command          | Analyst  |
| `POST` | `/unlock/{bot_id}`              | send unlock command            | Analyst  |
| `GET`  | `/bots`                         | list active bot IDs            | Viewer   |
| `GET`  | `/computers`                    | list all registered computers  | Viewer   |
| `PUT`  | `/computers/{bot_id}/ou`        | assign computer to OU          | Analyst  |
| `PUT`  | `/bots/{bot_id}/displayname`    | set display name               | Analyst  |
| `PUT`  | `/bots/{bot_id}/department`     | set department                 | Analyst  |

### Policies

| Method   | Endpoint                                  | Description             | Min Role |
|----------|-------------------------------------------|-------------------------|----------|
| `GET`    | `/policies`                               | list all policies       | Analyst  |
| `POST`   | `/policies`                               | create a policy         | Admin    |
| `PUT`    | `/policies/{id}`                          | update a policy         | Analyst  |
| `DELETE` | `/policies/{id}`                          | delete a policy         | Admin    |
| `GET`    | `/policies/{id}/versions`                 | get version history     | Analyst  |
| `POST`   | `/policies/{id}/rollback/{version_id}`    | rollback to version     | Admin    |

### Users, Groups & OUs

| Method   | Endpoint                          | Description                  | Min Role |
|----------|-----------------------------------|------------------------------|----------|
| `GET`    | `/users`                          | list all users               | Admin    |
| `DELETE` | `/users/{id}`                     | delete a user                | Admin    |
| `PUT`    | `/users/{id}/role`                | change user role             | Admin    |
| `PUT`    | `/users/{id}/disable`             | enable/disable a user        | Admin    |
| `GET`    | `/groups`                         | list all groups              | Analyst  |
| `POST`   | `/groups`                         | create a group               | Admin    |
| `PUT`    | `/groups/{id}`                    | update a group               | Admin    |
| `DELETE` | `/groups/{id}`                    | delete a group               | Admin    |
| `POST`   | `/users/{uid}/groups/{gid}`       | add user to group            | Admin    |
| `DELETE` | `/users/{uid}/groups/{gid}`       | remove user from group       | Admin    |
| `GET`    | `/organizational-units`           | list all OUs                 | Viewer   |
| `POST`   | `/organizational-units`           | create an OU                 | Admin    |
| `PUT`    | `/organizational-units/{id}`      | update an OU                 | Admin    |
| `DELETE` | `/organizational-units/{id}`      | delete an OU                 | Admin    |

### Monitoring & Data

| Method | Endpoint                       | Description                    | Min Role |
|--------|--------------------------------|--------------------------------|----------|
| `GET`  | `/audit`                       | query audit logs (filterable)  | Analyst  |
| `GET`  | `/network-traffic`             | query network traffic          | Analyst  |
| `GET`  | `/forensics`                   | list forensic snapshots        | Analyst  |
| `GET`  | `/forensics/{id}/download`     | download forensic snapshot     | Analyst  |

Example login:

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

## WebSocket Protocol

Endpoint: `ws://<server-ip>:8000/ws`

All messages are JSON objects with a `type` field.

### Bot → Server

| Type                | When Sent              | Key Fields                                     |
|---------------------|------------------------|-------------------------------------------------|
| `register`          | on connection          | `bot_id`, `username`                            |
| `alert`             | threat detected        | `threat_score`, `suspicious_processes`           |
| `enforcement`       | process killed         | `policy_id`, `policy_name`, `action`, `target`   |
| `compliance_alert`  | required process missing | `process`, `missing_duration`                  |
| `session_status`    | every 30 seconds       | `logged_in`, `session_user`                     |
| `network_traffic`   | every 30 seconds       | `connections[]`                                 |
| `forensics`         | on lockdown            | `data` (full snapshot)                          |
| `emergency_unlock`  | hotkey press           | `bot_id`, `username`                            |
| `ping`              | every 60 seconds       | heartbeat                                       |

### Server → Bot

| Type             | When Sent                  | Effect                                    |
|------------------|----------------------------|-------------------------------------------|
| `lockdown`       | manual or auto-trigger     | activates full lockdown sequence          |
| `unlock`         | admin command              | deactivates lockdown, restores operation  |
| `policy_update`  | on connect or policy change | bot updates local policy cache           |

## Database Schema

The server uses SQLite with 9 tables:

- `users` — accounts with bcrypt passwords, TOTP secrets, roles
- `groups` — logical user collections
- `user_groups` — many-to-many user–group memberships
- `organizational_units` — hierarchical computer organization
- `computers` — registered endpoints with OU assignment
- `policies` — active enforcement rules
- `policy_versions` — version history for rollback
- `audit_log` — timestamped action log
- `network_traffic` — per-connection traffic records
- `forensics` — forensic snapshot metadata and file paths

## Auto-Generated Runtime Files

These files are created during operation and excluded from Git:

| File                  | Location   | Purpose                                |
|-----------------------|------------|----------------------------------------|
| `bot_id.txt`          | `bot/`     | unique bot UUID                        |
| `bot_user.txt`        | `bot/`     | username entered during setup          |
| `locked_state.json`   | `bot/`     | lockdown persistence                   |
| `sentinelai.db`       | `server/`  | SQLite database                        |
| `forensics/`          | `server/`  | forensic snapshot JSON files           |
| `forensics_*.json`    | `bot/`     | local forensic snapshots               |

## Security Considerations

Implemented:

- JWT authentication with HS256 signing
- bcrypt password hashing with random salt
- TOTP multi-factor authentication (RFC 6238)
- role-based access control (Admin > Analyst > Viewer)
- full audit trail for all actions
- Windows Firewall network isolation on lockdown
- lockdown state persistence across reboots

Production hardening required:

- replace default `SECRET_KEY` with a random token
- change default admin password immediately
- deploy behind a reverse proxy with TLS (use `wss://` for WebSocket)
- restrict CORS `allow_origins` to your dashboard domain
- migrate from SQLite to PostgreSQL for scale
- add rate limiting on `/login`
- sanitize shell command arguments (`icacls`, `netsh`)
- add bot authentication (shared secrets or certificates)

## Tech Stack

| Layer         | Technology                    | Purpose                              |
|---------------|-------------------------------|--------------------------------------|
| Bot Agent     | Python 3, asyncio             | async monitoring event loop          |
|               | psutil                        | process and system monitoring        |
|               | websockets                    | persistent server connection         |
|               | tkinter                       | full-screen lockdown overlay         |
|               | ctypes (Win32)                | BlockInput API                       |
|               | subprocess + netsh            | firewall rule management             |
|               | winreg                        | registry access (USB, autoruns)      |
|               | watchdog                      | file system event monitoring         |
|               | keyboard                      | emergency unlock hotkey              |
| Server        | FastAPI                       | async web framework                  |
|               | uvicorn                       | ASGI server with WebSocket support   |
|               | SQLite                        | embedded relational database         |
|               | python-jose                   | JWT token management                 |
|               | bcrypt                        | secure password hashing              |
|               | pyotp                         | TOTP multi-factor authentication     |
|               | pydantic                      | data validation and serialization    |
| Dashboard     | HTML5/CSS3                    | responsive dark-themed UI            |
|               | vanilla JavaScript            | no framework dependencies            |
|               | QRCode.js (CDN)               | QR code generation for MFA setup     |

## Troubleshooting

**Bot can't connect to server:**
Verify `SERVER_URL` in `bot_end.py`, ensure the server is running, check that port 8000 is open, and test with `curl http://SERVER_IP:8000/docs`.

**Bot doesn't start / UAC prompt fails:**
The bot requires administrator privileges. Right-click → "Run as administrator" or accept the UAC prompt.

**Dashboard shows "Login failed":**
Verify `API_BASE` in `dashboard.html`, check server accessibility, try default credentials (`admin` / `admin123`), and check the browser console for CORS errors.

**Lockdown won't release / machine stuck:**
Press `Ctrl+Alt+Shift+U` (emergency hotkey). If that fails, force-reboot and delete `locked_state.json` before the bot restarts. Booting into Safe Mode prevents the bot from auto-starting.

**Policies not being enforced:**
Check that the policy is enabled, the target matches the bot (user, group, OU, machine), the schedule is active, and the bot is connected. Check bot console output for "Received X policies".

**Emergency hotkey not working:**
Install the keyboard library: `pip install keyboard`. It requires admin privileges.

---

**SentinelAI** — Autonomous Endpoint Defence Platform

Made by [Karthik Varma](https://github.com/karthik-varma671)
