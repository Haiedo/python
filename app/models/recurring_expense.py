from datetime import datetime, timedelta
from app import db


class RecurringExpense(db.Model):
    """Model for recurring expense templates"""
    __tablename__ = 'recurring_expenses'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default='VND')
    paid_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    split_type = db.Column(db.String(20), default='equal')
    frequency = db.Column(db.String(20), nullable=False)
    interval = db.Column(db.Integer, default=1)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    next_occurrence = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_paused = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_executed = db.Column(db.DateTime)

    group = db.relationship('Group')
    category = db.relationship('Category')
    creator = db.relationship('User', foreign_keys=[created_by_id])
    paid_by = db.relationship('User', foreign_keys=[paid_by_id])

    def calculate_next_occurrence(self):
        """Calculate next occurrence date based on frequency"""
        current = self.next_occurrence or self.start_date

        if self.frequency == 'daily':
            next_date = current + timedelta(days=self.interval)
        elif self.frequency == 'weekly':
            next_date = current + timedelta(weeks=self.interval)
        elif self.frequency == 'monthly':
            next_date = current + timedelta(days=30 * self.interval)
        elif self.frequency == 'yearly':
            next_date = current + timedelta(days=365 * self.interval)
        else:
            return None

        return next_date

    def should_execute(self):
        """Check if recurring expense should be executed now"""
        if not self.is_active or self.is_paused:
            return False

        if self.next_occurrence > datetime.utcnow():
            return False

        if self.end_date and datetime.utcnow() > self.end_date:
            return False

        return True

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'category_id': self.category_id,
            'created_by_id': self.created_by_id,
            'description': self.description,
            'amount': float(self.amount),
            'currency': self.currency,
            'paid_by_id': self.paid_by_id,
            'split_type': self.split_type,
            'frequency': self.frequency,
            'interval': self.interval,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'next_occurrence': self.next_occurrence.isoformat() if self.next_occurrence else None,
            'is_active': self.is_active,
            'is_paused': self.is_paused,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_executed': self.last_executed.isoformat() if self.last_executed else None,
            'category': self.category.to_dict() if self.category else None
        }

    def __repr__(self):
        return f'<RecurringExpense {self.description} - {self.frequency}>'
