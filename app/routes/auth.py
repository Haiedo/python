from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from app import db
from app.models.user import User
from app.utils.validators import validate_email, validate_phone

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Username, email, and password are required'}), 400

    # Validate email format
    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    # Validate phone if provided
    if data.get('phone') and not validate_phone(data['phone']):
        return jsonify({'error': 'Invalid phone number format'}), 400

    # Check if username or email already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        full_name=data.get('full_name'),
        phone=data.get('phone')
    )
    user.set_password(data['password'])

    try:
        db.session.add(user)
        db.session.commit()

        # Generate tokens (identity must be string)
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(include_sensitive=True),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT tokens"""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400

    # Find user by username or email
    user = User.query.filter(
        (User.username == data['username']) | (User.email == data['username'])
    ).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 403

    # Generate tokens (identity must be string)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    from flask import current_app
    current_app.logger.info(f'Login successful for user {user.id}, token generated')
    current_app.logger.info(f'Access token (first 20 chars): {access_token[:20]}...')

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(include_sensitive=True),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    current_user_id = get_jwt_identity()
    # Ensure identity is string
    access_token = create_access_token(identity=str(current_user_id))

    return jsonify({
        'access_token': access_token
    }), 200


@bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    user_id = int(get_jwt_identity())  # Convert string to int
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'user': user.to_dict(include_sensitive=True)
    }), 200


@bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    user_id = int(get_jwt_identity())  # Convert string to int
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    # Update allowed fields
    if 'full_name' in data:
        user.full_name = data['full_name']

    if 'phone' in data:
        if not validate_phone(data['phone']):
            return jsonify({'error': 'Invalid phone number format'}), 400
        user.phone = data['phone']

    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']

    if 'bank_name' in data:
        user.bank_name = data['bank_name']

    if 'bank_account_number' in data:
        user.bank_account_number = data['bank_account_number']

    if 'bank_account_name' in data:
        user.bank_account_name = data['bank_account_name']

    # Update password if provided
    if 'password' in data and data['password']:
        user.set_password(data['password'])

    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict(include_sensitive=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    user_id = int(get_jwt_identity())  # Convert string to int
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    # Validate required fields
    if not data or not data.get('old_password') or not data.get('new_password'):
        return jsonify({'error': 'Old password and new password are required'}), 400

    # Verify old password
    if not user.check_password(data['old_password']):
        return jsonify({'error': 'Current password is incorrect'}), 401

    # Validate new password
    if len(data['new_password']) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400

    # Update password
    user.set_password(data['new_password'])

    try:
        db.session.commit()
        return jsonify({
            'message': 'Password changed successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Password change failed: {str(e)}'}), 500


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should delete tokens)"""
    # In a production app, you might want to blacklist the token here
    return jsonify({'message': 'Logout successful'}), 200


@bp.route('/test-token', methods=['GET'])
@jwt_required()
def test_token():
    """Test endpoint to verify JWT token is working"""
    from flask import current_app, request
    user_id = get_jwt_identity()  # This is now a string
    current_app.logger.info(f'Token test - User ID: {user_id} (type: {type(user_id)})')
    current_app.logger.info(f'Headers: {dict(request.headers)}')

    return jsonify({
        'message': 'Token is valid!',
        'user_id': user_id,
        'user_id_type': str(type(user_id))
    }), 200
