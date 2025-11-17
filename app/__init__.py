from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from config import config

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    # CORS Configuration - Allow all origins for development
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # JWT Error Handlers
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        from flask import jsonify
        app.logger.error(f'Invalid token: {error_string}')
        return jsonify({'error': 'Invalid token', 'details': error_string}), 422

    @jwt.unauthorized_loader
    def unauthorized_callback(error_string):
        from flask import jsonify
        app.logger.error(f'Unauthorized: {error_string}')
        return jsonify({'error': 'Missing Authorization Header', 'details': error_string}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        from flask import jsonify
        app.logger.error('Token has expired')
        return jsonify({'error': 'Token has expired'}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        from flask import jsonify
        app.logger.error('Token has been revoked')
        return jsonify({'error': 'Token has been revoked'}), 401

    # Register blueprints
    from app.routes import auth, groups, expenses, payments, admin, dashboard, recurring, exports, payment_gateway, receipts

    app.register_blueprint(auth.bp)
    app.register_blueprint(groups.bp)
    app.register_blueprint(expenses.bp)
    app.register_blueprint(payments.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(recurring.bp)
    app.register_blueprint(exports.bp)
    app.register_blueprint(payment_gateway.bp)
    app.register_blueprint(receipts.bp)

    # Frontend routes
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')

    @app.route('/login')
    def login_page():
        from flask import render_template
        return render_template('login.html')

    @app.route('/register')
    def register_page():
        from flask import render_template
        return render_template('register.html')

    @app.route('/dashboard')
    def dashboard_page():
        from flask import render_template
        return render_template('dashboard.html')

    @app.route('/groups')
    def groups_page():
        from flask import render_template
        return render_template('groups.html')

    @app.route('/groups/<int:group_id>')
    def group_detail_page(group_id):
        from flask import render_template
        return render_template('group_detail.html')

    @app.route('/expenses')
    def expenses_page():
        from flask import render_template
        return render_template('expenses.html')

    @app.route('/settlements')
    def settlements_page():
        from flask import render_template
        return render_template('settlements.html')

    @app.route('/profile')
    def profile_page():
        from flask import render_template
        return render_template('profile.html')

    @app.route('/admin')
    def admin_page():
        from flask import render_template
        return render_template('admin.html')

    @app.route('/test-jwt')
    def test_jwt_page():
        from flask import send_file
        import os
        return send_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_jwt.html'))

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
