from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse
from typing import Dict, Optional, List
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
import sqlite3
import json
import bcrypt
import pyotp
import os
import secrets
import time

# ==================== SECURITY CONSTANTS ====================
SECRET_KEY = "change-this-in-production-please-use-a-long-random-string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ==================== PASSWORD HASHING ====================
def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

# ==================== JWT ====================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ==================== DATABASE SETUP ====================
DB_FILE = "sentinelai.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'viewer',
        disabled BOOLEAN DEFAULT 0,
        totp_secret TEXT,
        totp_enabled BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS organizational_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        parent_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(parent_id) REFERENCES organizational_units(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS computers (
        bot_id TEXT PRIMARY KEY,
        computer_name TEXT,
        display_name TEXT,
        department TEXT,
        ou_id INTEGER,
        last_user TEXT,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ou_id) REFERENCES organizational_units(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        target_type TEXT NOT NULL,
        target_value TEXT NOT NULL,
        rule TEXT NOT NULL,
        enabled BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS policy_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        target_type TEXT NOT NULL,
        target_value TEXT NOT NULL,
        rule TEXT NOT NULL,
        enabled BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(policy_id) REFERENCES policies(id) ON DELETE CASCADE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_groups (
        user_id INTEGER,
        group_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
        PRIMARY KEY (user_id, group_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user TEXT,
        action TEXT,
        target_type TEXT,
        target_id INTEGER,
        details TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS network_traffic (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        bot_id TEXT,
        username TEXT,
        src_ip TEXT,
        src_port INTEGER,
        dst_ip TEXT,
        dst_port INTEGER,
        protocol INTEGER,
        process TEXT,
        pid INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS forensics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id TEXT NOT NULL,
        username TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_path TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

def ensure_admin_user():
    """Create default admin user if no users exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        hashed = get_password_hash("admin123")
        c.execute("INSERT INTO users (username, email, hashed_password, full_name, role) VALUES (?,?,?,?,?)",
                  ("admin", "admin@sentinelai.local", hashed, "Administrator", "admin"))
        conn.commit()
        print("✅ Created default admin user: admin / admin123")
    conn.close()

def ensure_default_ou():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM organizational_units WHERE name='Unassigned'")
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO organizational_units (name, description) VALUES (?,?)",
                  ("Unassigned", "Default OU for new computers"))
        conn.commit()
        ou_id = c.lastrowid
    else:
        ou_id = row[0]
    conn.close()
    return ou_id

def get_user(username: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, email, hashed_password, full_name, role, disabled, totp_secret, totp_enabled FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "hashed_password": row[3],
            "full_name": row[4],
            "role": row[5],
            "disabled": bool(row[6]),
            "totp_secret": row[7],
            "totp_enabled": bool(row[8])
        }
    return None

def get_user_id(username: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def log_audit(user: str, action: str, target_type: str, target_id: Optional[int], details: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO audit_log (user, action, target_type, target_id, details) VALUES (?,?,?,?,?)",
              (user, action, target_type, target_id, details))
    conn.commit()
    conn.close()

# ==================== PYDANTIC MODELS ====================
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class MFALogin(BaseModel):
    username: str
    password: str
    code: str

class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    target_type: str
    target_value: str
    rule: dict
    enabled: bool = True

class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_type: Optional[str] = None
    target_value: Optional[str] = None
    rule: Optional[dict] = None
    enabled: Optional[bool] = None

class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class OUCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    parent_id: Optional[int] = None

class OUUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None

# ==================== FASTAPI APP ====================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    if current_user["disabled"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# ==================== WEBSOCKET MANAGER ====================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.bot_locked: Dict[str, bool] = {}
        self.bot_user: Dict[str, str] = {}

    async def connect(self, bot_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[bot_id] = websocket
        self.bot_locked[bot_id] = False
        print(f"Bot {bot_id} connected")

    def disconnect(self, bot_id: str):
        self.active_connections.pop(bot_id, None)
        self.bot_locked.pop(bot_id, None)
        self.bot_user.pop(bot_id, None)
        print(f"Bot {bot_id} disconnected")

    async def send_command(self, bot_id: str, command: dict):
        if bot_id in self.active_connections:
            await self.active_connections[bot_id].send_json(command)
            print(f"Sent command to {bot_id}: {command}")
        else:
            print(f"Bot {bot_id} not connected")

    def get_policies_for_bot(self, bot_id: str, username: str):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        user_id = get_user_id(username)
        c.execute("SELECT ou_id FROM computers WHERE bot_id=?", (bot_id,))
        row = c.fetchone()
        ou_id = row[0] if row else None

        query = '''
            SELECT id, name, rule FROM policies WHERE enabled=1 AND (
                (target_type='all' AND target_value='*')
                OR (target_type='user' AND target_value=?)
                OR (target_type='machine' AND target_value=?)
                OR (target_type='group' AND target_value IN (
                    SELECT name FROM groups WHERE id IN (
                        SELECT group_id FROM user_groups WHERE user_id=?
                    )
                ))
        '''
        params = [username, bot_id]
        if user_id:
            params.append(user_id)
        if ou_id:
            query += ''' OR (target_type='ou' AND target_value IN (
                SELECT name FROM organizational_units WHERE id=?
            ))'''
            params.append(ou_id)
        query += ')'
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "rule": json.loads(r[2])} for r in rows]

    async def broadcast_policy_update(self):
        for bot_id, ws in self.active_connections.items():
            username = self.bot_user.get(bot_id, "unknown")
            policies = self.get_policies_for_bot(bot_id, username)
            try:
                await ws.send_json({"type": "policy_update", "policies": policies})
                print(f"Sent policy update to {bot_id} ({len(policies)} policies)")
            except:
                print(f"Failed to send policy update to {bot_id}")

manager = ConnectionManager()
AUTOLOCK_THRESHOLD = 0.6

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        msg = json.loads(data)
    except Exception:
        await websocket.close(code=1008, reason="Invalid JSON")
        return

    if msg.get("type") != "register":
        await websocket.close(code=1008, reason="First message must be registration")
        return

    bot_id = msg.get("bot_id")
    username = msg.get("username", "unknown")
    if not bot_id:
        await websocket.close(code=1008, reason="Missing bot_id")
        return

    manager.active_connections[bot_id] = websocket
    manager.bot_locked[bot_id] = False
    manager.bot_user[bot_id] = username
    print(f"Bot {bot_id} connected (user: {username})")

    default_ou_id = ensure_default_ou()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO computers (bot_id, computer_name, ou_id, last_user, last_seen) VALUES (?,?,?,?,CURRENT_TIMESTAMP)",
              (bot_id, bot_id, default_ou_id, username))
    conn.commit()
    conn.close()

    # Auto‑create user if not exists
    user = get_user(username)
    if not user:
        random_password = secrets.token_urlsafe(16)
        hashed = get_password_hash(random_password)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, email, hashed_password, full_name, role) VALUES (?,?,?,?,?)",
                  (username, f"{username}@terminaldefence.local", hashed, username, "viewer"))
        conn.commit()
        new_user_id = c.lastrowid
        conn.close()
        log_audit("SYSTEM", "CREATE", "user", new_user_id, f"Auto-created user for {username}")
        print(f"Auto-created user: {username}")

    policies = manager.get_policies_for_bot(bot_id, username)
    await manager.send_command(bot_id, {"type": "policy_update", "policies": policies})
    print(f"Sent {len(policies)} policies to {bot_id}")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "alert":
                threat = msg.get("threat_score", 0)
                procs = msg.get("suspicious_processes", [])
                print(f"🚨 ALERT from {bot_id}: threat_score={threat}, processes={procs}")
                if threat >= AUTOLOCK_THRESHOLD and not manager.bot_locked.get(bot_id, False):
                    print(f"🤖 AI DECISION: Lockdown {bot_id} (score={threat})")
                    await manager.send_command(bot_id, {"type": "lockdown"})
                    manager.bot_locked[bot_id] = True
            elif msg.get("type") == "enforcement":
                log_audit("SYSTEM", "ENFORCE", "process", None,
                          f"Bot {msg['bot_id']} terminated {msg['target']} due to policy '{msg['policy_name']}'")
            elif msg.get("type") == "compliance_alert":
                log_audit("SYSTEM", "COMPLIANCE", "process", None,
                          f"Bot {msg['bot_id']} missing required process: {msg['process']} (missing for {msg.get('missing_duration', '?')}s)")
            elif msg.get("type") == "ips_alert":
                log_audit("SYSTEM", "IPS", "ip", None,
                          f"Bot {msg['bot_id']} blocked connection to malicious IP {msg['ip']}")
                print(f"🚫 IPS blocked connection to {msg['ip']} on {msg['bot_id']}")
            elif msg.get("type") == "logon_event":
                event_id = msg.get("event_id")
                event_user = msg.get("event_user")
                source_ip = msg.get("source_ip", "")
                logon_type = msg.get("logon_type", "")
                details = f"EventID {event_id}: User '{event_user}' from IP {source_ip} (Logon Type {logon_type})"
                log_audit("SYSTEM", "LOGON_SUCCESS" if event_id == "4624" else "LOGON_FAILURE", "logon", None, details)
                print(f"🔐 Logon event from {msg['bot_id']}: {details}")
            elif msg.get("type") == "session_status":
                logged_in = msg.get("logged_in")
                session_user = msg.get("session_user")
                print(f"👤 Session status from {msg['bot_id']}: logged_in={logged_in}, user={session_user}")
            elif msg.get("type") == "file_event":
                log_audit("SYSTEM", f"FILE_{msg['action']}", "file", None,
                          f"Bot {msg['bot_id']}: {msg['action']} {msg['src']}" + (f" -> {msg['dest']}" if msg.get('dest') else ""))
                print(f"📄 File event from {msg['bot_id']}: {msg['action']} {msg['src']}")
            elif msg.get("type") == "network_traffic":
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                for conn_entry in msg.get("connections", []):
                    c.execute('''INSERT INTO network_traffic 
                                 (timestamp, bot_id, username, src_ip, src_port, dst_ip, dst_port, protocol, process, pid)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (msg.get("timestamp"), msg['bot_id'], msg['username'],
                               conn_entry.get("src_ip"), conn_entry.get("src_port"),
                               conn_entry.get("dst_ip"), conn_entry.get("dst_port"),
                               conn_entry.get("protocol"), conn_entry.get("process"), conn_entry.get("pid")))
                conn.commit()
                conn.close()
                print(f"🌐 Network traffic from {msg['bot_id']}: {len(msg.get('connections', []))} connections")
            elif msg.get("type") == "forensics":
                bot_id = msg.get("bot_id")
                username = msg.get("username")
                timestamp = msg.get("timestamp", time.time())
                forensic_data = msg.get("data", {})
                forensics_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forensics")
                os.makedirs(forensics_dir, exist_ok=True)
                filename = f"forensics_{bot_id}_{int(timestamp)}.json"
                filepath = os.path.join(forensics_dir, filename)
                with open(filepath, "w") as f:
                    json.dump(forensic_data, f, indent=2)
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO forensics (bot_id, username, timestamp, file_path) VALUES (?,?,?,?)",
                          (bot_id, username, datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"), filepath))
                conn.commit()
                conn.close()
                print(f"📁 Received forensics from {bot_id}")
            else:
                print(f"Unknown message type from {bot_id}: {msg.get('type')}")
    except WebSocketDisconnect:
        manager.disconnect(bot_id)

# ==================== AUTH ENDPOINTS ====================
@app.post("/register")
async def register(user: UserCreate):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? OR email=?", (user.username, user.email))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already registered")
    hashed = get_password_hash(user.password)
    c.execute("INSERT INTO users (username, email, hashed_password, full_name, role) VALUES (?,?,?,?,?)",
              (user.username, user.email, hashed, user.full_name, "viewer"))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    log_audit("system", "CREATE", "user", user_id, f"User '{user.username}' created")
    return {"message": "User created successfully"}

@app.post("/login")
async def login(user_data: UserLogin):
    user = get_user(user_data.username)
    if not user or not verify_password(user_data.password, user["hashed_password"]) or user["disabled"]:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if user["totp_enabled"]:
        temp_token = create_access_token(data={"sub": user["username"], "temp": True}, expires_delta=timedelta(minutes=5))
        return {"mfa_required": True, "temp_token": temp_token}
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    log_audit(user["username"], "LOGIN", "user", user["id"], "User logged in")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login-mfa")
async def login_mfa(mfa_data: MFALogin):
    user = get_user(mfa_data.username)
    if not user or not verify_password(mfa_data.password, user["hashed_password"]) or user["disabled"]:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user["totp_enabled"]:
        raise HTTPException(status_code=400, detail="MFA not enabled for this user")
    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(mfa_data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    log_audit(user["username"], "LOGIN", "user", user["id"], "User logged in with MFA")
    return {"access_token": access_token, "token_type": "bearer"}

# ==================== MFA MANAGEMENT ====================
@app.post("/mfa/enable")
async def enable_mfa(current_user = Depends(get_current_active_user)):
    secret = pyotp.random_base32()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET totp_secret=?, totp_enabled=1 WHERE id=?", (secret, current_user["id"]))
    conn.commit()
    conn.close()
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_user["username"], issuer_name="TerminalDefence")
    log_audit(current_user["username"], "MFA_ENABLE", "user", current_user["id"], "MFA enabled")
    return {"secret": secret, "uri": provisioning_uri}

@app.post("/mfa/disable")
async def disable_mfa(current_user = Depends(get_current_active_user)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET totp_enabled=0 WHERE id=?", (current_user["id"],))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "MFA_DISABLE", "user", current_user["id"], "MFA disabled")
    return {"message": "MFA disabled"}

@app.post("/mfa/verify")
async def verify_mfa(code: str, current_user = Depends(get_current_active_user)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT totp_secret FROM users WHERE id=?", (current_user["id"],))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="MFA not enabled")
    totp = pyotp.TOTP(row[0])
    if totp.verify(code, valid_window=1):
        return {"valid": True}
    else:
        raise HTTPException(status_code=400, detail="Invalid code")

# ==================== BOT CONTROL ENDPOINTS ====================
@app.post("/lockdown/{bot_id}")
async def lockdown_bot(bot_id: str, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    await manager.send_command(bot_id, {"type": "lockdown"})
    manager.bot_locked[bot_id] = True
    log_audit(current_user["username"], "LOCKDOWN", "bot", None, f"Manually locked down {bot_id}")
    return {"status": f"Lockdown command sent to {bot_id}"}

@app.post("/unlock/{bot_id}")
async def unlock_bot(bot_id: str, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    await manager.send_command(bot_id, {"type": "unlock"})
    manager.bot_locked[bot_id] = False
    log_audit(current_user["username"], "UNLOCK", "bot", None, f"Manually unlocked {bot_id}")
    return {"status": f"Unlock command sent to {bot_id}"}

@app.get("/computers")
async def get_computers(current_user = Depends(get_current_active_user)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT c.bot_id, c.computer_name, c.display_name, c.department, ou.name as ou_name, ou.id as ou_id, c.last_user, c.last_seen 
                 FROM computers c
                 LEFT JOIN organizational_units ou ON c.ou_id = ou.id
                 ORDER BY c.computer_name''')
    rows = c.fetchall()
    conn.close()
    computers = []
    for r in rows:
        bot_id = r[0]
        active = bot_id in manager.active_connections
        locked = manager.bot_locked.get(bot_id, False)
        computers.append({
            "bot_id": bot_id,
            "computer_name": r[1],
            "display_name": r[2],
            "department": r[3],
            "ou_name": r[4],
            "ou_id": r[5],
            "last_user": r[6],
            "last_seen": r[7],
            "active": active,
            "locked": locked
        })
    return {"computers": computers}

@app.get("/bots")
async def get_bots(current_user = Depends(get_current_active_user)):
    return {"bots": list(manager.active_connections.keys())}

@app.put("/computers/{bot_id}/ou")
async def set_computer_ou(bot_id: str, ou_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE computers SET ou_id=? WHERE bot_id=?", (ou_id, bot_id))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "UPDATE", "computer", None, f"Moved computer {bot_id} to OU {ou_id}")
    return {"message": "Computer OU updated"}

@app.put("/bots/{bot_id}/displayname")
async def set_bot_displayname(bot_id: str, display_name: str, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE computers SET display_name=? WHERE bot_id=?", (display_name, bot_id))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "UPDATE", "bot", None, f"Set display name for {bot_id} to '{display_name}'")
    return {"message": "Display name updated"}

@app.put("/bots/{bot_id}/department")
async def set_bot_department(bot_id: str, department: str, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE computers SET department=? WHERE bot_id=?", (department, bot_id))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "UPDATE", "bot", None, f"Set department for {bot_id} to '{department}'")
    return {"message": "Department updated"}

# ==================== ORGANIZATIONAL UNITS ====================
@app.get("/organizational-units")
async def get_ous(current_user = Depends(get_current_active_user)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, description, parent_id, created_at FROM organizational_units")
    rows = c.fetchall()
    conn.close()
    return {"ous": [{"id": r[0], "name": r[1], "description": r[2], "parent_id": r[3], "created_at": r[4]} for r in rows]}

@app.post("/organizational-units")
async def create_ou(ou: OUCreate, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO organizational_units (name, description, parent_id) VALUES (?,?,?)",
                  (ou.name, ou.description, ou.parent_id))
        conn.commit()
        ou_id = c.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="OU name already exists")
    conn.close()
    log_audit(current_user["username"], "CREATE", "ou", ou_id, f"Created OU '{ou.name}'")
    return {"message": "OU created", "id": ou_id}

@app.put("/organizational-units/{ou_id}")
async def update_ou(ou_id: int, ou: OUUpdate, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    fields = []
    values = []
    if ou.name is not None:
        fields.append("name=?")
        values.append(ou.name)
    if ou.description is not None:
        fields.append("description=?")
        values.append(ou.description)
    if ou.parent_id is not None:
        fields.append("parent_id=?")
        values.append(ou.parent_id)
    if not fields:
        conn.close()
        return {"message": "No changes"}
    query = f"UPDATE organizational_units SET {', '.join(fields)} WHERE id=?"
    values.append(ou_id)
    try:
        c.execute(query, values)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="OU name already exists")
    conn.close()
    log_audit(current_user["username"], "UPDATE", "ou", ou_id, f"Updated OU ID {ou_id}")
    return {"message": "OU updated"}

@app.delete("/organizational-units/{ou_id}")
async def delete_ou(ou_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM computers WHERE ou_id=?", (ou_id,))
    count = c.fetchone()[0]
    if count > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot delete OU with computers. Move them first.")
    c.execute("DELETE FROM organizational_units WHERE id=?", (ou_id,))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "DELETE", "ou", ou_id, f"Deleted OU ID {ou_id}")
    return {"message": "OU deleted"}

# ==================== USER MANAGEMENT ====================
@app.get("/users")
async def get_users(current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, email, full_name, role, disabled, created_at FROM users")
    rows = c.fetchall()
    conn.close()
    users = [{"id": r[0], "username": r[1], "email": r[2], "full_name": r[3], "role": r[4], "disabled": bool(r[5]), "created_at": r[6]} for r in rows]
    return {"users": users}

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "DELETE", "user", user_id, f"Deleted user ID {user_id}")
    return {"message": "User deleted"}

@app.put("/users/{user_id}/role")
async def update_user_role(user_id: int, role: str, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if role not in ["admin", "analyst", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "UPDATE", "user", user_id, f"Changed role to {role}")
    return {"message": "Role updated"}

@app.put("/users/{user_id}/disable")
async def disable_user(user_id: int, disabled: bool, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET disabled=? WHERE id=?", (1 if disabled else 0, user_id))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "UPDATE", "user", user_id, f"Set disabled={disabled}")
    return {"message": f"User {'disabled' if disabled else 'enabled'}"}

# ==================== GROUP MANAGEMENT ====================
@app.get("/groups")
async def get_groups(current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, description, created_at FROM groups ORDER BY name")
    rows = c.fetchall()
    conn.close()
    groups = [{"id": r[0], "name": r[1], "description": r[2], "created_at": r[3]} for r in rows]
    return {"groups": groups}

@app.post("/groups")
async def create_group(group: GroupCreate, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO groups (name, description) VALUES (?,?)", (group.name, group.description))
        conn.commit()
        group_id = c.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Group name already exists")
    conn.close()
    log_audit(current_user["username"], "CREATE", "group", group_id, f"Created group '{group.name}'")
    return {"message": "Group created", "id": group_id}

@app.put("/groups/{group_id}")
async def update_group(group_id: int, group: GroupUpdate, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    fields = []
    values = []
    if group.name is not None:
        fields.append("name=?")
        values.append(group.name)
    if group.description is not None:
        fields.append("description=?")
        values.append(group.description)
    if not fields:
        conn.close()
        return {"message": "No changes"}
    query = f"UPDATE groups SET {', '.join(fields)} WHERE id=?"
    values.append(group_id)
    try:
        c.execute(query, values)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Group name already exists")
    conn.close()
    log_audit(current_user["username"], "UPDATE", "group", group_id, f"Updated group")
    return {"message": "Group updated"}

@app.delete("/groups/{group_id}")
async def delete_group(group_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM groups WHERE id=?", (group_id,))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "DELETE", "group", group_id, f"Deleted group ID {group_id}")
    return {"message": "Group deleted"}

# ==================== USER-GROUP MEMBERSHIP ====================
@app.get("/users/{user_id}/groups")
async def get_user_groups(user_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT g.id, g.name FROM groups g
                 JOIN user_groups ug ON g.id = ug.group_id
                 WHERE ug.user_id = ?''', (user_id,))
    rows = c.fetchall()
    conn.close()
    return {"groups": [{"id": r[0], "name": r[1]} for r in rows]}

@app.post("/users/{user_id}/groups/{group_id}")
async def add_user_to_group(user_id: int, group_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO user_groups (user_id, group_id) VALUES (?,?)", (user_id, group_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="User already in group or invalid user/group")
    conn.close()
    log_audit(current_user["username"], "ADD", "user_group", None, f"Added user {user_id} to group {group_id}")
    await manager.broadcast_policy_update()
    return {"message": "User added to group"}

@app.delete("/users/{user_id}/groups/{group_id}")
async def remove_user_from_group(user_id: int, group_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM user_groups WHERE user_id=? AND group_id=?", (user_id, group_id))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "REMOVE", "user_group", None, f"Removed user {user_id} from group {group_id}")
    await manager.broadcast_policy_update()
    return {"message": "User removed from group"}

# ==================== POLICY MANAGEMENT ====================
@app.get("/policies")
async def get_policies(current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, description, target_type, target_value, rule, enabled, created_at, updated_at FROM policies ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    policies = []
    for r in rows:
        policies.append({
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "target_type": r[3],
            "target_value": r[4],
            "rule": json.loads(r[5]),
            "enabled": bool(r[6]),
            "created_at": r[7],
            "updated_at": r[8]
        })
    return {"policies": policies}

@app.post("/policies")
async def create_policy(policy: PolicyCreate, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    rule_json = json.dumps(policy.rule)
    c.execute('''INSERT INTO policies (name, description, target_type, target_value, rule, enabled)
                 VALUES (?,?,?,?,?,?)''',
              (policy.name, policy.description, policy.target_type, policy.target_value, rule_json, 1 if policy.enabled else 0))
    conn.commit()
    policy_id = c.lastrowid
    c.execute("INSERT INTO policy_versions (policy_id, name, description, target_type, target_value, rule, enabled) VALUES (?,?,?,?,?,?,?)",
              (policy_id, policy.name, policy.description, policy.target_type, policy.target_value, rule_json, 1 if policy.enabled else 0))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "CREATE", "policy", policy_id, f"Created policy '{policy.name}'")
    await manager.broadcast_policy_update()
    return {"message": "Policy created", "id": policy_id}

@app.put("/policies/{policy_id}")
async def update_policy(policy_id: int, policy: PolicyUpdate, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Save current version
    c.execute("SELECT name, description, target_type, target_value, rule, enabled FROM policies WHERE id=?", (policy_id,))
    row = c.fetchone()
    if row:
        c.execute("INSERT INTO policy_versions (policy_id, name, description, target_type, target_value, rule, enabled) VALUES (?,?,?,?,?,?,?)",
                  (policy_id, row[0], row[1], row[2], row[3], row[4], row[5]))
    fields = []
    values = []
    if policy.name is not None:
        fields.append("name=?")
        values.append(policy.name)
    if policy.description is not None:
        fields.append("description=?")
        values.append(policy.description)
    if policy.target_type is not None:
        fields.append("target_type=?")
        values.append(policy.target_type)
    if policy.target_value is not None:
        fields.append("target_value=?")
        values.append(policy.target_value)
    if policy.rule is not None:
        fields.append("rule=?")
        values.append(json.dumps(policy.rule))
    if policy.enabled is not None:
        fields.append("enabled=?")
        values.append(1 if policy.enabled else 0)
    fields.append("updated_at=CURRENT_TIMESTAMP")
    if not fields:
        conn.close()
        return {"message": "No changes"}
    query = f"UPDATE policies SET {', '.join(fields)} WHERE id=?"
    values.append(policy_id)
    c.execute(query, values)
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "UPDATE", "policy", policy_id, f"Updated policy '{policy.name or ''}'")
    await manager.broadcast_policy_update()
    return {"message": "Policy updated"}

@app.delete("/policies/{policy_id}")
async def delete_policy(policy_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM policies WHERE id=?", (policy_id,))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "DELETE", "policy", policy_id, f"Deleted policy ID {policy_id}")
    await manager.broadcast_policy_update()
    return {"message": "Policy deleted"}

@app.get("/policies/{policy_id}/versions")
async def get_policy_versions(policy_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, description, target_type, target_value, rule, enabled, created_at FROM policy_versions WHERE policy_id=? ORDER BY created_at DESC", (policy_id,))
    rows = c.fetchall()
    conn.close()
    versions = []
    for r in rows:
        versions.append({
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "target_type": r[3],
            "target_value": r[4],
            "rule": json.loads(r[5]),
            "enabled": bool(r[6]),
            "created_at": r[7]
        })
    return {"versions": versions}

@app.post("/policies/{policy_id}/rollback/{version_id}")
async def rollback_policy(policy_id: int, version_id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, description, target_type, target_value, rule, enabled FROM policy_versions WHERE id=? AND policy_id=?", (version_id, policy_id))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Version not found")
    # Save current policy as version (optional)
    c.execute("SELECT name, description, target_type, target_value, rule, enabled FROM policies WHERE id=?", (policy_id,))
    current = c.fetchone()
    if current:
        c.execute("INSERT INTO policy_versions (policy_id, name, description, target_type, target_value, rule, enabled) VALUES (?,?,?,?,?,?,?)",
                  (policy_id, current[0], current[1], current[2], current[3], current[4], current[5]))
    c.execute("UPDATE policies SET name=?, description=?, target_type=?, target_value=?, rule=?, enabled=? WHERE id=?",
              (row[0], row[1], row[2], row[3], row[4], 1 if row[5] else 0, policy_id))
    conn.commit()
    conn.close()
    log_audit(current_user["username"], "ROLLBACK", "policy", policy_id, f"Rolled back policy to version {version_id}")
    await manager.broadcast_policy_update()
    return {"message": "Policy rolled back"}

# ==================== AUDIT, NETWORK, FORENSICS ====================
@app.get("/audit")
async def get_audit_logs(limit: int = 100, username: Optional[str] = None, action: Optional[str] = None,
                         from_date: Optional[str] = None, to_date: Optional[str] = None,
                         current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = "SELECT timestamp, user, action, target_type, target_id, details FROM audit_log WHERE 1=1"
    params = []
    if username:
        query += " AND user LIKE ?"
        params.append(f"%{username}%")
    if action:
        query += " AND action LIKE ?"
        params.append(f"%{action}%")
    if from_date:
        query += " AND timestamp >= ?"
        params.append(from_date)
    if to_date:
        query += " AND timestamp <= ?"
        params.append(to_date)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return {"logs": [{"timestamp": r[0], "user": r[1], "action": r[2], "target_type": r[3], "target_id": r[4], "details": r[5]} for r in rows]}

@app.get("/network-traffic")
async def get_network_traffic(limit: int = 100, bot_id: Optional[str] = None, username: Optional[str] = None,
                              from_date: Optional[str] = None, to_date: Optional[str] = None,
                              current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = "SELECT timestamp, bot_id, username, src_ip, src_port, dst_ip, dst_port, protocol, process, pid FROM network_traffic WHERE 1=1"
    params = []
    if bot_id:
        query += " AND bot_id = ?"
        params.append(bot_id)
    if username:
        query += " AND username LIKE ?"
        params.append(f"%{username}%")
    if from_date:
        query += " AND timestamp >= ?"
        params.append(from_date)
    if to_date:
        query += " AND timestamp <= ?"
        params.append(to_date)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return {"traffic": [{"timestamp": r[0], "bot_id": r[1], "username": r[2], "src_ip": r[3], "src_port": r[4],
                        "dst_ip": r[5], "dst_port": r[6], "protocol": r[7], "process": r[8], "pid": r[9]} for r in rows]}

@app.get("/forensics")
async def get_forensics(limit: int = 100, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, bot_id, username, timestamp, file_path FROM forensics ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    forensics = []
    for r in rows:
        forensics.append({
            "id": r[0],
            "bot_id": r[1],
            "username": r[2],
            "timestamp": r[3],
            "file_path": r[4]
        })
    return {"forensics": forensics}

@app.get("/forensics/{id}/download")
async def download_forensics(id: int, current_user = Depends(get_current_active_user)):
    if current_user["role"] not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_path FROM forensics WHERE id=?", (id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    file_path = row[0]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=os.path.basename(file_path))

# ==================== RUN SERVER WITH INCREASED PING TIMEOUTS ====================
if __name__ == "__main__":
    import uvicorn
    init_db()
    ensure_admin_user()
    ensure_default_ou()
    # Increase WebSocket ping intervals to prevent timeouts
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ws_ping_interval=60,   # send ping every 60 seconds
        ws_ping_timeout=30     # wait 30 seconds for pong
    )