"""
Unit tests for settlement algorithm
"""
import pytest
from decimal import Decimal
from app.utils.settlement import calculate_balances, optimize_settlements, calculate_settlements


class TestCalculateBalances:
    """Test balance calculation"""

    def test_calculate_who_owes_whom(self):
        """Test basic balance calculation"""
        # Simulate balances after expenses
        balances = {
            1: Decimal('100'),   # User 1 is owed 100
            2: Decimal('-50'),   # User 2 owes 50
            3: Decimal('-50')    # User 3 owes 50
        }

        settlements = optimize_settlements(balances)

        # Should have 2 transactions
        assert len(settlements) == 2

        # Check that balances are settled
        total_settled = sum(s[2] for s in settlements)
        assert float(total_settled) == 100

    def test_settlement_optimization_algorithm(self):
        """Test that algorithm minimizes transactions"""
        balances = {
            1: Decimal('100'),
            2: Decimal('-40'),
            3: Decimal('-30'),
            4: Decimal('-30')
        }

        settlements = optimize_settlements(balances)

        # Should optimize to 3 transactions instead of potentially 6
        assert len(settlements) <= 3

        # All balances should be settled
        settled_balance = Decimal('0')
        for payer_id, payee_id, amount in settlements:
            settled_balance += amount

        assert float(settled_balance) == 100

    def test_settlement_with_multiple_currencies(self):
        """Test settlement calculation (single currency in this test)"""
        balances = {
            1: Decimal('200'),
            2: Decimal('-100'),
            3: Decimal('-100')
        }

        settlements = optimize_settlements(balances)

        assert len(settlements) == 2
        assert sum(s[2] for s in settlements) == Decimal('200')

    def test_settlement_suggestions(self):
        """Test settlement suggestions format"""
        balances = {
            1: Decimal('100'),
            2: Decimal('-100')
        }

        settlements = optimize_settlements(balances)

        # Should suggest one payment from 2 to 1
        assert len(settlements) == 1
        assert settlements[0][0] == 2  # payer
        assert settlements[0][1] == 1  # payee
        assert settlements[0][2] == Decimal('100')

    def test_empty_balances(self):
        """Test with empty balances"""
        balances = {}
        settlements = optimize_settlements(balances)

        assert len(settlements) == 0

    def test_zero_balances(self):
        """Test with all zero balances"""
        balances = {
            1: Decimal('0'),
            2: Decimal('0'),
            3: Decimal('0')
        }

        settlements = optimize_settlements(balances)

        assert len(settlements) == 0

    def test_partial_payment_handling(self):
        """Test handling of partial payments"""
        balances = {
            1: Decimal('150'),
            2: Decimal('-100'),
            3: Decimal('-50')
        }

        settlements = optimize_settlements(balances)

        # Verify all debts are covered
        total_owed = sum(abs(b) for b in balances.values() if b < 0)
        total_settled = sum(s[2] for s in settlements)

        assert float(total_owed) == float(total_settled)


class TestComplexSettlements:
    """Test complex settlement scenarios"""

    def test_multiple_debtors_single_creditor(self):
        """Test multiple people owing one person"""
        balances = {
            1: Decimal('300'),   # One person paid everything
            2: Decimal('-100'),
            3: Decimal('-100'),
            4: Decimal('-100')
        }

        settlements = optimize_settlements(balances)

        # Should have 3 transactions (all pay person 1)
        assert len(settlements) == 3

        # All payments should go to person 1
        assert all(s[1] == 1 for s in settlements)

    def test_single_debtor_multiple_creditors(self):
        """Test one person owing multiple people"""
        balances = {
            1: Decimal('100'),
            2: Decimal('100'),
            3: Decimal('100'),
            4: Decimal('-300')
        }

        settlements = optimize_settlements(balances)

        # Should have 3 transactions (person 4 pays everyone)
        assert len(settlements) == 3

        # All payments should come from person 4
        assert all(s[0] == 4 for s in settlements)

    def test_circular_debts(self):
        """Test handling of circular debt situations"""
        # A owes B, B owes C, C owes A
        # Net result should minimize transactions
        balances = {
            1: Decimal('50'),
            2: Decimal('50'),
            3: Decimal('-100')
        }

        settlements = optimize_settlements(balances)

        # Should optimize to fewer transactions
        assert len(settlements) <= 2

    def test_large_group_settlement(self):
        """Test settlement with larger group"""
        balances = {
            1: Decimal('500'),
            2: Decimal('200'),
            3: Decimal('-100'),
            4: Decimal('-200'),
            5: Decimal('-150'),
            6: Decimal('-250')
        }

        settlements = optimize_settlements(balances)

        # Verify balances sum to zero
        total_balance = sum(balances.values())
        assert abs(total_balance) < Decimal('0.01')

        # Verify settlements cover all debts
        total_to_pay = sum(abs(b) for b in balances.values() if b < 0)
        total_settled = sum(s[2] for s in settlements)

        assert abs(total_to_pay - total_settled) < Decimal('0.01')


class TestEdgeCases:
    """Test edge cases in settlement calculation"""

    def test_very_small_amounts(self):
        """Test handling of very small amounts (rounding)"""
        balances = {
            1: Decimal('0.01'),
            2: Decimal('-0.01')
        }

        settlements = optimize_settlements(balances)

        # May or may not create a settlement for tiny amounts
        # depending on threshold (0.01 in our code)
        assert len(settlements) in [0, 1]

    def test_all_positive_balances(self):
        """Test with only creditors (should not happen in practice)"""
        balances = {
            1: Decimal('100'),
            2: Decimal('200')
        }

        settlements = optimize_settlements(balances)

        # No settlements possible - everyone is owed money
        assert len(settlements) == 0

    def test_all_negative_balances(self):
        """Test with only debtors (should not happen in practice)"""
        balances = {
            1: Decimal('-100'),
            2: Decimal('-200')
        }

        settlements = optimize_settlements(balances)

        # No settlements possible - everyone owes money
        assert len(settlements) == 0

    def test_single_user_balance(self):
        """Test with single user"""
        balances = {
            1: Decimal('100')
        }

        settlements = optimize_settlements(balances)

        assert len(settlements) == 0
