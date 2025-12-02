from flask import Flask, request, jsonify, redirect
import time, base64, requests, re

app = Flask(__name__)
ip_data = {}

@app.before_request
def rate_limit():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    now = time.time()
    data = ip_data.get(ip, {"timestamps": [], "blocked": 0})
    if data["blocked"] > now:
        return jsonify({"error": "IP temporarily blocked", "until": time.ctime(data["blocked"])}), 429

    # chỉ giữ log trong 1h
    data["timestamps"] = [t for t in data["timestamps"] if now - t < 3600]
    data["timestamps"].append(now)

    # tính trong 1s / 1p / 1h
    last_1s = len([t for t in data["timestamps"] if now - t < 1])
    last_1m = len([t for t in data["timestamps"] if now - t < 60])
    last_1h = len(data["timestamps"])

    # giới hạn
    if last_1s > 5 or last_1m > 20 or last_1h > 50:
        block_time = now + (1800 if last_1m > 50 else 60)  # block 30p hoặc 1p
        data["blocked"] = block_time
        ip_data[ip] = data
        return jsonify({"error": "Too many requests, IP temporarily blocked"}), 429

    ip_data[ip] = data

def is_valid_webhook_path(path):
    # path dạng: api/webhooks/<id>/<token> (id là số)
    return re.match(r"^api/webhooks/\d+/[\w-]+$", path) is not None

@app.route("/<path:encoded>", methods=["POST"])
def relay(encoded):
    try:
        decoded_bytes = base64.b64decode(encoded)
        decoded = decoded_bytes.decode("utf-8")
    except Exception:
        return jsonify({"error": "Invalid base64"}), 400

    if not is_valid_webhook_path(decoded):
        return jsonify({"error": "Invalid webhook path"}), 400

    try:
        resp = requests.post(
            f"https://discord.com/{decoded}",
            data=request.data,
            headers={"Content-Type": "application/json"}
        )
        return jsonify({"status": resp.status_code, "response": resp.text}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/")
def home():
    return redirect("https://discord.gg/HcxFCR3ZTQ")
