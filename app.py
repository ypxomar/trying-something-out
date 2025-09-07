from flask import Flask, render_template, jsonify
import threading, random, string, requests, os, time

app = Flask(__name__)

# Your webhook (kept as requested)
WEBHOOK_URL = "https://discord.com/api/webhooks/1414069816465162330/zkYiHEGIudWkXkeHEVppeeWtqSuTo5MaXULSFsKvHSnVRPzQP1866Fk-MQbfyLl-Ye8w"
CODES_FILE = "generated_codes.txt"

running = False
generator_thread = None
logs = []  # in-memory logs (also persisted codes in file)

# ---------- helpers ----------
def append_log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{ts} - {msg}"
    print(entry)
    logs.append(entry)
    # keep logs size bounded
    if len(logs) > 500:
        del logs[:-500]

def load_generated_codes():
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_generated_code(code):
    try:
        with open(CODES_FILE, "a", encoding="utf-8") as f:
            f.write(code + "\n")
    except Exception as e:
        append_log(f"Error saving code to file: {e}")

def generate_unique_random_string(length=18):
    existing = load_generated_codes()
    while True:
        code = "".join(random.choices(string.ascii_letters + string.digits, k=length))
        if code not in existing:
            save_generated_code(code)
            return code

def send_webhook_message(message):
    try:
        r = requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
        if r.status_code in (200, 204):
            append_log(f"Webhook sent: {message.splitlines()[-1]}")
        else:
            append_log(f"Webhook returned {r.status_code}")
    except Exception as e:
        append_log(f"Webhook error: {e}")

# ---------- simulated checker (safe) ----------
def simulated_check_code(code):
    """
    Simulates checking the code. Retries on transient simulated errors
    until it returns 200 (valid) or 404 (invalid).
    """
    while True:
        r = random.random()
        # 5% chance of transient error -> retry
        if r < 0.05:
            append_log(f"⚠️ Transient error checking {code}, retrying...")
            time.sleep(0.5)
            continue
        # very small chance to simulate a valid code
        if r < 0.05 + 0.0005:
            return 200
        # otherwise invalid
        return 404

# ---------- generator ----------
def generator():
    append_log("Generator thread started.")
    while running:
        code = generate_unique_random_string()
        status = simulated_check_code(code)  # SAFE: simulated, not hitting Discord
        if status == 200:
            append_log(f"✅ VALID CODE FOUND: {code}")
            send_webhook_message(f"@everyone Here is a valid code\ndiscord.gift/{code}")
        elif status == 404:
            append_log(f"❌ Invalid: {code}")
        else:
            append_log(f"⚠️ Unexpected status for {code}: {status}")
        # small sleep to keep browser responsive and reduce CPU
        time.sleep(0.15)
    append_log("Generator thread stopped.")

# ---------- routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    global running, generator_thread
    if not running:
        running = True
        generator_thread = threading.Thread(target=generator, daemon=True)
        generator_thread.start()
        append_log("Start requested.")
    return jsonify({"running": running})

@app.route("/stop", methods=["POST"])
def stop():
    global running
    running = False
    append_log("Stop requested.")
    return jsonify({"running": running})

@app.route("/status")
def status():
    return jsonify({"running": running})

@app.route("/logs")
def get_logs():
    # return last 200 logs
    return jsonify({"logs": logs[-200:]})

if __name__ == "__main__":
    append_log("App starting. Open http://127.0.0.1:5000")
    app.run(debug=True)
