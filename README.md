<![CDATA[<div align="center">

# 🛡️ SentinelAI

### Autonomous Endpoint Security & Threat Response Platform

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--Time-4FC08D?style=for-the-badge&logo=socketdotio&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-Endpoint-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

<br>

**SentinelAI** is an enterprise-grade, real-time endpoint security platform that monitors Windows machines, detects threats autonomously, enforces organizational policies, and performs automated incident response — all controlled from a centralized web dashboard.

<br>

*Think of it as your organization's own lightweight AI-powered security operations center (SOC) — watching every endpoint, every process, every network connection, 24/7.*

<br>

[🚀 Quick Start](#-quick-start) · [✨ Features](#-features) · [🏗️ Architecture](#️-architecture) · [📖 How It Works](#-how-it-works) · [⚙️ Configuration](#️-configuration) · [🔌 API Docs](#-api-reference) · [🔐 Security](#-security)

</div>

---

## 📋 Table of Contents

- [What is SentinelAI?](#-what-is-sentinelai)
- [Why SentinelAI?](#-why-sentinelai)
- [Features](#-features)
- [Architecture](#️-architecture)
- [How It Works](#-how-it-works)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Configuration Reference](#️-configuration)
- [Dashboard Guide](#-dashboard-guide)
- [Policy System Deep Dive](#-policy-system-deep-dive)
- [Forensics & Incident Response](#-forensics--incident-response)
- [API Reference](#-api-reference)
- [WebSocket Protocol](#-websocket-protocol)
- [Security Considerations](#-security)
- [Tech Stack](#️-tech-stack)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧠 What is SentinelAI?

SentinelAI is a **three-component security platform** designed to protect Windows endpoints in an organizational network:

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   🖥️ Bot     │         │   🌐 Server  │         │   📊 Dashboard│
│   Agent      │◄───────►│   (C2)       │◄────────│   (Web UI)   │
│              │   WS    │              │   REST  │              │
│ Runs on each │         │ Central hub  │         │ Admin panel  │
│ endpoint     │         │ for all bots │         │ for humans   │
└──────────────┘         └──────────────┘         └──────────────┘
```

| Component | What it does | Where it runs |
|-----------|-------------|---------------|
| **Bot Agent** (`bot_end.py`) | Monitors processes, enforces policies, locks down machines, captures forensics | On every Windows endpoint you want to protect |
| **Server** (`server.py`) | Manages bots, authenticates admins, stores data, makes lockdown decisions | On a central server (can be Linux or Windows) |
| **Dashboard** (`dashboard.html`) | Visual interface for admins to monitor, control bots, manage policies | Opened in any web browser |

**In simple terms:** You install the bot on every computer in your organization. The bot constantly watches what's happening on that computer and reports back to the server. If something suspicious is detected, the system can automatically lock down the machine. Admins use the dashboard to see everything, create rules, and take manual action.

---

## 💡 Why SentinelAI?

Most endpoint security solutions are expensive, complex, and require cloud subscriptions. SentinelAI is:

| | Traditional EDR | SentinelAI |
|---|---|---|
| **Cost** | Expensive per-endpoint licensing | Free & open source |
| **Deployment** | Heavy agent installation | Single Python script |
| **Cloud dependency** | Requires cloud connectivity | Fully self-hosted, works on LAN |
| **Customization** | Limited to vendor features | Fully customizable policies & rules |
| **Transparency** | Black-box detection | Open source, you see exactly what it does |
| **Setup time** | Days to weeks | Minutes |

### Use Cases

- 🏫 **Educational Labs** — Prevent students from running unauthorized software
- 🏢 **Corporate Networks** — Enforce security policies across all workstations
- 🔬 **Research Environments** — Lock down sensitive machines during off-hours
- 🏥 **Compliance-Heavy Industries** — Ensure required security software is always running
- 🎓 **Cybersecurity Training** — Learn endpoint security concepts hands-on

---

## ✨ Features

### 🔍 1. Real-Time Threat Detection

The bot agent continuously scans all running processes on the endpoint every **5 seconds** (configurable). It looks for two types of threats:

**Name-Based Detection:** Processes with names matching known malicious patterns are flagged:
```
ransomware, encrypt, decrypt, locky, wannacry, cerber, cryptolocker,
badrabbit, notpetya, gandcrab, teslacrypt, torrent, miner, coin, xmrig
```

**Behavioral Detection:** Processes consuming more than **50% CPU** are flagged as potentially malicious (crypto miners, runaway malware, etc.)

**How the threat score works:**
```
Each suspicious process name match  →  +0.3 to threat score
Each high-CPU process (>50%)        →  +0.3 to threat score
Maximum score                       →  1.0 (capped)

If score ≥ 0.5  →  Alert sent to server
If score ≥ 0.6  →  Server triggers AUTOMATIC lockdown
```

> **Example:** If a process named `xmrig_miner.exe` is found running at 80% CPU, the threat score would be 0.6 (0.3 for name match + 0.3 for high CPU), which automatically triggers a lockdown.

---

### 🔒 2. Endpoint Lockdown System

When a lockdown is triggered (automatically or manually), **four things happen simultaneously:**

```
┌─────────────────────────────────────────────────┐
│              LOCKDOWN SEQUENCE                   │
│                                                  │
│  1. 🖥️  Full-screen overlay appears              │
│     → Black screen with red "SYSTEM LOCKDOWN"    │
│     → Cannot be closed, alt-tabbed, or minimized │
│                                                  │
│  2. ⌨️  Input blocked                            │
│     → Keyboard and mouse are disabled            │
│     → Uses Windows BlockInput() API              │
│                                                  │
│  3. 🌐 Network isolated                          │
│     → All outbound traffic blocked               │
│     → Only DNS, DHCP, and server IP allowed      │
│     → Prevents data exfiltration                 │
│                                                  │
│  4. 🔬 Forensics captured (background)           │
│     → Full system snapshot taken                 │
│     → Sent to server for analysis                │
└─────────────────────────────────────────────────┘
```

**Key lockdown properties:**
- **Persistent across reboots** — Lockdown state is saved to `locked_state.json`. If the machine restarts, the bot re-applies the lockdown on startup
- **Survives reconnection** — If the WebSocket connection drops and reconnects, lockdown is re-applied
- **Emergency escape** — Physical users can press `Ctrl+Alt+Shift+U` to emergency-unlock (the server is notified)
- **Remote unlock** — Admins can unlock from the dashboard at any time

---

### 📜 3. Centralized Policy Engine

Policies are rules created by admins that are **automatically pushed to bots** and **enforced in real-time**. When you create, update, or delete a policy on the server, all connected bots immediately receive the change.

#### Policy Targeting

Each policy specifies **who it applies to:**

| Target Type | Target Value | What it matches |
|-------------|-------------|-----------------|
| `all` | `*` | Every connected endpoint |
| `user` | `john` | Only the endpoint where user `john` is logged in |
| `group` | `developers` | All endpoints with users in the `developers` group |
| `machine` | `<bot-id>` | A specific machine by its unique bot ID |
| `ou` | `Finance` | All machines in the `Finance` organizational unit |

#### What Can Policies Do?

**a) Block Processes**
```json
{
  "block_processes": ["notepad.exe", "calc.exe", "steam.exe"]
}
```
Any process in this list is **immediately terminated** when detected. The bot checks every scan cycle (5 seconds). An enforcement log is sent to the server and recorded in the audit trail.

**b) Require Processes**
```json
{
  "required_processes": ["MsMpEng.exe", "CrowdStrike.exe"]
}
```
If any listed process is **not running**, the bot starts tracking how long it's been missing. After the grace period (30 seconds by default), a **compliance alert** is sent to the server. This is useful for ensuring antivirus or security software is always active.

**c) Block USB Storage**
```json
{
  "block_usb": true
}
```
Disables USB mass storage by modifying the Windows registry key `HKLM\SYSTEM\CurrentControlSet\Services\USBSTOR\Start`. Setting it to `4` disables USB storage; `3` re-enables it. This prevents data theft via USB drives.

**d) Folder Access Control (RBAC)**
```json
{
  "folder_rules": [
    {
      "path": "C:\\ConfidentialReports",
      "target": "user",
      "target_value": "intern_john",
      "permission": "R"
    },
    {
      "path": "C:\\SharedDocs",
      "target": "group",
      "target_value": "Everyone",
      "permission": "D"
    }
  ]
}
```
Uses Windows `icacls` to set NTFS permissions. Permissions: `R` (Read), `W` (Write), `X` (Execute), `F` (Full Control), `D` (Deny All).

**e) Time-Based Scheduling**
```json
{
  "schedule": {
    "days": [0, 1, 2, 3, 4],
    "start": "09:00",
    "end": "17:00"
  }
}
```
Days are 0-indexed (0=Monday, 6=Sunday). Policies with schedules only enforce during the specified time windows.

#### Complete Policy Example

Here's a real-world policy that blocks gaming and torrent apps during work hours for the Finance department:

```json
{
  "name": "Finance Work Hours Restriction",
  "description": "Block entertainment and P2P software during business hours",
  "target_type": "ou",
  "target_value": "Finance",
  "rule": {
    "block_processes": [
      "steam.exe",
      "epicgameslauncher.exe",
      "utorrent.exe",
      "bittorrent.exe",
      "discord.exe"
    ],
    "required_processes": ["MsMpEng.exe"],
    "block_usb": true,
    "folder_rules": [
      {
        "path": "C:\\FinanceData",
        "target": "group",
        "target_value": "Interns",
        "permission": "R"
      }
    ],
    "schedule": {
      "days": [0, 1, 2, 3, 4],
      "start": "08:00",
      "end": "18:00"
    }
  },
  "enabled": true
}
```

#### Policy Versioning & Rollback

Every time a policy is updated, the **previous version is saved** in the `policy_versions` table. Admins can:
- View the complete change history of any policy
- **Rollback** to any previous version with a single API call
- The rollback itself is also versioned (so you can undo a rollback)

---

### 👥 4. User & Access Management

#### Role-Based Access Control

SentinelAI has three user roles with escalating privileges:

```
┌─────────────────────────────────────────────────────────┐
│                    ROLE HIERARCHY                        │
│                                                          │
│  👁️ Viewer   → Can view bots, computers, dashboards      │
│                 Cannot take any actions                   │
│                                                          │
│  🔍 Analyst  → Everything Viewer can do, PLUS:           │
│                 Can lockdown/unlock bots                  │
│                 Can view/edit policies                    │
│                 Can view audit logs & network traffic     │
│                 Can view forensics                        │
│                                                          │
│  👑 Admin    → Everything Analyst can do, PLUS:          │
│                 Can create/delete users                   │
│                 Can manage groups & OUs                   │
│                 Can create/delete policies                │
│                 Can assign roles                          │
│                 Can rollback policies                     │
└─────────────────────────────────────────────────────────┘
```

#### Multi-Factor Authentication (MFA)

SentinelAI supports TOTP-based MFA (compatible with Google Authenticator, Authy, Microsoft Authenticator):

```
Admin enables MFA → QR code generated → Scan with authenticator app
                                          ↓
                     Next login requires: Password + 6-digit TOTP code
```

**Setup flow:**
1. Admin clicks "🔐 MFA Setup" in the dashboard
2. A QR code and secret key are displayed
3. Scan with any TOTP authenticator app
4. Enter the 6-digit code to verify
5. MFA is now active — all future logins require the code

#### Groups & Organizational Units

**Groups** are logical collections of users (e.g., `Developers`, `Finance`, `Interns`). Policies can target groups, so when you add a user to a group, they automatically inherit all policies targeting that group.

**Organizational Units (OUs)** are hierarchical structures for organizing **computers** (not users). Think of them like Active Directory OUs. Each computer belongs to exactly one OU, and policies can target OUs.

```
Organization
├── Headquarters
│   ├── Finance
│   ├── Engineering
│   └── HR
├── Branch Office
│   ├── Sales
│   └── Support
└── Unassigned (default)
```

---

### 📊 5. Network Traffic Monitoring

Every 30 seconds, the bot agent captures all **established network connections** on the endpoint and sends them to the server:

```
For each connection, the following is captured:
  • Source IP and Port
  • Destination IP and Port
  • Protocol (TCP/UDP)
  • Process name that owns the connection
  • Process ID (PID)
```

This data is stored in the server's database and can be queried from the dashboard with filters:
- By bot ID
- By username
- By date range
- With configurable result limits

**Use case:** If an endpoint is compromised, you can retroactively analyze what external IPs it was communicating with, which processes were making connections, and when the suspicious activity started.

---

### 🔬 6. Forensic Snapshot System

When a lockdown occurs, the bot automatically captures a **comprehensive forensic snapshot** containing:

| Data Collected | Details |
|----------------|---------|
| **Running Processes** | PID, name, executable path, command line arguments, CPU %, memory % |
| **Network Connections** | All active connections with local/remote addresses, status, owning PID |
| **Windows Services** | Names of all registered services (running and stopped) |
| **Scheduled Tasks** | All scheduled tasks registered on the system |
| **Installed Software** | All software from the Windows registry (Add/Remove Programs) |
| **Autorun Entries** | All programs configured to run at startup (Run/RunOnce registry keys) |
| **Event Log Errors** | Last 10 system event log errors |

The snapshot is:
1. **Saved locally** on the endpoint as `forensics_<bot_id>_<timestamp>.json`
2. **Uploaded to the server** via WebSocket
3. **Stored on the server** in the `forensics/` directory
4. **Downloadable** via the REST API for later analysis

> **Why is this important?** When a machine is locked down due to a threat, you need to understand exactly what was running at the time of the incident. The forensic snapshot gives you a complete picture of the system state at the moment of compromise.

---

### 📝 7. Comprehensive Audit Logging

Every significant action in the system is logged with a timestamp, user, action type, and details:

| Event Type | Examples |
|------------|---------|
| **Authentication** | Login, MFA enable/disable |
| **Bot Control** | Manual lockdown, manual unlock, emergency unlock |
| **Policy Management** | Create, update, delete, rollback policies |
| **User Management** | Create, delete, disable users; role changes |
| **Group Management** | Create/delete groups; user-group membership changes |
| **Automated Actions** | Process termination, compliance alerts, IPS blocks |
| **System Events** | Logon events (success/failure), file events |

Audit logs are searchable and filterable by:
- Username
- Action type
- Date/time range
- Result count limit

---

## 🏗️ Architecture

### System Architecture Diagram

```
╔════════════════════════════════════════════════════════════════════╗
║                        ADMIN / ANALYST                             ║
║                                                                     ║
║    ┌────────────────────────────────────────┐                       ║
║    │          📊 Dashboard (Web UI)          │                       ║
║    │         dashboard/dashboard.html        │                       ║
║    │                                         │                       ║
║    │  • Bots View       • Policy Management  │                       ║
║    │  • System View     • Audit Logs         │                       ║
║    │  • User Admin      • Network Traffic    │                       ║
║    │  • Group Admin     • MFA Setup          │                       ║
║    └────────────────┬───────────────────────┘                       ║
║                     │                                                ║
║                     │ REST API (HTTP)                                ║
║                     │ JWT Bearer Authentication                      ║
║                     ▼                                                ║
║    ┌────────────────────────────────────────┐                       ║
║    │         🌐 FastAPI Server (C2)          │                       ║
║    │           server/server.py              │                       ║
║    │                                         │                       ║
║    │  ┌──────────┐  ┌──────────────────┐    │                       ║
║    │  │ Auth     │  │ Policy Engine    │    │                       ║
║    │  │ • JWT    │  │ • CRUD + Version │    │                       ║
║    │  │ • bcrypt │  │ • Target resolve │    │                       ║
║    │  │ • TOTP   │  │ • Auto-broadcast │    │                       ║
║    │  └──────────┘  └──────────────────┘    │                       ║
║    │  ┌──────────┐  ┌──────────────────┐    │                       ║
║    │  │ WebSocket│  │ Data Store       │    │                       ║
║    │  │ Manager  │  │ • SQLite DB      │    │                       ║
║    │  │ • Track  │  │ • Forensic files │    │                       ║
║    │  │ • Route  │  │ • Audit logs     │    │                       ║
║    │  └──────────┘  └──────────────────┘    │                       ║
║    └───────┬────────────┬───────────┬───────┘                       ║
║            │            │           │                                ║
║            │ WebSocket  │ WebSocket │ WebSocket                      ║
║            │ (persist)  │ (persist) │ (persist)                      ║
║            ▼            ▼           ▼                                ║
║    ┌────────────┐ ┌────────────┐ ┌────────────┐                    ║
║    │ 🖥️ Bot #1  │ │ 🖥️ Bot #2  │ │ 🖥️ Bot #N  │                    ║
║    │            │ │            │ │            │                    ║
║    │ ┌────────┐ │ │ ┌────────┐ │ │ ┌────────┐ │                    ║
║    │ │Monitor │ │ │ │Monitor │ │ │ │Monitor │ │                    ║
║    │ │Process │ │ │ │Process │ │ │ │Process │ │                    ║
║    │ │Scanner │ │ │ │Scanner │ │ │ │Scanner │ │                    ║
║    │ └────────┘ │ │ └────────┘ │ │ └────────┘ │                    ║
║    │ ┌────────┐ │ │ ┌────────┐ │ │ ┌────────┐ │                    ║
║    │ │Policy  │ │ │ │Policy  │ │ │ │Policy  │ │                    ║
║    │ │Enforcer│ │ │ │Enforcer│ │ │ │Enforcer│ │                    ║
║    │ └────────┘ │ │ └────────┘ │ │ └────────┘ │                    ║
║    │ ┌────────┐ │ │ ┌────────┐ │ │ ┌────────┐ │                    ║
║    │ │Lockdown│ │ │ │Lockdown│ │ │ │Lockdown│ │                    ║
║    │ │Engine  │ │ │ │Engine  │ │ │ │Engine  │ │                    ║
║    │ └────────┘ │ │ └────────┘ │ │ └────────┘ │                    ║
║    │ ┌────────┐ │ │ ┌────────┐ │ │ ┌────────┐ │                    ║
║    │ │Forensic│ │ │ │Forensic│ │ │ │Forensic│ │                    ║
║    │ │Capture │ │ │ │Capture │ │ │ │Capture │ │                    ║
║    │ └────────┘ │ │ └────────┘ │ │ └────────┘ │                    ║
║    └────────────┘ └────────────┘ └────────────┘                    ║
║                                                                     ║
╚════════════════════════════════════════════════════════════════════╝
```

### Communication Flow

```
BOT STARTUP:
  Bot → Server:  { type: "register", bot_id: "uuid", username: "john" }
  Server → Bot:  { type: "policy_update", policies: [...] }

ONGOING MONITORING (every 5 seconds):
  Bot scans processes → Calculates threat score
  If threat score ≥ 0.5:
    Bot → Server:  { type: "alert", threat_score: 0.7, suspicious_processes: [...] }
    If threat score ≥ 0.6:
      Server → Bot:  { type: "lockdown" }

PERIODIC REPORTS (every 30 seconds):
  Bot → Server:  { type: "session_status", logged_in: true, session_user: "john" }
  Bot → Server:  { type: "network_traffic", connections: [...] }

POLICY CHANGES (on-demand):
  Admin updates policy via dashboard
  Server → ALL Bots:  { type: "policy_update", policies: [...] }

MANUAL ACTIONS:
  Admin clicks "Lockdown" in dashboard
  Dashboard → Server:  POST /lockdown/{bot_id}
  Server → Bot:  { type: "lockdown" }
```

---

## 📖 How It Works

### Step-by-Step: What happens when you deploy SentinelAI

#### Phase 1: Server Initialization
```
1. Server starts → Creates SQLite database with all tables
2. Default admin account created (admin / admin123)
3. Default "Unassigned" OU created
4. Server listens on port 8000 for HTTP + WebSocket connections
```

#### Phase 2: Bot Agent Connection
```
1. Bot starts → Requires admin privileges (auto-elevates via UAC)
2. Generates unique UUID (saved to bot_id.txt for persistence)
3. Prompts for username on first run (saved to bot_user.txt)
4. Waits 10 seconds for network initialization
5. Connects to server via WebSocket
6. Sends registration message with bot_id and username
7. Server auto-creates user account if not exists
8. Server assigns bot to "Unassigned" OU
9. Server sends current policies to the bot
10. Bot starts monitoring loops:
    - Process scanner (every 5 seconds)
    - Session status reporter (every 30 seconds)
    - Network traffic reporter (every 30 seconds)
    - Heartbeat ping (every 60 seconds)
```

#### Phase 3: Continuous Protection
```
Every 5 seconds, the bot:
  1. Scans all running processes
  2. Calculates threat score
  3. Sends alert if threshold exceeded
  4. Checks policies:
     - Terminates blocked processes
     - Checks required processes
     - Applies USB restrictions
     - Applies folder permissions
  5. Reports results to server
```

#### Phase 4: Incident Response (Automated)
```
High threat detected (score ≥ 0.6):
  1. Server sends lockdown command
  2. Bot creates full-screen overlay
  3. Bot blocks keyboard/mouse input
  4. Bot applies firewall isolation rules
  5. Bot captures complete forensic snapshot
  6. Bot uploads forensics to server
  7. Lockdown state saved to disk
  8. Admin notified via dashboard
  9. Admin reviews forensics
  10. Admin clicks "Unlock" when safe
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python** | Version 3.9 or higher |
| **OS (Bot)** | Windows 10/11 (uses Windows-specific APIs) |
| **OS (Server)** | Windows or Linux (Python-based, cross-platform) |
| **Privileges** | Administrator (for bot agent) |
| **Network** | All endpoints must be able to reach the server on port 8000 |

### Step 1: Clone the Repository

```bash
git clone https://github.com/karthik-varma671/SentinelAI.git
cd SentinelAI
```

### Step 2: Install Python Dependencies

```bash
pip install fastapi uvicorn websockets psutil bcrypt python-jose[cryptography] pyotp pydantic watchdog
```

**Optional (for emergency hotkey):**
```bash
pip install keyboard
```

### Step 3: Start the Central Server

```bash
cd server
python server.py
```

You should see:
```
✅ Created default admin user: admin / admin123
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The server is now ready to accept bot connections and dashboard requests.

### Step 4: Configure and Deploy the Bot Agent

**On each Windows endpoint you want to protect:**

1. Copy the `bot/` folder to the target machine

2. Open `bot_end.py` and update the server address:
   ```python
   # Change this to your server's IP address
   SERVER_URL = "ws://YOUR_SERVER_IP:8000/ws"
   BACKDOOR_IP = "YOUR_SERVER_IP"
   ```

3. Run as Administrator:
   ```bash
   cd bot
   python bot_end.py
   ```

4. On first run, enter a username when prompted:
   ```
   First run configuration:
   Username: john_workstation
   ```

5. The bot will connect and you should see:
   ```
   Running with administrator privileges.
   Reported username: john_workstation
   Unique bot ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
   Connected to server. Registering as a1b2c3d4...
   📋 Received 0 policies
   ```

### Step 5: Open the Dashboard

1. Open `dashboard/dashboard.html` in any web browser

2. **Important:** If your server is not on `localhost`, edit line 241 of `dashboard.html`:
   ```javascript
   const API_BASE = 'http://YOUR_SERVER_IP:8000';
   ```

3. Log in with the default credentials:
   - **Username:** `admin`
   - **Password:** `admin123`

4. You should now see your connected bots in the "Bots" tab! 🎉

---

## 📁 Project Structure

```
SentinelAI/
│
├── 📄 README.md                  ← You are here
├── 📄 .gitignore                 ← Git ignore rules
│
├── 🤖 bot/                       ← ENDPOINT AGENT
│   └── bot_end.py                ← Main bot script (742 lines)
│       ├── Configuration         ← Server URL, thresholds, scan intervals
│       ├── Persistent Identity   ← UUID generation, username storage
│       ├── Windows API           ← BlockInput, UAC elevation
│       ├── Overlay System        ← Tkinter full-screen lockdown UI
│       ├── Emergency Hotkey      ← Ctrl+Alt+Shift+U unlock
│       ├── Firewall Management   ← netsh rules for isolation
│       ├── Forensics Capture     ← Deep system snapshot
│       ├── Lockdown Engine       ← Lock/unlock orchestration
│       ├── Policy Enforcement    ← Process blocking, USB, folder RBAC
│       ├── Monitoring Loops      ← Process scanner, session, network
│       └── Main Connection Loop  ← WebSocket with auto-reconnect
│
├── 🌐 server/                    ← CENTRAL SERVER
│   └── server.py                 ← FastAPI server (1163 lines)
│       ├── Security Layer        ← JWT, bcrypt, TOTP
│       ├── Database Schema       ← 9 SQLite tables
│       ├── Pydantic Models       ← Request/response validation
│       ├── WebSocket Manager     ← Bot connection tracking
│       ├── Auth Endpoints        ← Register, login, MFA
│       ├── Bot Control           ← Lockdown, unlock, computer mgmt
│       ├── Policy CRUD           ← Create, read, update, delete, rollback
│       ├── User/Group/OU Mgmt    ← Full CRUD with RBAC
│       ├── Audit & Monitoring    ← Logs, network traffic, forensics
│       └── Server Startup        ← DB init, admin creation
│
└── 📊 dashboard/                 ← WEB DASHBOARD
    └── dashboard.html            ← Single-page application (866 lines)
        ├── Login (with MFA)      ← Two-step authentication UI
        ├── Bots Tab              ← Live bot cards with lock/unlock
        ├── System Tab            ← All computers table with search
        ├── User Admin Tab        ← User management + group assignment
        ├── Groups Tab            ← Group CRUD
        ├── Policies Tab          ← Policy editor with schedule UI
        ├── Audit Logs Tab        ← Searchable audit trail
        ├── Network Traffic Tab   ← Live connection monitoring
        └── MFA Setup Modal       ← QR code provisioning
```

### Auto-Generated Runtime Files

These files are created during operation and are **excluded from Git:**

| File | Location | Purpose | Created When |
|------|----------|---------|-------------|
| `bot_id.txt` | `bot/` | Unique bot UUID (persists across restarts) | First bot startup |
| `bot_user.txt` | `bot/` | Username entered during setup | First bot startup |
| `locked_state.json` | `bot/` | `{"locked": true/false}` | Any lockdown/unlock event |
| `sentinelai.db` | `server/` | SQLite database with all data | Server first startup |
| `forensics/` | `server/` | Forensic snapshot JSON files | Each lockdown event |
| `forensics_*.json` | `bot/` | Local forensic snapshots | Each lockdown event |

---

## ⚙️ Configuration

### Bot Agent Configuration (`bot_end.py`)

All configuration is at the top of the file:

```python
# ==================== CONFIGURATION ====================
SERVER_URL = "ws://10.165.201.130:8000/ws"   # Server WebSocket URL
ALERT_THRESHOLD = 0.5                         # Score to send alert
SCAN_INTERVAL = 5                             # Seconds between scans
COMPLIANCE_GRACE_PERIOD = 30                  # Seconds before compliance alert
BACKDOOR_IP = "10.165.201.130"               # IP allowed during isolation
```

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SERVER_URL` | string | `ws://10.165.201.130:8000/ws` | WebSocket URL of the central server. Must be `ws://` for unencrypted or `wss://` for TLS |
| `ALERT_THRESHOLD` | float | `0.5` | Minimum threat score to send an alert to the server. Range: 0.0 to 1.0 |
| `SCAN_INTERVAL` | int | `5` | Seconds between process scanning cycles. Lower = more responsive but higher CPU usage |
| `COMPLIANCE_GRACE_PERIOD` | int | `30` | Seconds a required process can be missing before triggering a compliance alert |
| `BACKDOOR_IP` | string | `10.165.201.130` | This IP is always allowed through the firewall, even during isolation mode. Set to your server's IP |

**Suspicious process names** can be modified in the `SUSPICIOUS_NAMES` list:
```python
SUSPICIOUS_NAMES = [
    "ransomware", "encrypt", "decrypt", "locky", "wannacry",
    "cerber", "cryptolocker", "badrabbit", "notpetya", "gandcrab",
    "teslacrypt", "torrent", "miner", "coin", "xmrig"
]
```

### Server Configuration (`server.py`)

```python
# ==================== SECURITY CONSTANTS ====================
SECRET_KEY = "change-this-in-production-please-use-a-long-random-string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SECRET_KEY` | string | *placeholder* | **MUST CHANGE** in production. Used to sign JWT tokens. Generate with: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ALGORITHM` | string | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30` | JWT token lifetime in minutes |
| `AUTOLOCK_THRESHOLD` | float | `0.6` | Threat score at which the server **automatically** sends a lockdown command |
| `DB_FILE` | string | `sentinelai.db` | SQLite database file path |

### Dashboard Configuration (`dashboard.html`)

```javascript
const API_BASE = 'http://localhost:8000';
```

Change `API_BASE` to point to your server's address if not running locally.

---

## 📊 Dashboard Guide

### Tab Overview

| Tab | Purpose | Auto-Refresh |
|-----|---------|-------------|
| **Bots** | Live view of connected bots with lock/unlock buttons | Every 3 seconds |
| **System** | Table of all registered computers (active or not) with search | Every 5 seconds |
| **User Admin** | Manage users, roles, and group assignments | On tab switch |
| **Groups** | Create and manage user groups | On tab switch |
| **Policies** | Create, edit, and manage enforcement policies | On tab switch |
| **Audit Logs** | Searchable log of all system actions | Manual refresh |
| **Network Traffic** | Live network connection data from all endpoints | Every 10 seconds |
| **🔐 MFA Setup** | Enable/disable multi-factor authentication | N/A |

### Bot Card States

```
┌──────────────────────────────────────────┐
│ 🟢 Connected  │ Bot is online and healthy │
│ 🔴 LOCKED     │ Bot is in lockdown mode   │
│ ⚫ Disconnected│ Bot is offline            │
└──────────────────────────────────────────┘
```

---

## 📜 Policy System Deep Dive

### Policy Lifecycle

```
Create Policy (Admin)
       │
       ▼
   Version 1 saved to policy_versions table
       │
       ▼
   Broadcasted to ALL connected bots
       │
       ▼
   Bots start enforcing immediately
       │
       ▼
   Admin edits policy
       │
       ▼
   Current version saved as Version 2
   New version becomes active
       │
       ▼
   Updated policy broadcasted to all bots
       │
       ▼
   If something goes wrong:
       │
       ▼
   Admin rolls back to Version 1
   Rollback saved as Version 3
   Rolled-back policy broadcasted
```

### Policy Resolution for a Bot

When a bot connects, the server determines which policies apply:

```python
# Pseudocode for policy resolution
applicable_policies = []

for policy in all_enabled_policies:
    if policy.target_type == "all":
        applicable_policies.append(policy)
    
    elif policy.target_type == "user" and policy.target_value == bot.username:
        applicable_policies.append(policy)
    
    elif policy.target_type == "machine" and policy.target_value == bot.bot_id:
        applicable_policies.append(policy)
    
    elif policy.target_type == "group":
        user_groups = get_groups_for_user(bot.username)
        if policy.target_value in user_groups:
            applicable_policies.append(policy)
    
    elif policy.target_type == "ou":
        bot_ou = get_ou_for_computer(bot.bot_id)
        if policy.target_value == bot_ou.name:
            applicable_policies.append(policy)

# All matching policies are merged and enforced simultaneously
```

---

## 🔬 Forensics & Incident Response

### Incident Response Workflow

```
1. DETECT
   └─ Threat score exceeds threshold
   └─ OR admin manually triggers lockdown

2. CONTAIN
   └─ Endpoint locked (overlay + input block)
   └─ Network isolated (firewall rules)
   └─ Only server communication allowed

3. CAPTURE
   └─ Full forensic snapshot taken:
      • All running processes with command lines
      • All network connections
      • All Windows services
      • All scheduled tasks
      • All installed software
      • All autorun entries
      • Recent system error events

4. ANALYZE
   └─ Forensic data uploaded to server
   └─ Admin reviews via API or downloads JSON
   └─ Network traffic history checked
   └─ Audit logs reviewed for timeline

5. REMEDIATE
   └─ Admin identifies the threat
   └─ Admin decides to unlock or keep locked
   └─ Policy updated to prevent recurrence
   └─ User notified

6. RECOVER
   └─ Admin sends unlock command
   └─ Overlay removed, input restored
   └─ Firewall rules restored to normal
   └─ Bot resumes normal monitoring
```

### Forensic Snapshot Structure

```json
{
  "bot_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "username": "john",
  "timestamp": 1712345678,
  "processes": [
    {
      "pid": 1234,
      "name": "suspicious.exe",
      "cpu_percent": 85.2,
      "memory_percent": 12.5,
      "exe": "C:\\Users\\john\\Downloads\\suspicious.exe",
      "cmdline": ["suspicious.exe", "--encrypt", "--all"]
    }
  ],
  "network_connections": [
    {
      "laddr": ["192.168.1.100", 49152],
      "raddr": ["185.45.67.89", 443],
      "status": "ESTABLISHED",
      "pid": 1234
    }
  ],
  "services": ["WinDefend", "Spooler", "USBSTOR", ...],
  "scheduled_tasks": ["\\Microsoft\\Windows\\UpdateOrchestrator\\..."],
  "installed_software": ["Google Chrome", "Python 3.11", ...],
  "autoruns": ["SecurityHealth: C:\\Windows\\System32\\..."],
  "event_log_errors": [
    {
      "id": "7034",
      "time": "2024-01-15T10:23:45",
      "source": "Service Control Manager",
      "message": "The Windows Defender service terminated unexpectedly"
    }
  ]
}
```

---

## 🔌 API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| `POST` | `/register` | Create a new user account | ❌ |
| `POST` | `/login` | Authenticate and receive JWT (or MFA prompt) | ❌ |
| `POST` | `/login-mfa` | Complete MFA authentication | ❌ |
| `POST` | `/mfa/enable` | Enable TOTP MFA for current user | ✅ |
| `POST` | `/mfa/disable` | Disable MFA for current user | ✅ |
| `POST` | `/mfa/verify` | Verify a TOTP code | ✅ |

<details>
<summary><strong>Login Example</strong></summary>

**Request:**
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**Response (no MFA):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Response (MFA enabled):**
```json
{
  "mfa_required": true,
  "temp_token": "eyJhbGciOiJIUzI1NiIs..."
}
```
</details>

---

### Bot Control Endpoints

| Method | Endpoint | Description | Min Role |
|--------|----------|-------------|---------|
| `POST` | `/lockdown/{bot_id}` | Send lockdown command to a bot | Analyst |
| `POST` | `/unlock/{bot_id}` | Send unlock command to a bot | Analyst |
| `GET` | `/bots` | List all active (connected) bot IDs | Viewer |
| `GET` | `/computers` | List all registered computers with details | Viewer |
| `PUT` | `/computers/{bot_id}/ou` | Assign a computer to an OU | Analyst |
| `PUT` | `/bots/{bot_id}/displayname` | Set a friendly display name | Analyst |
| `PUT` | `/bots/{bot_id}/department` | Set department name | Analyst |

<details>
<summary><strong>Lockdown Example</strong></summary>

```bash
curl -X POST http://localhost:8000/lockdown/a1b2c3d4-e5f6-7890 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response:**
```json
{
  "status": "Lockdown command sent to a1b2c3d4-e5f6-7890"
}
```
</details>

---

### Policy Endpoints

| Method | Endpoint | Description | Min Role |
|--------|----------|-------------|---------|
| `GET` | `/policies` | List all policies | Analyst |
| `POST` | `/policies` | Create a new policy | Admin |
| `PUT` | `/policies/{id}` | Update an existing policy | Analyst |
| `DELETE` | `/policies/{id}` | Delete a policy | Admin |
| `GET` | `/policies/{id}/versions` | Get version history | Analyst |
| `POST` | `/policies/{id}/rollback/{version_id}` | Rollback to a previous version | Admin |

<details>
<summary><strong>Create Policy Example</strong></summary>

```bash
curl -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block Gaming Apps",
    "description": "Prevent gaming software from running",
    "target_type": "all",
    "target_value": "*",
    "rule": {
      "block_processes": ["steam.exe", "epicgameslauncher.exe", "origin.exe"]
    },
    "enabled": true
  }'
```

**Response:**
```json
{
  "message": "Policy created",
  "id": 1
}
```
</details>

---

### User & Group Endpoints

| Method | Endpoint | Description | Min Role |
|--------|----------|-------------|---------|
| `GET` | `/users` | List all users | Admin |
| `DELETE` | `/users/{id}` | Delete a user | Admin |
| `PUT` | `/users/{id}/role` | Change user role | Admin |
| `PUT` | `/users/{id}/disable` | Enable/disable a user | Admin |
| `GET` | `/groups` | List all groups | Analyst |
| `POST` | `/groups` | Create a group | Admin |
| `PUT` | `/groups/{id}` | Update a group | Admin |
| `DELETE` | `/groups/{id}` | Delete a group | Admin |
| `GET` | `/users/{id}/groups` | List user's group memberships | Analyst |
| `POST` | `/users/{uid}/groups/{gid}` | Add user to group | Admin |
| `DELETE` | `/users/{uid}/groups/{gid}` | Remove user from group | Admin |

---

### Organizational Unit Endpoints

| Method | Endpoint | Description | Min Role |
|--------|----------|-------------|---------|
| `GET` | `/organizational-units` | List all OUs | Viewer |
| `POST` | `/organizational-units` | Create an OU | Admin |
| `PUT` | `/organizational-units/{id}` | Update an OU | Admin |
| `DELETE` | `/organizational-units/{id}` | Delete an OU (must have no computers) | Admin |

---

### Monitoring & Data Endpoints

| Method | Endpoint | Description | Min Role |
|--------|----------|-------------|---------|
| `GET` | `/audit?limit=100&username=&action=&from_date=&to_date=` | Query audit logs | Analyst |
| `GET` | `/network-traffic?limit=100&bot_id=&username=&from_date=&to_date=` | Query network traffic | Analyst |
| `GET` | `/forensics?limit=100` | List forensic snapshots | Analyst |
| `GET` | `/forensics/{id}/download` | Download a forensic snapshot JSON | Analyst |

---

## 📡 WebSocket Protocol

### Connection Endpoint

```
ws://<server-ip>:8000/ws
```

### Message Flow

All messages are JSON objects with a `type` field.

#### Bot → Server Messages

| Type | When Sent | Key Fields |
|------|-----------|------------|
| `register` | On connection | `bot_id`, `username` |
| `alert` | When threat detected | `threat_score`, `suspicious_processes`, `bot_id`, `username` |
| `enforcement` | When process killed | `bot_id`, `policy_id`, `policy_name`, `action`, `target` |
| `compliance_alert` | When required process missing | `bot_id`, `process`, `missing_duration` |
| `session_status` | Every 30 seconds | `bot_id`, `logged_in`, `session_user` |
| `network_traffic` | Every 30 seconds | `bot_id`, `connections[]` |
| `forensics` | On lockdown | `bot_id`, `data` (full snapshot) |
| `emergency_unlock` | On hotkey press | `bot_id`, `username` |
| `ping` | Every 60 seconds | (heartbeat) |

#### Server → Bot Messages

| Type | When Sent | Effect on Bot |
|------|-----------|--------------|
| `lockdown` | Manual or auto-trigger | Activates full lockdown sequence |
| `unlock` | Admin command | Deactivates lockdown, restores normal operation |
| `policy_update` | On connect or policy change | Bot updates its local policy cache |

---

## 🔐 Security

### Implemented Security Features

| Feature | Implementation |
|---------|---------------|
| 🔑 **Authentication** | JWT tokens with HS256 signing and configurable expiration |
| 🔒 **Password Storage** | bcrypt hashing with random salt |
| 📱 **Multi-Factor Auth** | TOTP (RFC 6238) with QR code provisioning |
| 👮 **Authorization** | Role-based access control (Admin > Analyst > Viewer) |
| 📋 **Audit Trail** | Every action logged with timestamp, user, and details |
| 🌐 **Network Isolation** | Windows Firewall rules isolate compromised endpoints |
| 💾 **State Persistence** | Lockdown persists across reboots |

### ⚠️ Production Hardening Checklist

Before deploying SentinelAI in a real environment, you **must** address these items:

| Priority | Item | How to Fix |
|----------|------|-----------|
| 🔴 **Critical** | Default JWT `SECRET_KEY` | Replace with: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| 🔴 **Critical** | Default admin password `admin123` | Change immediately after first login |
| 🔴 **Critical** | No TLS/HTTPS | Deploy behind Nginx/Caddy with SSL certificates. Use `wss://` for WebSocket |
| 🟡 **High** | SQLite database | Migrate to PostgreSQL for production scale and concurrent access |
| 🟡 **High** | `CORS allow_origins=["*"]` | Restrict to your dashboard's domain only |
| 🟡 **High** | Hardcoded `BACKDOOR_IP` | Remove or restrict to server IP only |
| 🟡 **High** | No rate limiting | Add rate limiting on `/login` to prevent brute force |
| 🟠 **Medium** | Shell command injection risk | Sanitize `icacls` and `netsh` command arguments |
| 🟠 **Medium** | No bot authentication | Add shared secrets or certificates for bot registration |
| 🟠 **Medium** | Plaintext WebSocket | Use WSS (WebSocket over TLS) |
| 🟢 **Low** | No code signing | Sign the bot agent binary to prevent tampering |
| 🟢 **Low** | No update mechanism | Add auto-update capability for bot agents |

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Bot Agent** | Python 3, asyncio | Async event loop for concurrent monitoring |
| | psutil | Cross-platform process and system monitoring |
| | websockets | Persistent WebSocket connection to server |
| | tkinter | Full-screen lockdown overlay UI |
| | ctypes (Win32) | `BlockInput()` API for input blocking |
| | subprocess + netsh | Windows Firewall rule management |
| | winreg | Windows Registry access (USB control, autorun reading) |
| | watchdog | File system event monitoring |
| | keyboard | Emergency unlock hotkey registration |
| **Server** | FastAPI | Modern async Python web framework |
| | uvicorn | ASGI server with WebSocket support |
| | SQLite | Embedded relational database |
| | python-jose | JWT token creation and validation |
| | bcrypt | Secure password hashing |
| | pyotp | TOTP multi-factor authentication |
| | pydantic | Data validation and serialization |
| **Dashboard** | HTML5/CSS3 | Responsive dark-themed UI |
| | Vanilla JavaScript | No framework dependencies, pure JS |
| | QRCode.js (CDN) | QR code generation for MFA setup |

---

## 🔧 Troubleshooting

### Common Issues

<details>
<summary><strong>Bot can't connect to server</strong></summary>

**Symptoms:** `Connection error: ... Reconnecting in 10 seconds...`

**Solutions:**
1. Verify `SERVER_URL` in `bot_end.py` matches your server's IP and port
2. Ensure the server is running (`python server.py`)
3. Check firewall rules — port 8000 must be open on the server
4. Test connectivity: `curl http://SERVER_IP:8000/docs`
5. If on different networks, ensure routing is configured
</details>

<details>
<summary><strong>Bot doesn't start / UAC prompt fails</strong></summary>

**Symptoms:** Script exits immediately or UAC dialog appears

**Solution:** The bot requires administrative privileges. Either:
- Right-click → "Run as administrator"
- Accept the UAC prompt when it appears
- Run from an elevated command prompt
</details>

<details>
<summary><strong>Dashboard shows "Login failed"</strong></summary>

**Solutions:**
1. Verify `API_BASE` in `dashboard.html` points to your server
2. Check if server is running and accessible
3. Try default credentials: `admin` / `admin123`
4. Check browser console for CORS errors
5. If CORS issues, ensure `allow_origins=["*"]` is set on the server
</details>

<details>
<summary><strong>Lockdown won't release / machine stuck</strong></summary>

**Emergency Solutions:**
1. Press `Ctrl+Alt+Shift+U` (emergency hotkey)
2. If hotkey doesn't work, force-reboot and delete `locked_state.json` from the bot directory before the bot starts
3. Boot into Safe Mode (bot won't auto-start)
</details>

<details>
<summary><strong>Policies not being enforced</strong></summary>

**Check:**
1. Is the policy `enabled`? Check in the dashboard
2. Does the policy target match the bot? (user, group, OU, machine)
3. Is the schedule active? (check day/time alignment)
4. Is the bot connected? Check the "Bots" tab
5. Check bot console output for "Received X policies"
</details>

<details>
<summary><strong>"keyboard" hotkey not working</strong></summary>

**Solution:** Install the keyboard library:
```bash
pip install keyboard
```
Note: The `keyboard` library requires root/admin privileges on most systems.
</details>

---

## 🗄️ Database Schema

The server uses SQLite with the following tables:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     users        │     │     groups       │     │   user_groups    │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)          │     │ id (PK)          │     │ user_id (FK)     │
│ username (UQ)    │     │ name (UQ)        │     │ group_id (FK)    │
│ email (UQ)       │     │ description      │     └─────────────────┘
│ hashed_password  │     │ created_at       │
│ full_name        │     └─────────────────┘
│ role             │
│ disabled         │     ┌─────────────────┐     ┌─────────────────┐
│ totp_secret      │     │    computers     │     │organizational_  │
│ totp_enabled     │     ├─────────────────┤     │    units         │
│ created_at       │     │ bot_id (PK)      │     ├─────────────────┤
└─────────────────┘     │ computer_name    │     │ id (PK)          │
                         │ display_name     │     │ name (UQ)        │
┌─────────────────┐     │ department       │     │ description      │
│    policies      │     │ ou_id (FK)       │     │ parent_id (FK)   │
├─────────────────┤     │ last_user        │     │ created_at       │
│ id (PK)          │     │ last_seen        │     └─────────────────┘
│ name             │     └─────────────────┘
│ description      │                              ┌─────────────────┐
│ target_type      │     ┌─────────────────┐     │  network_traffic │
│ target_value     │     │ policy_versions  │     ├─────────────────┤
│ rule (JSON)      │     ├─────────────────┤     │ id (PK)          │
│ enabled          │     │ id (PK)          │     │ timestamp        │
│ created_at       │     │ policy_id (FK)   │     │ bot_id           │
│ updated_at       │     │ name             │     │ username         │
└─────────────────┘     │ description      │     │ src_ip/port      │
                         │ target_type      │     │ dst_ip/port      │
┌─────────────────┐     │ target_value     │     │ protocol         │
│   audit_log      │     │ rule (JSON)      │     │ process          │
├─────────────────┤     │ enabled          │     │ pid              │
│ id (PK)          │     │ created_at       │     └─────────────────┘
│ timestamp        │     └─────────────────┘
│ user             │                              ┌─────────────────┐
│ action           │                              │    forensics     │
│ target_type      │                              ├─────────────────┤
│ target_id        │                              │ id (PK)          │
│ details          │                              │ bot_id           │
└─────────────────┘                              │ username         │
                                                  │ timestamp        │
                                                  │ file_path        │
                                                  └─────────────────┘
```

---

## 🤝 Contributing

Contributions are welcome! Here are some areas where help is needed:

- [ ] Linux bot agent support
- [ ] macOS bot agent support
- [ ] Real-time dashboard updates via WebSocket (not polling)
- [ ] Threat intelligence feed integration
- [ ] Email/SMS alerting
- [ ] Machine learning-based anomaly detection
- [ ] Docker deployment support
- [ ] Automated testing suite
- [ ] Plugin/extension system for custom rules

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">

### 🛡️ Built for Security. Designed for Control. Open for Everyone.

<br>

**SentinelAI** — Autonomous Endpoint Defence Platform

<br>

Made with ❤️ by [Karthik Varma](https://github.com/karthik-varma671)

<br>

⭐ **Star this repo if you find it useful!** ⭐

</div>
