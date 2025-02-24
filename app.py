from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 บอท Lazada + LINE พร้อมใช้งาน!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("🔹 Received Data:", data)
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
