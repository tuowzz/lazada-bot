import os
import logging
from time import time
import requests
from flask import Flask, request, jsonify
from lazop import Client as lazopClient, Request as lazopRequest
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ตั้งค่า API Credentials (ใช้ environment variables เท่านั้น)
LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_ACCESS_TOKEN = os.getenv("LAZADA_ACCESS_TOKEN")
LAZADA_AFFILIATE_ID = os.getenv("LAZADA_AFFILIATE_ID", "272261049")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"

# ตรวจสอบว่าตั้งค่า credentials ครบหรือไม่
if not all([LAZADA_APP_KEY, LAZADA_APP_SECRET, LAZADA_ACCESS_TOKEN, LINE_CHANNEL_ACCESS_TOKEN]):
    raise ValueError("Missing required environment variables")

app = Flask(__name__)

# ตั้งค่า requests session พร้อม retry
session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

# เชื่อมต่อกับ Lazada API
def get_lazada_affiliate_link(keyword):
    try:
        client = lazopClient("https://api.lazada.co.th/rest", LAZADA_APP_KEY, LAZADA_APP_SECRET)
        req = lazopRequest("/marketing/getlink")
        req.add_api_param("userToken", LAZADA_ACCESS_TOKEN)
        req.add_api_param("inputType", "keyword")
        req.add_api_param("inputValue", keyword)
        req.add_api_param("mmCampaignId", "1")
        req.add_api_param("subAffId", LAZADA_AFFILIATE_ID)

        response = client.execute(req, LAZADA_ACCESS_TOKEN)
        data = response.body

        if isinstance(data, dict) and "result" in data and data["result"]["success"]:
            return data["result"]["link"]
        else:
            logger.error(f"Lazada API error: {data}")
            return None
    except Exception as e:
        logger.error(f"Error fetching Lazada link: {str(e)}")
        return None

# ส่งข้อความกลับไปที่ LINE
def send_line_message(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text[:5000]}]  # จำกัดความยาวข้อความ
    }
    try:
        response = session.post(LINE_API_URL, headers=headers, json=payload, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send LINE message: {str(e)}")

# Webhook สำหรับรับข้อความจาก LINE
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data or "events" not in data or not data["events"]:
            return jsonify({"status": "no events"}), 400

        event = data["events"][0]
        if event["type"] == "message" and event["message"]["type"] == "text":
            keyword = event["message"]["text"].strip()
            reply_token = event["replyToken"]

            lazada_link = get_lazada_affiliate_link(keyword)
            response_text = (
                f"🛍 ค้นหาสินค้า: {keyword}\n🔗 {lazada_link}"
                if lazada_link else f"❌ ไม่พบสินค้าสำหรับ: {keyword}"
            )
            send_line_message(reply_token, response_text)

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"status": "error"}), 500

# หน้าแรกของเซิร์ฟเวอร์
@app.route("/")
def home():
    return "🚀 บอท Lazada + LINE พร้อมใช้งาน!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
