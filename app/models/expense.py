from datetime import datetime
from app import db


class Expense(db.Model):
    """Expense model for tracking group expenses"""
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default='VND')
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    paid_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    split_type = db.Column(db.String(20), default='equal')
    status = db.Column(db.String(20), default='pending')
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    receipt_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group = db.relationship('Group', back_populates='expenses')
    category = db.relationship('Category', back_populates='expenses')
    creator = db.relationship('User', foreign_keys=[created_by_id], back_populates='expenses_created')
    paid_by = db.relationship('User', foreign_keys=[paid_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    splits = db.relationship('ExpenseSplit', back_populates='expense', cascade='all, delete-orphan')

    def to_dict(self, include_splits=False):
        """Convert expense to dictionary"""
        data = {
            'id': self.id,
            'group_id': self.group_id,
            'category_id': self.category_id,
            'created_by_id': self.created_by_id,
            'description': self.description,
            'amount': float(self.amount),
            'currency': self.currency,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'paid_by_id': self.paid_by_id,
            'split_type': self.split_type,
            'status': self.status,
            'receipt_url': self.receipt_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'category': self.category.to_dict() if self.category else None,
            'creator': self.creator.to_dict() if self.creator else None,
            'paid_by': self.paid_by.to_dict() if self.paid_by else None
        }

        if include_splits:
            data['splits'] = [s.to_dict() for s in self.splits]

        return data

    def __repr__(self):
        return f'<Expense {self.description} - {self.amount}>'


class ExpenseSplit(db.Model):
    """Model for tracking how an expense is split among users"""
    __tablename__ = 'expense_splits'

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    percentage = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expense = db.relationship('Expense', back_populates='splits')
    user = db.relationship('User', back_populates='expense_splits')

    __table_args__ = (
        db.UniqueConstraint('expense_id', 'user_id', name='unique_expense_user_split'),
    )

    def to_dict(self):
        """Convert split to dictionary"""
        return {
            'id': self.id,
            'expense_id': self.expense_id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'percentage': float(self.percentage) if self.percentage else None,
            'user': self.user.to_dict() if self.user else None
        }

    def __repr__(self):
        return f'<ExpenseSplit expense={self.expense_id} user={self.user_id} amount={self.amount}>'
