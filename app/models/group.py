from datetime import datetime
from app import db


class Group(db.Model):
    """Group model for managing expense groups"""
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    currency = db.Column(db.String(3), default='VND')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = db.relationship('GroupMember', back_populates='group', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', back_populates='group', cascade='all, delete-orphan')

    def get_admins(self):
        """Get all admin members of the group"""
        return [m.user for m in self.members if m.role == 'admin']

    def get_members(self):
        """Get all members (admin + client) of the group"""
        return [m.user for m in self.members]

    def has_member(self, user_id):
        """Check if user is a member of this group"""
        return any(m.user_id == user_id for m in self.members)

    def to_dict(self, include_members=False):
        """Convert group to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'currency': self.currency,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'member_count': len(self.members)
        }

        if include_members:
            data['members'] = [m.to_dict() for m in self.members]

        return data

    def __repr__(self):
        return f'<Group {self.name}>'


class GroupMember(db.Model):
    """Association table for users and groups with roles"""
    __tablename__ = 'group_members'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    role = db.Column(db.String(20), default='client')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='group_memberships')
    group = db.relationship('Group', back_populates='members')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'group_id', name='unique_user_group'),
    )

    def to_dict(self):
        """Convert membership to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'user': self.user.to_dict() if self.user else None
        }

    def __repr__(self):
        return f'<GroupMember user={self.user_id} group={self.group_id} role={self.role}>'
