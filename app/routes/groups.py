from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.group import Group, GroupMember
from app.utils.decorators import group_admin_required, group_member_required

bp = Blueprint('groups', __name__, url_prefix='/api/groups')


@bp.route('/search-users', methods=['GET'])
@jwt_required()
def search_users():
    """Search users by username or email"""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400

    # Search by username or email
    users = User.query.filter(
        (User.username.ilike(f'%{query}%')) |
        (User.email.ilike(f'%{query}%'))
    ).limit(10).all()

    return jsonify({
        'users': [u.to_dict() for u in users]
    }), 200


@bp.route('', methods=['POST'])
@jwt_required()
def create_group():
    """Create a new group (creator becomes admin)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': 'Group name is required'}), 400

    # Create group
    group = Group(
        name=data['name'],
        description=data.get('description'),
        currency=data.get('currency', 'VND')
    )

    try:
        db.session.add(group)
        db.session.flush()  # Get group.id

        # Add creator as admin
        membership = GroupMember(
            user_id=user_id,
            group_id=group.id,
            role='admin'
        )
        db.session.add(membership)
        db.session.commit()

        return jsonify({
            'message': 'Group created successfully',
            'group': group.to_dict(include_members=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create group: {str(e)}'}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_user_groups():
    """Get all groups the current user is a member of"""
    user_id = int(get_jwt_identity())  # Convert string to int

    # Get all group memberships
    memberships = GroupMember.query.filter_by(user_id=user_id).all()
    groups = [m.group.to_dict(include_members=True) for m in memberships if m.group.is_active]

    # Add role information
    for i, membership in enumerate(memberships):
        if membership.group.is_active:
            groups[i]['user_role'] = membership.role

    return jsonify({'groups': groups}), 200


@bp.route('/<int:group_id>', methods=['GET'])
@jwt_required()
@group_member_required
def get_group(group_id):
    """Get group details (members only)"""
    group = Group.query.get(group_id)

    if not group:
        return jsonify({'error': 'Group not found'}), 404

    if not group.is_active:
        return jsonify({'error': 'Group is inactive'}), 403

    # Get user's role in this group
    user_id = int(get_jwt_identity())  # Convert string to int
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=group_id
    ).first()

    group_data = group.to_dict(include_members=True)
    group_data['user_role'] = membership.role if membership else None

    return jsonify({'group': group_data}), 200


@bp.route('/<int:group_id>', methods=['PUT'])
@jwt_required()
@group_admin_required
def update_group(group_id):
    """Update group details (admin only)"""
    group = Group.query.get(group_id)

    if not group:
        return jsonify({'error': 'Group not found'}), 404

    data = request.get_json()

    # Update allowed fields
    if 'name' in data:
        group.name = data['name']

    if 'description' in data:
        group.description = data['description']

    if 'currency' in data:
        group.currency = data['currency']

    try:
        db.session.commit()
        return jsonify({
            'message': 'Group updated successfully',
            'group': group.to_dict(include_members=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@bp.route('/<int:group_id>', methods=['DELETE'])
@jwt_required()
@group_admin_required
def delete_group(group_id):
    """Delete/deactivate group (admin only)"""
    group = Group.query.get(group_id)

    if not group:
        return jsonify({'error': 'Group not found'}), 404

    # Soft delete - just mark as inactive
    group.is_active = False

    try:
        db.session.commit()
        return jsonify({'message': 'Group deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500


@bp.route('/<int:group_id>/members', methods=['POST'])
@jwt_required()
@group_admin_required
def add_member(group_id):
    """Add a member to the group (admin only)"""
    group = Group.query.get(group_id)

    if not group or not group.is_active:
        return jsonify({'error': 'Group not found'}), 404

    data = request.get_json()

    if not data or not data.get('user_id'):
        return jsonify({'error': 'User ID is required'}), 400

    # Check if user exists
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Check if already a member
    existing = GroupMember.query.filter_by(
        user_id=data['user_id'],
        group_id=group_id
    ).first()

    if existing:
        return jsonify({'error': 'User is already a member'}), 409

    # Add member
    role = data.get('role', 'member')
    # Accept both 'member' and 'client' for backward compatibility
    if role == 'client':
        role = 'member'
    if role not in ['admin', 'member']:
        return jsonify({'error': 'Invalid role'}), 400

    membership = GroupMember(
        user_id=data['user_id'],
        group_id=group_id,
        role=role
    )

    try:
        db.session.add(membership)
        db.session.commit()

        return jsonify({
            'message': 'Member added successfully',
            'membership': membership.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to add member: {str(e)}'}), 500


@bp.route('/<int:group_id>/members/<int:user_id>', methods=['DELETE'])
@jwt_required()
@group_admin_required
def remove_member(group_id, user_id):
    """Remove a member from the group (admin only)"""
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Membership not found'}), 404

    # Check if this is the last admin
    admin_count = GroupMember.query.filter_by(
        group_id=group_id,
        role='admin'
    ).count()

    if membership.role == 'admin' and admin_count <= 1:
        return jsonify({'error': 'Cannot remove the last admin'}), 400

    try:
        db.session.delete(membership)
        db.session.commit()
        return jsonify({'message': 'Member removed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to remove member: {str(e)}'}), 500


@bp.route('/<int:group_id>/members/<int:user_id>/role', methods=['PUT'])
@jwt_required()
@group_admin_required
def update_member_role(group_id, user_id):
    """Update member role (admin only)"""
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Membership not found'}), 404

    data = request.get_json()
    new_role = data.get('role')

    # Accept both 'member' and 'client' for backward compatibility
    if new_role == 'client':
        new_role = 'member'
    if new_role not in ['admin', 'member']:
        return jsonify({'error': 'Invalid role'}), 400

    # Check if demoting the last admin
    if membership.role == 'admin' and new_role == 'member':
        admin_count = GroupMember.query.filter_by(
            group_id=group_id,
            role='admin'
        ).count()

        if admin_count <= 1:
            return jsonify({'error': 'Cannot demote the last admin'}), 400

    membership.role = new_role

    try:
        db.session.commit()
        return jsonify({
            'message': 'Role updated successfully',
            'membership': membership.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update role: {str(e)}'}), 500


@bp.route('/<int:group_id>/leave', methods=['POST'])
@jwt_required()
@group_member_required
def leave_group(group_id):
    """Leave a group (any member can leave)"""
    user_id = int(get_jwt_identity())  # Convert string to int

    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=group_id
    ).first()

    if not membership:
        return jsonify({'error': 'You are not a member of this group'}), 404

    # Check if this is the last admin
    if membership.role == 'admin':
        admin_count = GroupMember.query.filter_by(
            group_id=group_id,
            role='admin'
        ).count()

        if admin_count <= 1:
            return jsonify({'error': 'Cannot leave as the last admin. Transfer admin rights first.'}), 400

    try:
        db.session.delete(membership)
        db.session.commit()
        return jsonify({'message': 'Left group successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to leave group: {str(e)}'}), 500
