import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ ตั้งค่า LINE และ Lazada Affiliate
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")  # ใช้ Token ของคุณ
LAZADA_AFFILIATE_ID = "272261049"  # Lazada Affiliate ID ของคุณ

# ✅ ฟังก์ชันสร้างลิงก์ Lazada Affiliate
def generate_lazada_link(keyword):
    return f"https://www.lazada.co.th/catalog/?q={keyword}&sub_aff_id={LAZADA_AFFILIATE_ID}"

# ✅ ฟังก์ชันส่งข้อความกลับไปยัง LINE
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
    requests.post(url, headers=headers, json=payload)

# ✅ Webhook API
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    # ✅ ตรวจสอบว่ามีข้อความจาก LINE Bot หรือไม่
    if "events" in data and len(data["events"]) > 0:
        event = data["events"][0]

        if event["type"] == "message" and event["message"]["type"] == "text":
            keyword = event["message"]["text"]
            reply_token = event["replyToken"]

            # ✅ สร้างลิงก์ Lazada Affiliate
            lazada_link = generate_lazada_link(keyword)

            response_text = f"🔎 ค้นหาสินค้าเกี่ยวกับ: {keyword}\n\n" \
                            f"🛍 Lazada: {lazada_link}\n\n" \
                            f"🔥 โปรโมชั่นมาแรง! รีบสั่งซื้อตอนนี้ก่อนสินค้าหมด 🔥"

            # ✅ ส่งข้อความกลับไปยัง LINE
            send_line_message(reply_token, response_text)

    return jsonify({"status": "ok"})

# ✅ รันเซิร์ฟเวอร์ (ใช้ PORT 8080)
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))  # เปลี่ยนเป็น 8080
    app.run(host="0.0.0.0", port=port)
