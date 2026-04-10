import asyncio
import websockets
import json
import sys
import subprocess
import psutil
import time
import os
import ctypes
import argparse
import winreg
import threading
import tkinter as tk
import uuid
from datetime import datetime, time as dtime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ==================== CONFIGURATION ====================
SERVER_URL = "ws://10.165.201.130:8000/ws"
ALERT_THRESHOLD = 0.5
SCAN_INTERVAL = 5
COMPLIANCE_GRACE_PERIOD = 30
BACKDOOR_IP = "10.165.201.130"
# =======================================================

# ==================== PERSISTENT ID & USER ====================
def get_bot_id():
    id_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_id.txt")
    if os.path.exists(id_file):
        with open(id_file, "r") as f:
            return f.read().strip()
    else:
        new_id = str(uuid.uuid4())
        with open(id_file, "w") as f:
            f.write(new_id)
        return new_id

def get_bot_username():
    user_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_user.txt")
    if os.path.exists(user_file):
        with open(user_file, "r") as f:
            return f.read().strip()
    else:
        print("First run configuration:")
        username = input("Username: ").strip()
        if not username:
            username = "unknown"
        with open(user_file, "w") as f:
            f.write(username)
        return username

BOT_ID = get_bot_id()
BOT_USERNAME = get_bot_username()

SUSPICIOUS_NAMES = [
    "ransomware", "encrypt", "decrypt", "locky", "wannacry",
    "cerber", "cryptolocker", "badrabbit", "notpetya", "gandcrab",
    "teslacrypt", "torrent", "miner", "coin", "xmrig"
]

CRITICAL_PROCESSES = [
    "System", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "svchost.exe", "winlogon.exe", "explorer.exe", "dwm.exe",
    "taskhostw.exe", "fontdrvhost.exe", "spoolsv.exe", "MsMpEng.exe",
    "NisSrv.exe", "SecurityHealthService.exe", "ctfmon.exe"
]

locked = False
websocket_connection = None
current_policies = []
missing_processes = {}
overlay_root = None
input_blocked = False
state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locked_state.json")

# ==================== STATE PERSISTENCE ====================
def save_locked_state():
    with open(state_file, "w") as f:
        json.dump({"locked": locked}, f)

def load_locked_state():
    global locked
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                data = json.load(f)
                locked = data.get("locked", False)
                print(f"Loaded locked state: {locked}")
        except:
            pass

# ==================== WINDOWS API ====================
user32 = ctypes.WinDLL('user32', use_last_error=True)
def block_input(block: bool):
    global input_blocked
    try:
        user32.BlockInput(block)
        input_blocked = block
        print(f"Input {'blocked' if block else 'unblocked'}.")
    except Exception as e:
        print(f"Failed to block input: {e}")

# ==================== OVERLAY ====================
def show_overlay():
    global overlay_root
    if overlay_root is not None:
        return
    def overlay_thread():
        global overlay_root
        overlay_root = tk.Tk()
        overlay_root.attributes('-fullscreen', True)
        overlay_root.attributes('-topmost', True)
        overlay_root.overrideredirect(True)
        overlay_root.configure(bg='black')
        overlay_root.protocol("WM_DELETE_WINDOW", lambda: None)
        label = tk.Label(overlay_root, text="🔒 SYSTEM LOCKDOWN\n\nContact IT immediately.\n\nThis system is locked by SentinelAI.",
                         fg='red', bg='black', font=('Arial', 48, 'bold'))
        label.pack(expand=True)
        def ignore(event):
            return "break"
        overlay_root.bind_all('<Key>', ignore)
        overlay_root.bind_all('<Button>', ignore)
        overlay_root.mainloop()
        overlay_root = None
    threading.Thread(target=overlay_thread, daemon=True).start()

def close_overlay():
    global overlay_root
    if overlay_root:
        overlay_root.quit()
        overlay_root = None

