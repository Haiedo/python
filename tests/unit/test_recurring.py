"""
Unit tests for recurring expense management
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.recurring_expense import RecurringExpense
from app.models.group import GroupMember
from app import db


class TestCreateRecurringExpense:
    """Test recurring expense creation"""

    def test_create_recurring_expense(self, client, admin_token, test_group, admin_user, init_database):
        """Test creating a recurring expense template"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        start_date = (datetime.utcnow() + timedelta(days=1)).isoformat()

        response = client.post('/api/recurring',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Monthly rent',
                'amount': 5000000,
                'paid_by_id': admin_user.id,
                'frequency': 'monthly',
                'interval': 1,
                'start_date': start_date,
                'split_type': 'equal'
            }
        )

        assert response.status_code == 201
        assert 'recurring_expense' in response.json
        assert response.json['recurring_expense']['frequency'] == 'monthly'
        assert response.json['recurring_expense']['is_active'] == True

    def test_create_recurring_expense_with_end_date(self, client, admin_token, test_group, admin_user, init_database):
        """Test creating recurring expense with end date"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        start_date = datetime.utcnow() + timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=365)

        response = client.post('/api/recurring',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Gym membership',
                'amount': 500000,
                'paid_by_id': admin_user.id,
                'frequency': 'monthly',
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        )

        assert response.status_code == 201
        assert response.json['recurring_expense']['end_date'] is not None

    def test_client_cannot_create_recurring_expense(self, client, test_group, client_user, init_database):
        """Test that client cannot create recurring expenses"""
        # Add client to group
        membership = GroupMember(
            user_id=client_user.id,
            group_id=test_group.id,
            role='client'
        )
        db.session.add(membership)
        db.session.commit()

        # Login as client
        response = client.post('/api/auth/login', json={
            'username': 'client_test',
            'password': 'client123'
        })
        client_token = response.json['access_token']

        headers = {
            'Authorization': f'Bearer {client_token}',
            'Content-Type': 'application/json'
        }

        start_date = datetime.utcnow().isoformat()

        response = client.post('/api/recurring',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Unauthorized recurring',
                'amount': 1000,
                'paid_by_id': client_user.id,
                'frequency': 'weekly',
                'start_date': start_date
            }
        )

        assert response.status_code == 403

    def test_create_recurring_expense_missing_fields(self, client, admin_token, test_group, init_database):
        """Test creating recurring expense with missing fields"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.post('/api/recurring',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Incomplete recurring'
                # Missing amount, frequency, start_date
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json

    def test_create_recurring_expense_invalid_frequency(self, client, admin_token, test_group, admin_user, init_database):
        """Test creating recurring expense with invalid frequency"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        start_date = datetime.utcnow().isoformat()

        response = client.post('/api/recurring',
            headers=headers,
            json={
                'group_id': test_group.id,
                'description': 'Invalid frequency',
                'amount': 1000,
                'paid_by_id': admin_user.id,
                'frequency': 'invalid_freq',
                'start_date': start_date
            }
        )

        assert response.status_code == 400

    def test_create_recurring_expense_different_frequencies(self, client, admin_token, test_group, admin_user, init_database):
        """Test creating recurring expenses with all valid frequencies"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        frequencies = ['daily', 'weekly', 'monthly', 'yearly']

        for freq in frequencies:
            start_date = datetime.utcnow().isoformat()

            response = client.post('/api/recurring',
                headers=headers,
                json={
                    'group_id': test_group.id,
                    'description': f'{freq.capitalize()} expense',
                    'amount': 1000,
                    'paid_by_id': admin_user.id,
                    'frequency': freq,
                    'start_date': start_date
                }
            )

            assert response.status_code == 201
            assert response.json['recurring_expense']['frequency'] == freq


