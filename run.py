import os
from app import create_app

# Lấy config từ environment (Vercel tự set)
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)

# === XÓA HOÀN TOÀN DÒNG NÀY ===
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)

# === THÊM DÒNG NÀY ĐỂ VERCEL NHẬN DIỆN ===
# Vercel cần biến `app` là WSGI object → đã có rồi!