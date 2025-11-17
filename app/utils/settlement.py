from decimal import Decimal
from collections import defaultdict
from app.models.expense import Expense, ExpenseSplit
from app.models.payment import Payment


def calculate_balances(group_id):
    """
    Calculate net balances for all members in a group.
    Returns dict: {user_id: net_balance}
    Positive balance = person is owed money
    Negative balance = person owes money
    """
    balances = defaultdict(Decimal)

    # Get all approved expenses for the group
    expenses = Expense.query.filter_by(
        group_id=group_id,
        status='approved'
    ).all()

    for expense in expenses:
        # Person who paid gets positive balance
        balances[expense.paid_by_id] += Decimal(str(expense.amount))

        # People who owe get negative balance
        for split in expense.splits:
            balances[split.user_id] -= Decimal(str(split.amount))

    # Subtract completed payments
    payments = Payment.query.filter_by(
        group_id=group_id,
        status='completed'
    ).all()

    for payment in payments:
        # Payer's balance increases (they paid off debt)
        balances[payment.payer_id] += Decimal(str(payment.amount))
        # Payee's balance decreases (they received payment)
        balances[payment.payee_id] -= Decimal(str(payment.amount))

    # Remove zero balances
    return {user_id: balance for user_id, balance in balances.items() if abs(balance) > 0.01}


def optimize_settlements(balances):
    """
    Optimize settlements to minimize number of transactions.
    Uses greedy algorithm to match largest debtor with largest creditor.

    Args:
        balances: dict of {user_id: net_balance}

    Returns:
        list of tuples: [(payer_id, payee_id, amount), ...]
    """
    settlements = []

    # Separate debtors (negative balance) and creditors (positive balance)
    debtors = []  # (user_id, amount_owed)
    creditors = []  # (user_id, amount_to_receive)

    for user_id, balance in balances.items():
        if balance < 0:
            debtors.append((user_id, abs(balance)))
        elif balance > 0:
            creditors.append((user_id, balance))

    # Sort by amount (largest first) for greedy matching
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    # Match debtors with creditors
    i, j = 0, 0

    while i < len(debtors) and j < len(creditors):
        debtor_id, debt_amount = debtors[i]
        creditor_id, credit_amount = creditors[j]

        # Settle the minimum of debt and credit
        settlement_amount = min(debt_amount, credit_amount)

        settlements.append((debtor_id, creditor_id, settlement_amount))

        # Update remaining amounts
        debtors[i] = (debtor_id, debt_amount - settlement_amount)
        creditors[j] = (creditor_id, credit_amount - settlement_amount)

        # Move to next debtor/creditor if settled
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1

    return settlements


def calculate_settlements(group_id):
    """
    Calculate optimized settlements for a group.

    Returns:
        dict with:
            - balances: {user_id: net_balance}
            - settlements: [(payer_id, payee_id, amount), ...]
    """
    balances = calculate_balances(group_id)
    settlements = optimize_settlements(balances)

    return {
        'balances': {str(k): float(v) for k, v in balances.items()},
        'settlements': [
            {
                'payer_id': payer_id,
                'payee_id': payee_id,
                'amount': float(amount)
            }
            for payer_id, payee_id, amount in settlements
        ]
    }


def get_user_debts(user_id, group_id):
    """
    Get specific user's debts and credits in a group.

    Returns:
        dict with:
            - owes: list of {user_id: amount} - people this user owes
            - owed: list of {user_id: amount} - people who owe this user
            - net_balance: total net balance
    """
    settlements_data = calculate_settlements(group_id)
    settlements = settlements_data['settlements']
    balances = settlements_data['balances']

    user_id_str = str(user_id)
    net_balance = balances.get(user_id_str, 0)

    owes = []  # This user owes others
    owed = []  # Others owe this user

    for settlement in settlements:
        if settlement['payer_id'] == user_id:
            owes.append({
                'user_id': settlement['payee_id'],
                'amount': settlement['amount']
            })
        elif settlement['payee_id'] == user_id:
            owed.append({
                'user_id': settlement['payer_id'],
                'amount': settlement['amount']
            })

    return {
        'net_balance': net_balance,
        'owes': owes,
        'owed': owed
    }