class TestEditRecurringExpense:
    """Test recurring expense editing"""

    def test_edit_recurring_template(self, client, admin_token, test_group, admin_user, init_database):
        """Test editing recurring expense template"""
        # Create recurring expense first
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Original description',
            amount=Decimal('1000'),
            paid_by_id=admin_user.id,
            frequency='monthly',
            start_date=datetime.utcnow(),
            next_occurrence=datetime.utcnow()
        )
        db.session.add(recurring)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Edit recurring expense
        response = client.put(f'/api/recurring/{recurring.id}',
            headers=headers,
            json={
                'description': 'Updated description',
                'amount': 1500
            }
        )

        assert response.status_code == 200
        assert response.json['recurring_expense']['description'] == 'Updated description'
        assert response.json['recurring_expense']['amount'] == 1500

    def test_edit_recurring_change_frequency(self, client, admin_token, test_group, admin_user, init_database):
        """Test changing frequency of recurring expense"""
        # Create recurring expense
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Frequency change test',
            amount=Decimal('2000'),
            paid_by_id=admin_user.id,
            frequency='monthly',
            start_date=datetime.utcnow(),
            next_occurrence=datetime.utcnow()
        )
        db.session.add(recurring)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Change frequency to weekly
        response = client.put(f'/api/recurring/{recurring.id}',
            headers=headers,
            json={
                'frequency': 'weekly',
                'interval': 2
            }
        )

        assert response.status_code == 200
        assert response.json['recurring_expense']['frequency'] == 'weekly'
        assert response.json['recurring_expense']['interval'] == 2


class TestDeleteRecurringExpense:
    """Test recurring expense deletion"""

    def test_delete_recurring_template(self, client, admin_token, test_group, admin_user, init_database):
        """Test deleting recurring expense template"""
        # Create recurring expense
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='To be deleted',
            amount=Decimal('500'),
            paid_by_id=admin_user.id,
            frequency='daily',
            start_date=datetime.utcnow(),
            next_occurrence=datetime.utcnow()
        )
        db.session.add(recurring)
        db.session.commit()
        recurring_id = recurring.id

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Delete recurring expense
        response = client.delete(f'/api/recurring/{recurring_id}', headers=headers)

        assert response.status_code == 200

        # Verify deletion
        deleted = RecurringExpense.query.get(recurring_id)
        assert deleted is None or not deleted.is_active


class TestPauseResumeRecurring:
    """Test pause/resume functionality"""

    def test_pause_recurring_expense(self, client, admin_token, test_group, admin_user, init_database):
        """Test pausing a recurring expense"""
        # Create recurring expense
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='To be paused',
            amount=Decimal('3000'),
            paid_by_id=admin_user.id,
            frequency='monthly',
            start_date=datetime.utcnow(),
            next_occurrence=datetime.utcnow(),
            is_paused=False
        )
        db.session.add(recurring)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        # Pause recurring expense
        response = client.post(f'/api/recurring/{recurring.id}/pause',
            headers=headers
        )

        assert response.status_code == 200
        assert response.json['recurring_expense']['is_paused'] == True



class TestRecurringExpenseGeneration:
    """Test automatic expense generation from recurring templates"""

    def test_recurring_expense_generation(self, init_database, test_group, admin_user):
        """Test that recurring expenses are generated correctly"""
        # Create recurring expense that should execute
        past_date = datetime.utcnow() - timedelta(days=1)
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Auto-generated expense',
            amount=Decimal('1000'),
            paid_by_id=admin_user.id,
            frequency='daily',
            start_date=past_date,
            next_occurrence=past_date,
            is_active=True,
            is_paused=False
        )
        db.session.add(recurring)
        db.session.commit()

        # Check if should execute
        assert recurring.should_execute() == True

    def test_recurring_expense_should_not_execute_if_paused(self, init_database, test_group, admin_user):
        """Test that paused recurring expenses don't execute"""
        past_date = datetime.utcnow() - timedelta(days=1)
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Paused recurring',
            amount=Decimal('1000'),
            paid_by_id=admin_user.id,
            frequency='daily',
            start_date=past_date,
            next_occurrence=past_date,
            is_active=True,
            is_paused=True
        )
        db.session.add(recurring)
        db.session.commit()

        # Should not execute because it's paused
        assert recurring.should_execute() == False

    def test_recurring_expense_should_not_execute_if_inactive(self, init_database, test_group, admin_user):
        """Test that inactive recurring expenses don't execute"""
        past_date = datetime.utcnow() - timedelta(days=1)
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Inactive recurring',
            amount=Decimal('1000'),
            paid_by_id=admin_user.id,
            frequency='daily',
            start_date=past_date,
            next_occurrence=past_date,
            is_active=False,
            is_paused=False
        )
        db.session.add(recurring)
        db.session.commit()

        assert recurring.should_execute() == False

    def test_recurring_expense_past_end_date(self, init_database, test_group, admin_user):
        """Test that recurring expenses past end date don't execute"""
        past_date = datetime.utcnow() - timedelta(days=10)
        end_date = datetime.utcnow() - timedelta(days=5)

        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Ended recurring',
            amount=Decimal('1000'),
            paid_by_id=admin_user.id,
            frequency='daily',
            start_date=past_date,
            next_occurrence=past_date,
            end_date=end_date,
            is_active=True,
            is_paused=False
        )
        db.session.add(recurring)
        db.session.commit()

        # Should not execute because past end date
        assert recurring.should_execute() == False