# ==================== EMERGENCY UNLOCK HOTKEY ====================
try:
    import keyboard
    HOTKEY = "ctrl+alt+shift+u"
    async def async_emergency_unlock_notify():
        if websocket_connection:
            try:
                await websocket_connection.send(json.dumps({
                    "type": "emergency_unlock",
                    "bot_id": BOT_ID,
                    "username": BOT_USERNAME,
                    "timestamp": time.time()
                }))
            except:
                pass
    def emergency_unlock():
        global locked
        if locked:
            print("⚠️ Emergency unlock triggered by hotkey!")
            close_overlay()
            block_input(False)
            restore_firewall()
            locked = False
            save_locked_state()
            asyncio.run_coroutine_threadsafe(async_emergency_unlock_notify(), asyncio.get_event_loop())
    keyboard.add_hotkey(HOTKEY, emergency_unlock)
    print(f"Emergency unlock hotkey registered: {HOTKEY}")
except ImportError:
    print("⚠️ keyboard library not installed. Emergency hotkey disabled. Install with: pip install keyboard")
except Exception as e:
    print(f"Failed to register hotkey: {e}")

# ==================== FIREWALL MANAGEMENT ====================
FIREWALL_RULE_PREFIX = "SentinelAI_"
IPS_RULE_PREFIX = "SentinelAI_IPS_"

def add_firewall_rule(name, action, direction, remote_ip, protocol="any", local_port="any"):
    cmd = f'netsh advfirewall firewall add rule name="{name}" dir={direction} action={action}'
    if remote_ip != "any":
        cmd += f' remoteip={remote_ip}'
    if protocol != "any":
        cmd += f' protocol={protocol}'
    if local_port != "any":
        cmd += f' localport={local_port}'
    subprocess.run(cmd, shell=True, capture_output=True)

def delete_firewall_rule(name):
    subprocess.run(f'netsh advfirewall firewall delete rule name="{name}"', shell=True, capture_output=True)

def isolate_with_firewall():
    subprocess.run('netsh advfirewall firewall delete rule name="SentinelAI_Isolation_*"', shell=True)
    subprocess.run('netsh advfirewall set allprofiles firewallpolicy blockinbound,blockoutbound', shell=True)
    subprocess.run('netsh advfirewall firewall add rule name="SentinelAI_Isolation_DNS" dir=out action=allow protocol=udp remoteport=53', shell=True)
    subprocess.run('netsh advfirewall firewall add rule name="SentinelAI_Isolation_DHCP" dir=out action=allow protocol=udp remoteport=67', shell=True)
    server_ip = SERVER_URL.split('/')[2].split(':')[0]
    if server_ip != "localhost" and not server_ip.startswith("127."):
        subprocess.run(f'netsh advfirewall firewall add rule name="SentinelAI_Isolation_Server" dir=out action=allow remoteip={server_ip}', shell=True)
    subprocess.run('netsh advfirewall firewall add rule name="SentinelAI_Isolation_Loopback" dir=out action=allow remoteip=127.0.0.1', shell=True)
    if BACKDOOR_IP:
        subprocess.run(f'netsh advfirewall firewall add rule name="SentinelAI_Isolation_Backdoor" dir=out action=allow remoteip={BACKDOOR_IP}', shell=True)
    print("🔒 Isolation firewall rules applied.")

def restore_firewall():
    subprocess.run('netsh advfirewall firewall delete rule name="SentinelAI_Isolation_*"', shell=True)
    subprocess.run('netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound', shell=True)
    print("🔓 Firewall restored.")

# ==================== FORENSICS (Background) ====================
async def capture_forensics():
    await asyncio.to_thread(_sync_forensics)

