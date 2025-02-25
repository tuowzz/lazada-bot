import os
import time
import hmac
import hashlib
import requests
import urllib.parse
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ โหลด API Keys
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")  # Long-lived Token
LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_USER_TOKEN = os.getenv("LAZADA_USER_TOKEN")  # ตรวจสอบว่า Token ถูกต้อง
LAZADA_AFFILIATE_ID = os.getenv("LAZADA_AFFILIATE_ID")

# ✅ ฟังก์ชัน Debug Log
def debug_log(message):
    print(f"🛠 DEBUG: {message}")

# ✅ ฟังก์ชันสร้าง Signature สำหรับ Lazada API
def generate_signature(params):
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    base_string = LAZADA_APP_SECRET + "".join(f"{k}{v}" for k, v in sorted_params)
    signature = hmac.new(
        LAZADA_APP_SECRET.encode(), base_string.encode(), hashlib.sha256
    ).hexdigest().upper()
    return signature

# ✅ ฟังก์ชันค้นหาสินค้าขายดีจาก Lazada API (Fallback ใช้ Google ถ้า API พัง)
def get_best_selling_lazada(keyword):
    endpoint = "https://api.lazada.co.th/rest/products/search"
    params = {
        "app_key": LAZADA_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "access_token": LAZADA_USER_TOKEN,
        "format": "JSON",
        "v": "1.0",
        "q": keyword,
        "sort_by": "sales_volume"
    }

    params["sign"] = generate_signature(params)
    debug_log(f"📤 Lazada API Request: {params}")

    try:
        response = requests.get(endpoint, params=params).json()
        debug_log(f"📥 Lazada API Response: {response}")

        if "data" in response and "products" in response["data"]:
            best_product = sorted(response["data"]["products"], key=lambda x: x["sales"], reverse=True)[0]
            return best_product["url"], best_product["name"]
        else:
            raise Exception("❌ ไม่พบสินค้าจาก Lazada API")

    except Exception as e:
        debug_log(f"🚨 Lazada API พัง! ใช้ Google Search แทน: {str(e)}")
        google_search_url = f"https://www.google.com/search?q={urllib.parse.quote(keyword)}+site%3Alazada.co.th"
        return google_search_url, f"🔎 ค้นหาสินค้าจาก Google: {keyword}"

# ✅ ฟังก์ชันสร้างลิงก์ Affiliate จาก Lazada API (ถ้าล้มเหลว ใช้ลิงก์ค้นหาสินค้า)
def generate_lazada_affiliate_link(product_url):
    endpoint = "https://api.lazada.co.th/rest/affiliate/link/generate"
    params = {
        "app_key": LAZADA_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "access_token": LAZADA_USER_TOKEN,
        "format": "JSON",
        "v": "1.0",
        "tracking_id": LAZADA_AFFILIATE_ID,
        "url": product_url
    }

    params["sign"] = generate_signature(params)
    debug_log(f"📤 Lazada Affiliate Request: {params}")

    try:
        response = requests.get(endpoint, params=params).json()
        debug_log(f"📥 Lazada Affiliate Response: {response}")

        if "data" in response and "aff_link" in response["data"]:
            return response["data"]["aff_link"]
        else:
            raise Exception("❌ ไม่สามารถสร้างลิงก์ Affiliate ได้")
    
    except Exception as e:
        debug_log(f"🚨 Lazada Affiliate พัง! ใช้ลิงก์ค้นหาสินค้าแทน: {str(e)}")
        return product_url  # กลับไปใช้ลิงก์ที่ค้นหามาแทน

# ✅ ฟังก์ชันส่งข้อความกลับไปที่ LINE
def send_line_message(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    response = requests.post(url, headers=headers, json=payload)
    debug_log(f"📤 LINE API Request: {payload}")
    debug_log(f"📥 LINE API Response: {response.json()}")

# ✅ Webhook API ที่รับคำค้นหาและสร้างลิงก์ Lazada
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        debug_log(f"📥 Received Data: {data}")

        if not data or "events" not in data or len(data["events"]) == 0:
            return jsonify({"error": "❌ ไม่มีข้อมูลที่ส่งมา"}), 400

        event = data["events"][0]
        if "message" not in event or "text" not in event["message"]:
            return jsonify({"error": "❌ ไม่มีข้อความที่ส่งมา"}), 400

        user_message = event["message"]["text"]
        reply_token = event["replyToken"]

        product_url, product_name = get_best_selling_lazada(user_message)
        lazada_link = generate_lazada_affiliate_link(product_url)

        response_text = (
            f"🔎 ค้นหาสินค้าเกี่ยวกับ: {user_message}\n\n"
            f"📌 สินค้า: {product_name}\n"
            f"🛍 Lazada: {lazada_link}\n\n"
            f"🔥 โปรโมชั่นมาแรง! รีบสั่งซื้อตอนนี้ก่อนสินค้าหมด 🔥"
        )

        send_line_message(reply_token, response_text)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        debug_log(f"❌ Error: {str(e)}")
        return jsonify({"error": f"❌ Internal Server Error: {str(e)}"}), 500

# ✅ ให้ Flask ใช้พอร์ตที่ถูกต้อง
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug_log(f"✅ Starting Flask on port {port}...")
    app.run(host="0.0.0.0", port=port)
