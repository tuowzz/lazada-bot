import os
import time
import hmac
import hashlib
import requests
import urllib.parse
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ Lazada API Credentials
LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_ACCESS_TOKEN = os.getenv("LAZADA_ACCESS_TOKEN")
LAZADA_AFFILIATE_ID = os.getenv("LAZADA_AFFILIATE_ID")

# ✅ LINE API Credentials
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# ✅ ฟังก์ชัน Debug Log
def debug_log(message):
    print(f"🛠 DEBUG: {message}")

# ✅ ฟังก์ชันสร้าง Signature สำหรับ Lazada API
def generate_signature(api_path, params):
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    base_string = api_path + "".join(f"{k}{v}" for k, v in sorted_params)
    signature = hmac.new(
        LAZADA_APP_SECRET.encode(), base_string.encode(), hashlib.sha256
    ).hexdigest().upper()
    return signature

# ✅ ค้นหาสินค้าบน Lazada
def get_best_selling_lazada(keyword):
    api_path = "/marketing/getlink"
    url = f"https://api.lazada.co.th/rest{api_path}"
    params = {
        "app_key": LAZADA_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "access_token": LAZADA_ACCESS_TOKEN,
        "inputType": "productid",
        "inputValue": keyword,
        "mmCampaignId": "1"
    }
    params["sign"] = generate_signature(api_path, params)
    response = requests.get(url, params=params).json()
    debug_log(f"Lazada Get Link Response: {response}")
    if response.get("result", {}).get("success"):
        return response["result"]["url"]
    return None

# ✅ ฟังก์ชันส่งข้อความกลับไปยัง LINE
def send_line_message(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    response = requests.post(url, headers=headers, json=payload).json()
    debug_log(f"LINE API Response: {response}")

# ✅ Webhook API สำหรับรับคำค้นหาและสร้างลิงก์
def process_lazada_request(keyword):
    product_url = get_best_selling_lazada(keyword)
    if not product_url:
        product_url = f"https://www.lazada.co.th/catalog/?q={urllib.parse.quote(keyword)}"
    return product_url

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    debug_log(f"Received Data: {data}")
    if "events" not in data or not data["events"]:
        return jsonify({"error": "❌ No events received"}), 400
    for event in data["events"]:
        if event["type"] == "message" and "text" in event["message"]:
            keyword = event["message"]["text"]
            reply_token = event["replyToken"]
            product_url = process_lazada_request(keyword)
            response_text = f"🔎 ค้นหาสินค้าเกี่ยวกับ: {keyword}\n\n🛍 สั่งซื้อที่ Lazada: {product_url}"
            send_line_message(reply_token, response_text)
    return jsonify({"message": "✅ Success"}), 200

# ✅ รัน Flask บนพอร์ต 8080
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug_log(f"🚀 บอท Lazada + LINE พร้อมใช้งานบนพอร์ต {port}!")
    app.run(host="0.0.0.0", port=port)