def _sync_forensics():
    timestamp = int(time.time())
    forensic_data = {
        "bot_id": BOT_ID,
        "username": BOT_USERNAME,
        "timestamp": timestamp,
        "processes": [],
        "network_connections": [],
        "services": [],
        "scheduled_tasks": [],
        "installed_software": [],
        "autoruns": [],
        "event_log_errors": []
    }
    # Processes
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'exe']):
        try:
            info = proc.info
            info['cmdline'] = proc.cmdline()
            forensic_data["processes"].append(info)
        except:
            pass
    # Network connections
    for conn in psutil.net_connections(kind='inet'):
        if conn.raddr:
            forensic_data["network_connections"].append({
                "laddr": (conn.laddr.ip, conn.laddr.port) if conn.laddr else None,
                "raddr": (conn.raddr.ip, conn.raddr.port) if conn.raddr else None,
                "status": conn.status,
                "pid": conn.pid
            })
    # Services
    try:
        result = subprocess.run('sc query state= all', shell=True, capture_output=True, text=True)
        service_names = []
        for line in result.stdout.splitlines():
            if line.strip().startswith("SERVICE_NAME:"):
                name = line.split(":",1)[1].strip()
                service_names.append(name)
        forensic_data["services"] = service_names[:100]
    except:
        pass
    # Scheduled tasks
    try:
        result = subprocess.run('schtasks /query /fo csv /v', shell=True, capture_output=True, text=True)
        tasks = []
        for line in result.stdout.splitlines()[1:]:
            parts = line.split('","')
            if len(parts) >= 2:
                tasks.append(parts[0].strip('"'))
        forensic_data["scheduled_tasks"] = tasks[:50]
    except:
        pass
    # Installed software (registry)
    software = []
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    for root in reg_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        if display_name:
                            software.append(display_name)
                    except:
                        pass
                    winreg.CloseKey(subkey)
                    i += 1
                except WindowsError:
                    break
            winreg.CloseKey(key)
        except:
            pass
    forensic_data["installed_software"] = list(set(software))[:100]
    # Autoruns
    autoruns = []
    run_keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce"
    ]
    for key_path in run_keys:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    autoruns.append(f"{name}: {value}")
                    i += 1
                except WindowsError:
                    break
            winreg.CloseKey(key)
        except:
            pass
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                autoruns.append(f"{name}: {value}")
                i += 1
            except WindowsError:
                break
        winreg.CloseKey(key)
    except:
        pass
    forensic_data["autoruns"] = autoruns[:50]
    # Event log errors
    try:
        result = subprocess.run('wevtutil qe System /rd:true /c:10 /f:text /e:events /q:"*[System[Level=2]]"', shell=True, capture_output=True, text=True)
        errors = []
        current_event = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Event["):
                if current_event:
                    errors.append(current_event)
                current_event = {}
            elif "EventID:" in line:
                current_event["id"] = line.split(":",1)[1].strip()
            elif "TimeCreated:" in line:
                current_event["time"] = line.split(":",1)[1].strip()
            elif "Provider Name:" in line:
                current_event["source"] = line.split(":",1)[1].strip()
            elif "Message:" in line:
                current_event["message"] = line.split(":",1)[1].strip()
        if current_event:
            errors.append(current_event)
        forensic_data["event_log_errors"] = errors[:10]
    except:
        pass
    # Save file
    local_filename = f"forensics_{BOT_ID}_{timestamp}.json"
    with open(local_filename, "w") as f:
        json.dump(forensic_data, f, indent=2)
    print(f"📁 Forensic snapshot saved locally to {local_filename}")
    global pending_forensic
    pending_forensic = forensic_data

pending_forensic = None

async def send_pending_forensic():
    global pending_forensic
    if pending_forensic and websocket_connection:
        try:
            await websocket_connection.send(json.dumps({
                "type": "forensics",
                "bot_id": BOT_ID,
                "username": BOT_USERNAME,
                "timestamp": pending_forensic["timestamp"],
                "data": pending_forensic
            }))
            print("📤 Forensic snapshot sent to server")
            pending_forensic = None
        except Exception as e:
            print(f"Failed to send forensics: {e}")

# ==================== LOCKDOWN (FAST) ====================
async def execute_lockdown():
    global locked
    if locked:
        print("Already locked down, ignoring command")
        return
    print("🔒 LOCKDOWN – Executing enhanced lockdown...")
    show_overlay()
    block_input(True)
    isolate_with_firewall()
    locked = True
    save_locked_state()
    print("🔒 Immediate lockdown applied.")
    asyncio.create_task(capture_forensics())
    asyncio.create_task(send_pending_forensic())

async def execute_unlock():
    global locked
    if not locked:
        print("Not locked, ignoring unlock")
        return
    print("🔓 UNLOCK – Restoring...")
    close_overlay()
    block_input(False)
    restore_firewall()
    locked = False
    save_locked_state()
    print("🔓 Unlock complete")

# ==================== POLICY ENFORCEMENT HELPERS ====================
def is_time_in_schedule(schedule):
    if not schedule:
        return True
    # Always return True for demonstration (ignore schedule)
    return True

def set_usb_storage(disable: bool):
    try:
        key_path = r"SYSTEM\CurrentControlSet\Services\USBSTOR"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
        new_value = 4 if disable else 3
        winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, new_value)
        winreg.CloseKey(key)
        print(f"USB storage {'disabled' if disable else 'enabled'} via registry.")
    except Exception as e:
        print(f"Failed to set USB storage: {e}")

