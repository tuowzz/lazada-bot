import os
import time
import hmac
import hashlib
import requests
import urllib.parse
import json
from flask import Flask, request, jsonify
from lazop import Client as lazopClient

app = Flask(__name__)

# ✅ โหลดค่า API Keys และ Tokens จาก Environment Variables
LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_USER_TOKEN = os.getenv("LAZADA_USER_TOKEN")  # 🔹 userToken ต้องได้จาก OAuth
LAZADA_AFFILIATE_ID = "272261049"  # ✅ Affiliate ID

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")  # 🔹 ใช้ส่งข้อความกลับ LINE

# ✅ กำหนด Lazada API Client
LAZADA_API_URL = "https://api.lazada.co.th/rest"
client = lazop.LazopClient(LAZADA_API_URL, LAZADA_APP_KEY, LAZADA_APP_SECRET)


# ✅ ฟังก์ชันสร้าง Signature สำหรับ Lazada API
def generate_signature(params):
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    base_string = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in sorted_params)
    signature = hmac.new(
        LAZADA_APP_SECRET.encode(), base_string.encode(), hashlib.sha256
    ).hexdigest().upper()
    return signature


# ✅ ฟังก์ชันค้นหาสินค้าและสร้างลิงก์ Affiliate
def get_lazada_affiliate_link(keyword):
    request = lazop.LazopRequest('/marketing/getlink', "POST")
    request.add_api_param('subId1', 'line_bot')
    request.add_api_param('userToken', LAZADA_USER_TOKEN)
    request.add_api_param('inputType', 'keyword')
    request.add_api_param('inputValue', keyword)
    request.add_api_param('subAffId', LAZADA_AFFILIATE_ID)

    response = client.execute(request)
    result = response.body

    if result.get("result", {}).get("success", False):
        return result["result"]["linkList"][0]["shortUrl"]  # ✅ ดึงลิงก์แบบสั้น
    return None


# ✅ ฟังก์ชันส่งข้อความกลับไปที่ LINE
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

    response = requests.post(url, headers=headers, json=payload)
    print(f"🛠 DEBUG: LINE API Response: {response.json()}")


# ✅ Webhook API สำหรับรับข้อความจาก LINE
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print(f"🛠 DEBUG: Received Data: {data}")

        if "events" not in data or not data["events"]:
            return jsonify({"status": "No events"}), 400

        for event in data["events"]:
            if event["type"] == "message" and event["message"]["type"] == "text":
                keyword = event["message"]["text"]
                reply_token = event["replyToken"]

                # ✅ ค้นหาสินค้า Lazada
                lazada_link = get_lazada_affiliate_link(keyword)

                if lazada_link:
                    response_text = f"🔎 ค้นหาสินค้าเกี่ยวกับ: {keyword}\n🛍 สั่งซื้อที่ Lazada: {lazada_link}"
                else:
                    response_text = f"⚠️ ไม่พบสินค้าสำหรับคำค้น '{keyword}'\nกรุณาลองค้นหาใหม่"

                # ✅ ส่งข้อความกลับไปที่ LINE
                send_line_message(reply_token, response_text)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


# ✅ ให้ Flask ใช้พอร์ต 8080
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 บอท Lazada + LINE พร้อมใช้งานที่พอร์ต {port}!")
    app.run(host="0.0.0.0", port=port)

