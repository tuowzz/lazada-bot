import os
import lazop
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ ตั้งค่า Lazada API
LAZADA_APP_KEY = os.getenv("LAZADA_APP_KEY")
LAZADA_APP_SECRET = os.getenv("LAZADA_APP_SECRET")
LAZADA_ACCESS_TOKEN = os.getenv("LAZADA_ACCESS_TOKEN")  # ใช้ Access Token ที่ถูกต้อง
LAZADA_AFFILIATE_ID = "272261049"  # 🔹 ใส่ Affiliate ID ที่ได้มา

# ✅ ตั้งค่า LINE API
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"

# ✅ ฟังก์ชันสร้างลิงก์สินค้า Lazada
def get_lazada_affiliate_link(keyword):
    url = "https://api.lazada.co.th/rest"
    client = lazop.LazopClient(url, LAZADA_APP_KEY, LAZADA_APP_SECRET)
    request = lazop.LazopRequest('/marketing/getlink')

    # ✅ กำหนดค่าพารามิเตอร์
    request.add_api_param('userToken', LAZADA_ACCESS_TOKEN)
    request.add_api_param('inputType', 'keyword')  # ค้นหาตามชื่อสินค้า
    request.add_api_param('inputValue', keyword)
    request.add_api_param('mmCampaignId', '1')
    request.add_api_param('dmInviteId', '1')
    request.add_api_param('subAffId', LAZADA_AFFILIATE_ID)

    # ✅ ส่งคำขอไปที่ Lazada API
    response = client.execute(request)
    result = response.body

    # ✅ ตรวจสอบว่ามีลิงก์หรือไม่
    if result.get("result", {}).get("success", False):
        return result["result"]["data"]["aff_link"]  # ✅ ลิงก์ Affiliate
    else:
        return None  # ❌ ไม่พบสินค้า

# ✅ ฟังก์ชันส่งข้อความกลับ LINE
def send_line_message(reply_token, text):
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    response = requests.post(LINE_API_URL, headers=headers, json=payload)
    return response.json()

# ✅ Webhook รับข้อความจาก LINE
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"🛠 DEBUG: Received Data: {data}")

    if "events" in data and len(data["events"]) > 0:
        event = data["events"][0]  # รับ Event แรก
        user_message = event["message"]["text"]
        reply_token = event["replyToken"]

        # ✅ ดึงลิงก์สินค้าจาก Lazada
        lazada_link = get_lazada_affiliate_link(user_message)

        if lazada_link:
            response_text = f"🛍 สินค้าที่คุณค้นหา: {user_message}\n🔗 ลิงก์สินค้า: {lazada_link}"
        else:
            response_text = f"❌ ไม่พบสินค้าที่ตรงกับ '{user_message}'"

        # ✅ ส่งข้อความกลับ LINE
        send_line_message(reply_token, response_text)

    return jsonify({"status": "success"}), 200

# ✅ รัน Flask Server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 บอท Lazada + LINE พร้อมใช้งานที่พอร์ต {port}")
    app.run(host="0.0.0.0", port=port)
