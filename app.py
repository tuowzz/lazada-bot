import os
import subprocess
import requests
from flask import Flask, request, jsonify

# ✅ ติดตั้ง lazop-sdk ถ้ายังไม่มี
try:
    from lazop import Client as lazopClient, Request as lazopRequest
except ModuleNotFoundError:
    subprocess.run(["pip", "install", "lazop-sdk"])
    from lazop import Client as lazopClient, Request as lazopRequest  # ลอง import ใหม่

# ✅ ตั้งค่า API Credentials
LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY", "132211")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET", "Xgs5j7N6SNvuVdHo9d6ybwd3LhVvaHVY")
LAZADA_ACCESS_TOKEN = os.getenv("LAZADA_ACCESS_TOKEN", "")
LAZADA_AFFILIATE_ID = os.getenv("LAZADA_AFFILIATE_ID", "272261049")  # ใส่ Affiliate ID

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"

app = Flask(__name__)

# ✅ เชื่อมต่อกับ Lazada API
def get_lazada_affiliate_link(keyword):
    client = lazopClient("https://api.lazada.co.th/rest", LAZADA_APP_KEY, LAZADA_APP_SECRET)
    request = lazopRequest("/marketing/getlink")
    request.add_api_param("userToken", LAZADA_ACCESS_TOKEN)
    request.add_api_param("inputType", "keyword")
    request.add_api_param("inputValue", keyword)
    request.add_api_param("mmCampaignId", "1")
    request.add_api_param("subAffId", LAZADA_AFFILIATE_ID)

    response = client.execute(request, LAZADA_ACCESS_TOKEN)

    try:
        data = response.body
        if "result" in data and data["result"]["success"]:
            return data["result"]["link"]
        else:
            return None
    except Exception as e:
        print(f"❌ Error fetching Lazada link: {str(e)}")
        return None

# ✅ ส่งข้อความกลับไปที่ LINE
def send_line_message(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(LINE_API_URL, headers=headers, json=payload)

# ✅ Webhook สำหรับรับข้อความจาก LINE
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "events" in data and len(data["events"]) > 0:
        event = data["events"][0]
        if event["type"] == "message" and event["message"]["type"] == "text":
            keyword = event["message"]["text"]
            reply_token = event["replyToken"]

            lazada_link = get_lazada_affiliate_link(keyword)

            if lazada_link:
                response_text = f"🛍 ค้นหาสินค้า: {keyword}\n🔗 {lazada_link}"
            else:
                response_text = f"❌ ไม่พบสินค้าสำหรับ: {keyword}"

            send_line_message(reply_token, response_text)

    return jsonify({"status": "ok"})

# ✅ หน้าแรกของเซิร์ฟเวอร์
@app.route("/")
def home():
    return "🚀 บอท Lazada + LINE พร้อมใช้งาน!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
