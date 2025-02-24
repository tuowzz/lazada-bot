from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

LAZADA_ACCESS_TOKEN = "ใส่ Access Token"
LINE_ACCESS_TOKEN = "ใส่ Access Token ของ LINE"

def search_lazada(keyword):
    """ ดึงสินค้าขายดีจาก Lazada """
    url = "https://api.lazada.co.th/rest/products/search"
    params = {
        "access_token": LAZADA_ACCESS_TOKEN,
        "format": "JSON",
        "q": keyword,
        "sort_by": "sales_volume"
    }
    response = requests.get(url, params=params).json()
    
    if "data" in response and "products" in response["data"]:
        best_product = response["data"]["products"][0]
        return best_product["url"], best_product["name"]
    
    return None, None

def send_line_message(reply_token, message):
    """ ส่งข้อความกลับไปที่ LINE """
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    payload = {"replyToken": reply_token, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

@app.route("/webhook", methods=["POST"])
def webhook():
    """ รับข้อความจาก LINE และค้นหาสินค้าใน Lazada """
    data = request.get_json()
    
    if "events" in data and len(data["events"]) > 0:
        event = data["events"][0]
        user_message = event["message"]["text"]
        reply_token = event["replyToken"]
        
        product_url, product_name = search_lazada(user_message)
        if product_url:
            response_text = f"🔎 ค้นหาสินค้าเกี่ยวกับ: {user_message}\n🛍 {product_name}\n➡️ {product_url}"
        else:
            response_text = f"❌ ไม่พบสินค้าที่ตรงกับ '{user_message}'"

        send_line_message(reply_token, response_text)

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
