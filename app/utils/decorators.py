from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User
from app.models.group import GroupMember


def admin_required(fn):
    """
    Decorator to require superadmin privileges.
    Use this for system-wide admin operations.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or not user.is_superadmin:
            return jsonify({'error': 'Admin privileges required'}), 403

        return fn(*args, **kwargs)

    return wrapper


def group_admin_required(fn):
    """
    Decorator to require group admin privileges.
    Expects 'group_id' in the route parameters or request.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()

        # Get group_id from kwargs (route parameter)
        group_id = kwargs.get('group_id')

        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400

        # Check if user is admin of this group
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if not membership or membership.role != 'admin':
            return jsonify({'error': 'Group admin privileges required'}), 403

        return fn(*args, **kwargs)

    return wrapper


def group_member_required(fn):
    """
    Decorator to require group membership (admin or client).
    Expects 'group_id' in the route parameters or request.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()

        # Get group_id from kwargs (route parameter)
        group_id = kwargs.get('group_id')

        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400

        # Check if user is member of this group
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if not membership:
            return jsonify({'error': 'Group membership required'}), 403

        return fn(*args, **kwargs)

    return wrapper