def apply_folder_rules(policy):
    rules = policy.get("rule", {}).get("folder_rules", [])
    for rule in rules:
        path = rule.get("path")
        target = rule.get("target")
        target_value = rule.get("target_value")
        permission = rule.get("permission")
        if not path or not os.path.exists(path):
            continue
        if target == "user":
            if permission == "D":
                cmd = f'icacls "{path}" /deny {target_value}:F'
            else:
                perm_map = {"R":"R", "W":"W", "X":"X", "F":"F"}
                perm = perm_map.get(permission, "F")
                cmd = f'icacls "{path}" /grant {target_value}:{perm}'
        elif target == "group":
            if permission == "D":
                cmd = f'icacls "{path}" /deny {target_value}:F'
            else:
                perm_map = {"R":"R", "W":"W", "X":"X", "F":"F"}
                perm = perm_map.get(permission, "F")
                cmd = f'icacls "{path}" /grant {target_value}:{perm}'
        elif target == "machine":
            current_user = BOT_USERNAME
            if permission == "D":
                cmd = f'icacls "{path}" /deny {current_user}:F'
            else:
                perm_map = {"R":"R", "W":"W", "X":"X", "F":"F"}
                perm = perm_map.get(permission, "F")
                cmd = f'icacls "{path}" /grant {current_user}:{perm}'
        else:
            continue
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            print(f"📁 Applied folder rule: {cmd}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to apply folder rule {cmd}: {e.stderr.decode()}")

async def send_compliance_alert(process_name, missing_duration):
    global websocket_connection
    if websocket_connection:
        try:
            await websocket_connection.send(json.dumps({
                "type": "compliance_alert",
                "bot_id": BOT_ID,
                "username": BOT_USERNAME,
                "process": process_name,
                "missing_duration": missing_duration,
                "timestamp": time.time()
            }))
        except:
            pass

