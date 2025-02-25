import os
import subprocess
import requests
import json
from flask import Flask, request, jsonify
from lazop import Client as lazopClient, Request as lazopRequest

# 🔹 ติดตั้ง lazop-sdk อัตโนมัติ ถ้ายังไม่มี
try:
    import lazop
except ModuleNotFoundError:
    subprocess.run(["pip", "install", "lazop-sdk"])

# 🔹 ตั้งค่าตัวแปร API
LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_ACCESS_TOKEN = os.getenv("LAZADA_ACCESS_TOKEN")  # ใช้ Access Token จาก OAuth2
LAZADA_AFFILIATE_ID = "272261049"  # ใส่ Affiliate ID ที่ได้รับจาก Lazada

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")  # 🔹 Token ของ LINE Bot API

app = Flask(__name__)

# ✅ ฟังก์ชันดึงลิงก์สินค้า Lazada ผ่าน API /marketing/getlink
def get_lazada_affiliate_link(product_id):
    url = "https://api.lazada.co.th/rest/marketing/getlink"
    
    client = lazopClient(url, LAZADA_APP_KEY, LAZADA_APP_SECRET)
    request = lazopRequest("/marketing/getlink")

    request.add_api_param("userToken", LAZADA_ACCESS_TOKEN)
    request.add_api_param("inputType", "productId")
    request.add_api_param("inputValue", product_id)  # ✅ ใส่ product_id ที่ค้นหา
    request.add_api_param("mmCampaignId", "1")
    request.add_api_param("dmInviteId", "1")
    request.add_api_param("subAffId", LAZADA_AFFILIATE_ID)
    request.add_api_param("subIdKey", "1")

    response = client.execute(request)

    response_data = json.loads(response.body)

    if response_data.get("result", {}).get("success"):
        return response_data["result"]["url"]
    else:
        return None

# ✅ ฟังก์ชันส่งข้อความกลับไปที่ LINE
def send_line_message(reply_token, message):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}],
    }

    requests.post(url, headers=headers, json=payload)

# ✅ Webhook รับข้อความจาก LINE และค้นหาสินค้า
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        events = data.get("events", [])

        if not events:
            return jsonify({"message": "No events received"}), 200

        for event in events:
            if event["type"] == "message" and event["message"]["type"] == "text":
                user_message = event["message"]["text"]
                reply_token = event["replyToken"]

                # 🔹 ค้นหาลิงก์สินค้า Lazada
                lazada_link = get_lazada_affiliate_link(user_message)

                if lazada_link:
                    response_text = f"🛍 สินค้าที่คุณค้นหา: {user_message}\n🔗 ลิงก์: {lazada_link}"
                else:
                    response_text = f"❌ ไม่พบสินค้าที่ตรงกับ '{user_message}'"

                # 🔹 ส่งกลับไปที่ LINE
                send_line_message(reply_token, response_text)

        return jsonify({"message": "Success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ หน้าแรกของเซิร์ฟเวอร์
@app.route("/")
def home():
    return "🚀 บอท Lazada + LINE พร้อมใช้งาน!"

# ✅ รันแอป
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
