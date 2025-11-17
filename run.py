from flask import Flask

app = Flask(__name__)  # PHẢI TÊN "app"

@app.route("/")
def home():
    return {"message": "Hello from Flask on Vercel! 🚀"}

# Thêm các route khác của bạn ở đây
# Ví dụ:
# @app.route("/api")
# def api():
#     return {"status": "ok"}

# === QUAN TRỌNG: KHÔNG DÙNG app.run() ===
# XÓA DÒNG NÀY NẾU CÓ:
# if __name__ == "__main__":
#     app.run(debug=True)