# ==================== MONITORING (WITH SIMPLE NOTEPAD KILL) ====================
async def monitor_processes():
    global websocket_connection, missing_processes
    if not hasattr(monitor_processes, "usb_blocked_state"):
        monitor_processes.usb_blocked_state = None

    while True:
        try:
            # 1. Threat score calculation (for alerts and auto-lockdown)
            threat_score, suspicious_found = await asyncio.to_thread(_compute_threat_score)
            print(f"Debug: threat score = {threat_score:.2f}")
            if threat_score >= ALERT_THRESHOLD and websocket_connection:
                alert_msg = {
                    "type": "alert",
                    "threat_score": threat_score,
                    "suspicious_processes": suspicious_found[:5],
                    "bot_id": BOT_ID,
                    "username": BOT_USERNAME,
                    "timestamp": time.time()
                }
                await websocket_connection.send(json.dumps(alert_msg))
                print(f"🚨 Alert sent: threat score {threat_score:.2f}")

            # 2. Policy enforcement (simplified: always enforce block_processes)
            for policy in current_policies:
                rule = policy.get("rule", {})
                # Ignore schedule – we always enforce
                blocked = rule.get("block_processes", [])
                if blocked:
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            if proc.info['name'].lower() in [b.lower() for b in blocked]:
                                proc.kill()
                                print(f"🛑 Policy '{policy['name']}' terminated {proc.info['name']}")
                                if websocket_connection:
                                    await websocket_connection.send(json.dumps({
                                        "type": "enforcement",
                                        "bot_id": BOT_ID,
                                        "username": BOT_USERNAME,
                                        "policy_id": policy["id"],
                                        "policy_name": policy["name"],
                                        "action": "terminate_process",
                                        "target": proc.info['name'],
                                        "timestamp": time.time()
                                    }))
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                # Folder RBAC
                folder_rules = rule.get("folder_rules", [])
                if folder_rules:
                    apply_folder_rules(policy)

            # USB blocking (global across policies)
            usb_blocked = any(p.get("rule", {}).get("block_usb", False) for p in current_policies)
            if usb_blocked != monitor_processes.usb_blocked_state:
                set_usb_storage(usb_blocked)
                monitor_processes.usb_blocked_state = usb_blocked
                if websocket_connection:
                    await websocket_connection.send(json.dumps({
                        "type": "enforcement",
                        "bot_id": BOT_ID,
                        "username": BOT_USERNAME,
                        "policy_id": None,
                        "policy_name": "USB Policy",
                        "action": "usb_block" if usb_blocked else "usb_unblock",
                        "target": "USB storage",
                        "timestamp": time.time()
                    }))

            # Required processes compliance
            required = set()
            for policy in current_policies:
                for req in policy.get("rule", {}).get("required_processes", []):
                    required.add(req.lower())

            running = set()
            for proc in psutil.process_iter(['name']):
                try:
                    running.add(proc.info['name'].lower())
                except:
                    pass

            now = time.time()
            for req in required:
                if req in running:
                    if req in missing_processes:
                        print(f"✅ Required process {req} is now running, cleared alert.")
                        del missing_processes[req]
                else:
                    if req not in missing_processes:
                        missing_processes[req] = now
                        print(f"⚠️ Required process {req} missing, tracking...")
                    else:
                        missing_since = missing_processes[req]
                        if now - missing_since >= COMPLIANCE_GRACE_PERIOD:
                            if f"{req}_alert_sent" not in missing_processes:
                                print(f"🚨 Compliance alert: Required process {req} missing for {now - missing_since:.0f}s")
                                await send_compliance_alert(req, int(now - missing_since))
                                missing_processes[f"{req}_alert_sent"] = True
            # Clean up
            to_remove = [p for p in missing_processes if p not in required and not p.endswith("_alert_sent")]
            for p in to_remove:
                del missing_processes[p]

        except Exception as e:
            print(f"Monitoring error: {e}")

        await asyncio.sleep(SCAN_INTERVAL)

def _compute_threat_score():
    score = 0.0
    suspicious = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            cmdline = ' '.join(proc.cmdline()).lower()
            proc_name = proc.info['name'].lower()
            combined = proc_name + ' ' + cmdline
            for suspicious_name in SUSPICIOUS_NAMES:
                if suspicious_name in combined:
                    score += 0.3
                    suspicious.append(proc_name)
                    break
            if proc.info['cpu_percent'] > 50:
                score += 0.3
        except:
            pass
    return min(score, 1.0), suspicious

