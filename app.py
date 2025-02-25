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
LAZADA_REFRESH_TOKEN = os.getenv("LAZADA_REFRESH_TOKEN")  # ใช้รีเฟรช Access Token
LAZADA_AFFILIATE_ID = os.getenv("LAZADA_AFFILIATE_ID")

# ✅ LINE Bot Credentials
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")

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

# ✅ ฟังก์ชันรีเฟรช Access Token อัตโนมัติ
def refresh_lazada_token():
    global LAZADA_ACCESS_TOKEN
    url = "https://auth.lazada.com/rest/token"
    params = {
        "app_key": LAZADA_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "grant_type": "refresh_token",
        "refresh_token": LAZADA_REFRESH_TOKEN
    }
    params["sign"] = generate_signature(params)
    
    response = requests.post(url, data=params).json()
    debug_log(f"Lazada Refresh Token Response: {response}")

    if "access_token" in response:
        LAZADA_ACCESS_TOKEN = response["access_token"]
        return True
    return False

# ✅ ฟังก์ชันดึงลิงก์ Affiliate ของ Lazada
def get_lazada_affiliate_link(product_id):
    global LAZADA_ACCESS_TOKEN
    url = "https://api.lazada.co.th/rest/marketing/getlink"
    params = {
        "app_key": LAZADA_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "access_token": LAZADA_ACCESS_TOKEN,
        "format": "JSON",
        "v": "1.0",
        "inputType": "productid",
        "inputValue": product_id,
        "tracking_id": LAZADA_AFFILIATE_ID
    }
    params["sign"] = generate_signature(params)

    response = requests.get(url, params=params).json()
    debug_log(f"Lazada Get Link Response: {response}")

    if response.get("code") == "InvalidToken":
        if refresh_lazada_token():
            return get_lazada_affiliate_link(product_id)  # รีลองหลังจาก Refresh Token
        return None

    return response["data"]["aff_link"] if "data" in response else None

# ✅ ฟังก์ชันส่งข้อความไป LINE
def send_line_message(reply_token, message):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    response = requests.post(url, headers=headers, json=payload).json()
    debug_log(f"LINE API Response: {response}")

# ✅ Webhook สำหรับ LINE Bot
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        debug_log(f"Received Data: {data}")

        if not data or "events" not in data or not data["events"]:
            return jsonify({"error": "❌ ไม่มีข้อมูลที่ส่งมา"}), 400

        event = data["events"][0]
        reply_token = event["replyToken"]
        keyword = event["message"]["text"]

        # ✅ ใช้ API Lazada ดึงลิงก์สินค้า
        affiliate_link = get_lazada_affiliate_link(keyword)

        if affiliate_link:
            response_text = f"🛍 คลิกเพื่อซื้อ: {affiliate_link}"
        else:
            response_text = f"❌ ไม่พบสินค้าใน Lazada\n🔎 ลองค้นหาเอง: https://www.lazada.co.th/catalog/?q={urllib.parse.quote(keyword)}"

        send_line_message(reply_token, response_text)
        return jsonify({"status": "success"}), 200

    except Exception as e:
        debug_log(f"❌ Error: {str(e)}")
        return jsonify({"error": f"❌ Internal Server Error: {str(e)}"}), 500

# ✅ เริ่ม Flask Server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # ใช้ port 8080
    debug_log(f"✅ Starting Flask on port {port}...")
    app.run(host="0.0.0.0", port=port)
