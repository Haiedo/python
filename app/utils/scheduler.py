"""
Scheduler for recurring expenses
"""
from datetime import datetime
from app import db
from app.models.recurring_expense import RecurringExpense
from app.models.expense import Expense, ExpenseSplit
from app.models.group import GroupMember


def execute_recurring_expenses():
    """
    Execute all recurring expenses that are due
    Should be called periodically (e.g., via cron job)
    """
    # Get all active recurring expenses that should be executed
    recurring_expenses = RecurringExpense.query.filter_by(
        is_active=True,
        is_paused=False
    ).all()

    executed_count = 0
    errors = []

    for recurring in recurring_expenses:
        try:
            if recurring.should_execute():
                # Create the expense
                expense = Expense(
                    group_id=recurring.group_id,
                    category_id=recurring.category_id,
                    created_by_id=recurring.created_by_id,
                    description=f"{recurring.description} (Auto-generated)",
                    amount=recurring.amount,
                    currency=recurring.currency,
                    paid_by_id=recurring.paid_by_id,
                    split_type=recurring.split_type,
                    status='approved',  # Auto-approve recurring expenses
                    approved_by_id=recurring.created_by_id,
                    approved_at=datetime.utcnow()
                )

                db.session.add(expense)
                db.session.flush()

                # Create splits (equal split for simplicity)
                if recurring.split_type == 'equal':
                    members = GroupMember.query.filter_by(
                        group_id=recurring.group_id
                    ).all()

                    if members:
                        split_amount = recurring.amount / len(members)

                        for member in members:
                            split = ExpenseSplit(
                                expense_id=expense.id,
                                user_id=member.user_id,
                                amount=split_amount,
                                percentage=100 / len(members)
                            )
                            db.session.add(split)

                # Update recurring expense
                recurring.last_executed = datetime.utcnow()
                recurring.next_occurrence = recurring.calculate_next_occurrence()

                # Deactivate if end date passed
                if recurring.end_date and recurring.next_occurrence > recurring.end_date:
                    recurring.is_active = False

                db.session.commit()
                executed_count += 1

        except Exception as e:
            db.session.rollback()
            errors.append({
                'recurring_id': recurring.id,
                'error': str(e)
            })

    return {
        'executed': executed_count,
        'errors': errors
    }


def run_scheduler():
    """
    Main scheduler function
    Call this from a cron job or background task
    """
    result = execute_recurring_expenses()
    return result


# CLI command for testing
if __name__ == '__main__':
    from app import create_app

    app = create_app('development')
    with app.app_context():
        run_scheduler()
