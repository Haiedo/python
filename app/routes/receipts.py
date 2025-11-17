import os
from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db
from app.models.expense import Expense
from app.models.group import GroupMember
from flask import current_app

bp = Blueprint('receipts', __name__, url_prefix='/api/receipts')


def allowed_file(filename):
    """Check if file extension is allowed"""
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'pdf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_receipt():
    """
    Upload receipt image/PDF

    Form data:
        file: Receipt file
        expense_id: Optional expense ID to attach to
    """
    user_id = int(get_jwt_identity())  # Convert string to int

    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Create uploads directory if not exists
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Generate secure filename
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{user_id}_{timestamp}_{filename}"
    filepath = os.path.join(upload_folder, unique_filename)

    # Save file
    try:
        file.save(filepath)
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

    # Get expense ID if provided
    expense_id = request.form.get('expense_id')

    if expense_id:
        expense = Expense.query.get(expense_id)

        if not expense:
            # Delete file if expense not found
            os.remove(filepath)
            return jsonify({'error': 'Expense not found'}), 404

        # Check permissions
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=expense.group_id
        ).first()

        if not membership:
            os.remove(filepath)
            return jsonify({'error': 'Access denied'}), 403

        # Update expense with receipt URL
        expense.receipt_url = unique_filename
        db.session.commit()

    return jsonify({
        'message': 'Receipt uploaded successfully',
        'filename': unique_filename,
        'url': f'/api/receipts/{unique_filename}'
    }), 201


@bp.route('/<filename>', methods=['GET'])
@jwt_required()
def get_receipt(filename):
    """
    Get receipt file

    Args:
        filename: Receipt filename
    """
    user_id = int(get_jwt_identity())  # Convert string to int

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')

    # Security: Check if user has access to this receipt
    # Extract user_id from filename (format: userid_timestamp_filename)
    try:
        file_user_id = int(filename.split('_')[0])
    except:
        return jsonify({'error': 'Invalid filename'}), 400

    # Check if user uploaded this file or is admin
    from app.models.user import User
    current_user = User.query.get(user_id)

    if file_user_id != user_id and not current_user.is_superadmin:
        # Check if user is in same group as expense
        expense = Expense.query.filter_by(receipt_url=filename).first()

        if expense:
            membership = GroupMember.query.filter_by(
                user_id=user_id,
                group_id=expense.group_id
            ).first()

            if not membership:
                return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Access denied'}), 403

    return send_from_directory(upload_folder, filename)


@bp.route('/<filename>', methods=['DELETE'])
@jwt_required()
def delete_receipt(filename):
    """
    Delete receipt file

    Args:
        filename: Receipt filename
    """
    user_id = int(get_jwt_identity())  # Convert string to int

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    filepath = os.path.join(upload_folder, filename)

    # Check if file exists
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    # Security: Check if user owns this receipt
    try:
        file_user_id = int(filename.split('_')[0])
    except:
        return jsonify({'error': 'Invalid filename'}), 400

    from app.models.user import User
    current_user = User.query.get(user_id)

    if file_user_id != user_id and not current_user.is_superadmin:
        return jsonify({'error': 'Access denied'}), 403

    # Remove from expense if attached
    expense = Expense.query.filter_by(receipt_url=filename).first()
    if expense:
        expense.receipt_url = None
        db.session.commit()

    # Delete file
    try:
        os.remove(filepath)
        return jsonify({'message': 'Receipt deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500


from datetime import datetime
