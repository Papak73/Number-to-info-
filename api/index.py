from http.server import BaseHTTPRequestHandler
import json
import base64
import urllib.parse
import requests
import random
import string
import time

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8844062890:AAEfR60g5ryBG_8EntBP1pDtLhoomJIB5uU"
ADMIN_ID = 5868498550
VERCEL_DOMAIN = "https://alok-developer.vercel.app"

REDIS_URL = "https://golden-koi-284683.upstash.io"
REDIS_TOKEN = "gQAAAAAABFgLAAIgcDI4ODA3MTQyNTYwYWM0NWFlYTUyNDlkN2RiNWFlOTNkYw"

_CONFIG_STREAM = b"aHR0cHM6Ly9hdmktYmFidS52ZXJjZWwuYXBwL2FwaT9rZXk9YXZpcmFqJmFjdGlvbj1OdW0="

session = requests.Session()

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_endpoint() -> str:
    return base64.b64decode(_CONFIG_STREAM).decode("utf-8")

def redis_cmd(command, *args):
    """Upstash Redis helper"""
    url = f"{REDIS_URL}/"
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    payload = [command] + list(args)
    try:
        res = session.post(url, headers=headers, json=payload, timeout=5)
        return res.json().get("result")
    except Exception:
        return None

def send_tg_msg(chat_id, text):
    """Telegram message sender"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        session.post(url, json=payload, timeout=5)
    except Exception:
        pass

def generate_key():
    chars = string.ascii_uppercase + string.digits
    return "Alok-" + "".join(random.choices(chars, k=10))

def clean_address(raw_address: str) -> str:
    if not raw_address or raw_address.strip() == "N/A": return "N/A"
    tokens = raw_address.replace("!!", "").split("!")
    cleaned = []
    for t in tokens:
        t = t.strip()
        if t and t.upper() != "NA" and t != "0" and t not in cleaned:
            cleaned.append(t)
    return ", ".join(cleaned) if cleaned else "N/A"

def format_ttl(seconds):
    """Seconds ko readable time format mein badle"""
    if not seconds or seconds < 0:
        return "Expired"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0: parts.append(f"{days} Days")
    if hours > 0: parts.append(f"{hours} Hours")
    if minutes > 0 or not parts: parts.append(f"{minutes} Mins")
    return ", ".join(parts)

# ==========================================
# MAIN VERCEL HANDLER
# ==========================================
class handler(BaseHTTPRequestHandler):
    
    def do_POST(self):
        """Handles Telegram Bot Webhook updates"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
        
        try:
            update = json.loads(post_data.decode('utf-8'))
        except Exception:
            return

        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id or not text or chat_id != ADMIN_ID:
            return # Ignore non-admin messages

        # Bot Commands Logic
        if text.startswith("/start"):
            msg = (
                "⚡ *PRO API MANAGER (SECURE)* ⚡\n\n"
                "🛠️ *Commands:*\n"
                "`/gen <days> <limit>` - Auto-generate key\n"
                "`/custom <name> <days> <limit>` - Create custom key\n"
                "`/list` - Monitor active keys & stats\n"
                "`/logs <key>` - Check usage history of a key\n"
                "`/broadcast <msg>` - Send announcement to all\n"
                "`/del <key>` - Delete specific key"
            )
            send_tg_msg(chat_id, msg)

        elif text.startswith("/gen "):
            parts = text.split()
            if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                days = int(parts[1])
                limit = int(parts[2])
                new_key = generate_key()
                seconds = days * 24 * 3600
                
                redis_cmd("SETEX", f"api:{new_key}", seconds, "active")
                redis_cmd("SETEX", f"limit:{new_key}", seconds, str(limit))
                redis_cmd("SADD", "all_keys", new_key)
                
                ready_url = f"{VERCEL_DOMAIN}/?key={new_key}&num=9608978318"
                msg = (
                    "✅ *AUTO KEY GENERATED*\n"
                    f"🔑 Key: `{new_key}`\n"
                    f"⏳ Validity: {days} Days\n"
                    f"📊 Limit: {limit} Queries\n\n"
                    f"🔗 *URL:* `{ready_url}`"
                )
                send_tg_msg(chat_id, msg)
            else:
                send_tg_msg(chat_id, "❌ Error. Use format: `/gen 1 100`")

        elif text.startswith("/custom "):
            parts = text.split()
            if len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit():
                custom_name = parts[1].strip()
                days = int(parts[2])
                limit = int(parts[3])
                seconds = days * 24 * 3600
                
                existing = redis_cmd("GET", f"api:{custom_name}")
                if existing:
                    send_tg_msg(chat_id, f"⚠️ Key `{custom_name}` already exists!")
                    return

                redis_cmd("SETEX", f"api:{custom_name}", seconds, "active")
                redis_cmd("SETEX", f"limit:{custom_name}", seconds, str(limit))
                redis_cmd("SADD", "all_keys", custom_name)
                
                ready_url = f"{VERCEL_DOMAIN}/?key={custom_name}&num=9608978318"
                msg = (
                    "✨ *CUSTOM KEY CREATED*\n"
                    f"🔑 Key: `{custom_name}`\n"
                    f"⏳ Validity: {days} Days\n"
                    f"📊 Limit: {limit} Queries\n\n"
                    f"🔗 *URL:* `{ready_url}`"
                )
                send_tg_msg(chat_id, msg)
            else:
                send_tg_msg(chat_id, "❌ Error. Use format: `/custom alfa 30 500`")

        elif text == "/list":
            keys = redis_cmd("SMEMBERS", "all_keys")
            if not keys:
                send_tg_msg(chat_id, "⚠️ No active keys found.")
                return
            
            msg = "📊 *API MONITORING DASHBOARD*\n\n"
            active_count = 0
            
            for k in keys:
                status = redis_cmd("GET", f"api:{k}")
                if status:
                    limit = redis_cmd("GET", f"limit:{k}") or "0"
                    ttl_sec = redis_cmd("TTL", f"api:{k}")
                    time_left = format_ttl(ttl_sec)
                    msg += f"🔑 `{k}`\n📉 Left: *{limit}* | ⏳ Time: *{time_left}*\n──────────────\n"
                    active_count += 1
                else:
                    redis_cmd("SREM", "all_keys", k)
                    redis_cmd("DEL", f"limit:{k}")
            
            summary = f"🟢 *Total Active Keys:* {active_count}\n\n"
            send_tg_msg(chat_id, summary + msg if active_count > 0 else "⚠️ No active keys found.")

        elif text.startswith("/logs "):
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                target_key = parts[1].strip()
                logs = redis_cmd("LRANGE", f"logs:{target_key}", 0, 9)
                if not logs:
                    send_tg_msg(chat_id, f"📂 No history found for key: `{target_key}`")
                    return
                
                log_msg = f"📜 *LOGS FOR KEY:* `{target_key}`\n\n"
                for entry in logs:
                    log_msg += f"• `{entry}`\n"
                send_tg_msg(chat_id, log_msg)
            else:
                send_tg_msg(chat_id, "❌ Use format: `/logs <key>`")

        elif text.startswith("/broadcast "):
            announcement = text[len("/broadcast "):].strip()
            if not announcement:
                send_tg_msg(chat_id, "❌ Please provide a message to broadcast.")
                return
            
            keys = redis_cmd("SMEMBERS", "all_keys") or []
            send_tg_msg(chat_id, f"✅ Broadcast triggered successfully for {len(keys)} active tracking slots.")

        elif text.startswith("/del "):
            parts = text.split()
            if len(parts) == 2:
                target = parts[1].strip()
                redis_cmd("DEL", f"api:{target}")
                redis_cmd("DEL", f"limit:{target}")
                redis_cmd("DEL", f"logs:{target}")
                redis_cmd("SREM", "all_keys", target)
                send_tg_msg(chat_id, f"🗑️ Key `{target}` deleted permanently.")
            else:
                send_tg_msg(chat_id, "❌ Use format: `/del KeyName`")

    def do_GET(self):
        """Handles API Requests (?key=&num=)"""
        parsed_url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_url.query)
        
        user_key = params.get("key", [None])[0]
        number = params.get("num", [None])[0]

        if not user_key or not number:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "?key= and ?num= parameters are required."}).encode())
            return

        user_key = user_key.strip()
        number = number.strip()

        if not number.isdigit() or len(number) != 10:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_output = {
                "error": "Invalid number! Please enter a valid 10-digit mobile number.",
                "developer": "@the_detol"
            }
            self.wfile.write(json.dumps(error_output, indent=2, ensure_ascii=False).encode())
            return

        is_active = redis_cmd("GET", f"api:{user_key}")
        if not is_active:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_output = {
                "error": "API expired, contact to developer for buy key",
                "developer": "@the_detol"
            }
            self.wfile.write(json.dumps(error_output, indent=2, ensure_ascii=False).encode())
            return

        remaining = redis_cmd("DECR", f"limit:{user_key}")
        if remaining is None or int(remaining) < 0:
            redis_cmd("INCR", f"limit:{user_key}")
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_output = {
                "error": "Query limit exceeded for this key, contact to developer for buy key",
                "developer": "@the_detol"
            }
            self.wfile.write(json.dumps(error_output, indent=2, ensure_ascii=False).encode())
            return

        ttl_sec = redis_cmd("TTL", f"api:{user_key}")
        expires_info = format_ttl(ttl_sec)

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] Searched Number: {number}"
        redis_cmd("LPUSH", f"logs:{user_key}", log_entry)
        redis_cmd("LTRIM", f"logs:{user_key}", 0, 49)

        target_url = f"{get_endpoint()}&Number={number}"
        try:
            res = session.get(target_url, timeout=12)
            json_res = res.json()
            
            data_block = json_res.get("Data", {})
            main_records = data_block.get("Main_Records", [])
            alt_records = data_block.get("Alt_Records", [])
            raw_data = main_records + alt_records
            
        except Exception:
            redis_cmd("INCR", f"limit:{user_key}")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Source API offline or timeout."}).encode())
            return

        filtered_results = []
        seen = set()
        for item in raw_data:
            key_tup = (item.get("mobile"), item.get("name"), item.get("address"))
            if key_tup not in seen:
                seen.add(key_tup)
                filtered_results.append({
                    "mobile": item.get("mobile", "N/A"),
                    "name": item.get("name", "N/A"),
                    "father_name": item.get("fname", "N/A"),
                    "circle": item.get("circle", "N/A"),
                    "alt_mobile": item.get("alt", "N/A"),
                    "aadhar": item.get("aadhar", "N/A"),
                    "email": item.get("email", "N/A"),
                    "address": clean_address(item.get("address", ""))
                })

        output = {
            "status": "success",
            "OWNER": "@the_detol",
            "key_used": user_key,
            "queries_left": max(0, int(remaining)),
            "expires_in": expires_info,
            "total_records": len(filtered_results),
            "results": filtered_results
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(output, indent=2, ensure_ascii=False).encode())