class TestCalculateNextOccurrence:
    """Test next occurrence calculation"""

    def test_calculate_next_occurrence_daily(self, init_database, test_group, admin_user):
        """Test next occurrence calculation for daily frequency"""
        start_date = datetime.utcnow()
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Daily test',
            amount=Decimal('100'),
            paid_by_id=admin_user.id,
            frequency='daily',
            interval=1,
            start_date=start_date,
            next_occurrence=start_date
        )

        next_date = recurring.calculate_next_occurrence()
        expected = start_date + timedelta(days=1)

        assert next_date.date() == expected.date()

    def test_calculate_next_occurrence_weekly(self, init_database, test_group, admin_user):
        """Test next occurrence calculation for weekly frequency"""
        start_date = datetime.utcnow()
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Weekly test',
            amount=Decimal('200'),
            paid_by_id=admin_user.id,
            frequency='weekly',
            interval=2,
            start_date=start_date,
            next_occurrence=start_date
        )

        next_date = recurring.calculate_next_occurrence()
        expected = start_date + timedelta(weeks=2)

        assert next_date.date() == expected.date()

    def test_calculate_next_occurrence_monthly(self, init_database, test_group, admin_user):
        """Test next occurrence calculation for monthly frequency"""
        start_date = datetime.utcnow()
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Monthly test',
            amount=Decimal('5000'),
            paid_by_id=admin_user.id,
            frequency='monthly',
            interval=1,
            start_date=start_date,
            next_occurrence=start_date
        )

        next_date = recurring.calculate_next_occurrence()

        # Should be approximately 30 days later
        assert (next_date - start_date).days == 30

    def test_calculate_next_occurrence_yearly(self, init_database, test_group, admin_user):
        """Test next occurrence calculation for yearly frequency"""
        start_date = datetime.utcnow()
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Yearly test',
            amount=Decimal('10000'),
            paid_by_id=admin_user.id,
            frequency='yearly',
            interval=1,
            start_date=start_date,
            next_occurrence=start_date
        )

        next_date = recurring.calculate_next_occurrence()

        # Should be approximately 365 days later
        assert (next_date - start_date).days == 365


class TestRecurringExpenseQueries:
    """Test recurring expense listing and filtering"""

    def test_get_group_recurring_expenses(self, client, admin_token, test_group, admin_user, init_database):
        """Test getting all recurring expenses for a group"""
        # Create multiple recurring expenses
        for i in range(3):
            recurring = RecurringExpense(
                group_id=test_group.id,
                created_by_id=admin_user.id,
                description=f'Recurring {i}',
                amount=Decimal(1000 + i * 100),
                paid_by_id=admin_user.id,
                frequency='monthly',
                start_date=datetime.utcnow(),
                next_occurrence=datetime.utcnow()
            )
            db.session.add(recurring)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.get(f'/api/recurring?group_id={test_group.id}', headers=headers)

        assert response.status_code == 200
        assert 'recurring_expenses' in response.json
        assert len(response.json['recurring_expenses']) >= 3

    def test_get_recurring_expense_details(self, client, admin_token, test_group, admin_user, init_database):
        """Test getting single recurring expense details"""
        recurring = RecurringExpense(
            group_id=test_group.id,
            created_by_id=admin_user.id,
            description='Details test',
            amount=Decimal('7500'),
            paid_by_id=admin_user.id,
            frequency='monthly',
            interval=2,
            start_date=datetime.utcnow(),
            next_occurrence=datetime.utcnow()
        )
        db.session.add(recurring)
        db.session.commit()

        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.get(f'/api/recurring/{recurring.id}', headers=headers)

        assert response.status_code == 200
        assert 'recurring_expense' in response.json
        assert response.json['recurring_expense']['interval'] == 2