# ==================== SESSION STATUS & NETWORK TRAFFIC ====================
async def report_session_status():
    while True:
        try:
            logged_in, session_user = get_session_status()
            if websocket_connection:
                await websocket_connection.send(json.dumps({
                    "type": "session_status",
                    "bot_id": BOT_ID,
                    "username": BOT_USERNAME,
                    "logged_in": logged_in,
                    "session_user": session_user,
                    "timestamp": time.time()
                }))
                print(f"👤 Session status: logged_in={logged_in}, user={session_user}")
        except:
            pass
        await asyncio.sleep(30)

def get_session_status():
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        try:
            if proc.info['name'].lower() == 'explorer.exe':
                user = proc.info['username']
                return True, user if user else "unknown"
        except:
            pass
    return False, None

async def report_network_traffic():
    while True:
        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    proc_name = ""
                    try:
                        proc = psutil.Process(conn.pid)
                        proc_name = proc.name()
                    except:
                        pass
                    connections.append({
                        "src_ip": conn.laddr.ip if conn.laddr else "",
                        "src_port": conn.laddr.port if conn.laddr else 0,
                        "dst_ip": conn.raddr.ip,
                        "dst_port": conn.raddr.port,
                        "protocol": conn.type,
                        "process": proc_name,
                        "pid": conn.pid
                    })
            if websocket_connection:
                await websocket_connection.send(json.dumps({
                    "type": "network_traffic",
                    "bot_id": BOT_ID,
                    "username": BOT_USERNAME,
                    "connections": connections,
                    "timestamp": time.time()
                }))
                print(f"🌐 Sent {len(connections)} network connections")
        except:
            pass
        await asyncio.sleep(30)

# ==================== MAIN LOOP (VERY LONG TIMEOUTS) ====================
async def main():
    global websocket_connection, locked
    load_locked_state()
    while True:
        try:
            # Use extremely long ping intervals to prevent disconnections
            async with websockets.connect(
                SERVER_URL,
                ping_interval=300,      # 5 minutes
                ping_timeout=120,       # 2 minutes
                close_timeout=30
            ) as websocket:
                websocket_connection = websocket
                print(f"Connected to server. Registering as {BOT_ID}...")
                await websocket.send(json.dumps({
                    "type": "register",
                    "bot_id": BOT_ID,
                    "username": BOT_USERNAME
                }))
                if locked:
                    print("Re-applying lockdown after reconnect...")
                    isolate_with_firewall()
                    show_overlay()
                    block_input(True)

                # Simple heartbeat (optional)
                async def heartbeat():
                    while True:
                        await asyncio.sleep(60)  # every minute
                        if websocket_connection and websocket_connection.state == websockets.protocol.State.OPEN:
                            try:
                                await websocket_connection.send(json.dumps({"type": "ping"}))
                            except:
                                pass
                asyncio.create_task(heartbeat())

                # Start monitoring tasks
                asyncio.create_task(monitor_processes())
                asyncio.create_task(report_session_status())
                asyncio.create_task(report_network_traffic())

                # Command loop
                async for message in websocket:
                    data = json.loads(message)
                    print(f"Received command: {data}")
                    cmd = data.get("type")
                    if cmd == "lockdown":
                        await execute_lockdown()
                    elif cmd == "unlock":
                        await execute_unlock()
                    elif cmd == "policy_update":
                        current_policies = data.get("policies", [])
                        print(f"📋 Received {len(current_policies)} policies")
                    else:
                        print(f"Unknown command: {cmd}")
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"Connection error: {e}. Reconnecting in 10 seconds...")
            await asyncio.sleep(10)
            continue
        except KeyboardInterrupt:
            print("\nBot stopped by user")
            break

if __name__ == "__main__":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    else:
        print("Running with administrator privileges.")
        print(f"Reported username: {BOT_USERNAME}")
        print(f"Unique bot ID: {BOT_ID}")
        print("Waiting 10 seconds for network to initialize...")
        time.sleep(10)
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            pass