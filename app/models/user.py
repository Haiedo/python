from datetime import datetime
from app import db, bcrypt


class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(255))
    bank_name = db.Column(db.String(100))
    bank_account_number = db.Column(db.String(50))
    bank_account_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    is_superadmin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group_memberships = db.relationship('GroupMember', back_populates='user', cascade='all, delete-orphan')
    expenses_created = db.relationship('Expense', foreign_keys='Expense.created_by_id', back_populates='creator')
    expense_splits = db.relationship('ExpenseSplit', back_populates='user')
    payments_made = db.relationship('Payment', foreign_keys='Payment.payer_id', back_populates='payer')
    payments_received = db.relationship('Payment', foreign_keys='Payment.payee_id', back_populates='payee')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_admin_of_group(self, group_id):
        """Check if user is admin of a specific group"""
        membership = GroupMember.query.filter_by(
            user_id=self.id,
            group_id=group_id
        ).first()
        return membership and membership.role == 'admin'

    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

        if include_sensitive:
            data.update({
                'bank_name': self.bank_name,
                'bank_account_number': self.bank_account_number,
                'bank_account_name': self.bank_account_name,
                'is_superadmin': self.is_superadmin
            })

        return data

    def __repr__(self):
        return f'<User {self.username}>'
