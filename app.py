import os
from app import create_app

# Vercel tự set FLASK_ENV=production
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)

# === XÓA HOÀN TOÀN app.run() ===
# if __name__ == '__main__':
#     app.run()