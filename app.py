import os
import json
import time
import hmac
import hashlib
import requests
import urllib.parse
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ โหลดค่าตัวแปร Environment จาก Railway
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_ACCESS_TOKEN = os.getenv("LAZADA_ACCESS_TOKEN")
LAZADA_AFFILIATE_ID = os.getenv("LAZADA_AFFILIATE_ID")

# ✅ ฟังก์ชัน Debug Log
def debug_log(message):
    print(f"🛠 DEBUG: {message}")

# ✅ ฟังก์ชันสร้าง Signature สำหรับ Lazada API
def generate_signature(params):
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    base_string = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in sorted_params)
    signature = hmac.new(
        LAZADA_APP_SECRET.encode(), base_string.encode(), hashlib.sha256
    ).hexdigest().upper()
    return signature

# ✅ ฟังก์ชันค้นหาสินค้าขายดีบน Lazada
def get_best_selling_lazada(keyword):
    endpoint = "https://api.lazada.co.th/rest/marketing/getlink"
    params = {
        "app_key": LAZADA_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "access_token": LAZADA_ACCESS_TOKEN,
        "format": "JSON",
        "v": "1.0",
        "inputType": "keyword",
        "inputValue": keyword,
        "subAffId": LAZADA_AFFILIATE_ID
    }

    params["sign"] = generate_signature(params)
    headers = {"Content-Type": "application/json; charset=UTF-8"}

    response = requests.get(endpoint, params=params, headers=headers).json()
    
    debug_log(f"Lazada Search Response: {response}")

    if "data" in response and "shortUrl" in response["data"]:
        return response["data"]["shortUrl"]

    return None

# ✅ ฟังก์ชันส่งข้อความกลับไปที่ LINE
def send_line_message(reply_token, message):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }

    response = requests.post(url, headers=headers, json=payload)

    debug_log(f"LINE API Response: {response.json()}")

    return response.json()

# ✅ Webhook API สำหรับรับข้อความจาก LINE
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        debug_log(f"Received Data: {json.dumps(data, ensure_ascii=False)}")  # ✅ รองรับภาษาไทย

        if not data or "events" not in data:
            return jsonify({"error": "❌ ไม่มีข้อมูลที่ส่งมา"}), 400

        for event in data["events"]:
            if event.get("type") == "message" and event["message"].get("type") == "text":
                user_id = event["source"]["userId"]
                text = event["message"]["text"]
                reply_token = event["replyToken"]

                # ✅ ค้นหาสินค้า Lazada
                lazada_link = get_best_selling_lazada(text)

                if not lazada_link:
                    message = "❌ ไม่พบสินค้าตามคำค้นหาของคุณ"
                else:
                    message = f"🔎 ค้นหาสินค้าเกี่ยวกับ: {text}\n➡️ {lazada_link}"

                send_line_message(reply_token, message)

        return jsonify({"status": "✅ Success"}), 200

    except Exception as e:
        debug_log(f"❌ Error: {str(e)}")
        return jsonify({"error": f"❌ Internal Server Error: {str(e)}"}), 500

# ✅ ให้ Flask ใช้พอร์ตที่ถูกต้อง
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_log(f"🚀 บอท Lazada + LINE พร้อมใช้งาน! กำลังรันที่พอร์ต {port}...")
    app.run(host="0.0.0.0", port=port)
