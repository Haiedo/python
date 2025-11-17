"""
Email notification service
"""
from flask import render_template_string
from flask_mail import Message
from app import mail


def send_email(subject, recipients, body_text, body_html=None):
    """
    Send email to recipients

    Args:
        subject: Email subject
        recipients: List of email addresses
        body_text: Plain text body
        body_html: HTML body (optional)
    """
    try:
        msg = Message(
            subject=subject,
            recipients=recipients if isinstance(recipients, list) else [recipients]
        )

        msg.body = body_text

        if body_html:
            msg.html = body_html

        mail.send(msg)
        return True

    except Exception as e:
        return False


def send_expense_approval_notification(expense, recipient_email):
    """
    Notify user when their expense is approved

    Args:
        expense: Expense object
        recipient_email: User email address
    """
    subject = f"Expense Approved: {expense.description}"

    body_text = f"""
    Your expense has been approved!

    Expense: {expense.description}
    Amount: {expense.amount} {expense.currency}
    Group: {expense.group.name}

    View details at: [Your App URL]

    ---
    Expense Splitter
    """

    body_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #28a745;">Expense Approved</h2>
            <p>Your expense has been approved!</p>

            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Expense:</strong> {expense.description}</p>
                <p><strong>Amount:</strong> {expense.amount} {expense.currency}</p>
                <p><strong>Group:</strong> {expense.group.name}</p>
            </div>

            <p>
                <a href="[Your App URL]" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    View Details
                </a>
            </p>

            <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">Expense Splitter - Group Expense Management</p>
        </body>
    </html>
    """

    return send_email(subject, recipient_email, body_text, body_html)


def send_expense_rejection_notification(expense, recipient_email, reason=None):
    """
    Notify user when their expense is rejected

    Args:
        expense: Expense object
        recipient_email: User email address
        reason: Rejection reason (optional)
    """
    subject = f"Expense Rejected: {expense.description}"

    reason_text = f"\nReason: {reason}" if reason else ""

    body_text = f"""
    Your expense has been rejected.

    Expense: {expense.description}
    Amount: {expense.amount} {expense.currency}
    Group: {expense.group.name}{reason_text}

    Please review and resubmit if necessary.

    ---
    Expense Splitter
    """

    body_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #dc3545;">✗ Expense Rejected</h2>
            <p>Your expense has been rejected.</p>

            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <p><strong>Expense:</strong> {expense.description}</p>
                <p><strong>Amount:</strong> {expense.amount} {expense.currency}</p>
                <p><strong>Group:</strong> {expense.group.name}</p>
                {f'<p><strong>Reason:</strong> {reason}</p>' if reason else ''}
            </div>

            <p>Please review and resubmit if necessary.</p>

            <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">Expense Splitter - Group Expense Management</p>
        </body>
    </html>
    """

    return send_email(subject, recipient_email, body_text, body_html)


def send_payment_reminder(user, payee, amount, currency, group_name):
    """
    Send payment reminder to user

    Args:
        user: User object (debtor)
        payee: User object (creditor)
        amount: Amount owed
        currency: Currency code
        group_name: Name of group
    """
    subject = f"Payment Reminder: {group_name}"

    body_text = f"""
    Payment Reminder

    Hi {user.full_name or user.username},

    This is a reminder that you owe {payee.full_name or payee.username} {amount} {currency} in the group "{group_name}".

    Please settle this payment at your earliest convenience.

    ---
    Expense Splitter
    """

    body_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #667eea;">💰 Payment Reminder</h2>
            <p>Hi {user.full_name or user.username},</p>

            <p>This is a reminder that you owe <strong>{payee.full_name or payee.username}</strong>
               <strong>{amount} {currency}</strong> in the group "{group_name}".</p>

            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Amount:</strong> {amount} {currency}</p>
                <p><strong>Pay to:</strong> {payee.full_name or payee.username}</p>
                <p><strong>Group:</strong> {group_name}</p>
            </div>

            <p>Please settle this payment at your earliest convenience.</p>

            <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">Expense Splitter - Group Expense Management</p>
        </body>
    </html>
    """

    return send_email(subject, user.email, body_text, body_html)


def send_payment_confirmation(payer, payee, amount, currency, group_name):
    """
    Send payment confirmation to both payer and payee

    Args:
        payer: User object (who paid)
        payee: User object (who received)
        amount: Amount paid
        currency: Currency code
        group_name: Name of group
    """
    # Email to payer
    payer_subject = f"Payment Confirmed: {group_name}"
    payer_body = f"""
    Payment Confirmed

    Hi {payer.full_name or payer.username},

    Your payment of {amount} {currency} to {payee.full_name or payee.username}
    in the group "{group_name}" has been confirmed.

    ---
    Expense Splitter
    """

    # Email to payee
    payee_subject = f"Payment Received: {group_name}"
    payee_body = f"""
    Payment Received

    Hi {payee.full_name or payee.username},

    {payer.full_name or payer.username} has paid you {amount} {currency}
    in the group "{group_name}".

    ---
    Expense Splitter
    """

    send_email(payer_subject, payer.email, payer_body)
    send_email(payee_subject, payee.email, payee_body)

    return True


def send_monthly_summary(user, stats):
    """
    Send monthly expense summary to user

    Args:
        user: User object
        stats: Dictionary with monthly statistics
    """
    subject = "Your Monthly Expense Summary"

    body_text = f"""
    Monthly Expense Summary

    Hi {user.full_name or user.username},

    Here's your expense summary for this month:

    Total Spent: {stats.get('total_spent', 0)} VND
    Total Owed: {stats.get('total_owed', 0)} VND
    Number of Expenses: {stats.get('expense_count', 0)}
    Number of Groups: {stats.get('group_count', 0)}

    Keep tracking your expenses!

    ---
    Expense Splitter
    """

    body_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #667eea;">📊 Monthly Expense Summary</h2>
            <p>Hi {user.full_name or user.username},</p>

            <p>Here's your expense summary for this month:</p>

            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Total Spent:</strong> {stats.get('total_spent', 0)} VND</p>
                <p><strong>Total Owed:</strong> {stats.get('total_owed', 0)} VND</p>
                <p><strong>Number of Expenses:</strong> {stats.get('expense_count', 0)}</p>
                <p><strong>Number of Groups:</strong> {stats.get('group_count', 0)}</p>
            </div>

            <p>Keep tracking your expenses!</p>

            <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">Expense Splitter - Group Expense Management</p>
        </body>
    </html>
    """

    return send_email(subject, user.email, body_text, body_html)


def send_settlement_notification(user, settlements, group_name):
    """
    Send settlement notification with optimized payment suggestions

    Args:
        user: User object
        settlements: List of settlement dictionaries
        group_name: Name of group
    """
    subject = f"Settlement Summary: {group_name}"

    # Build settlement list text
    settlement_text = "\n".join([
        f"- Pay {s['payee_name']} {s['amount']} {s['currency']}"
        for s in settlements
    ])

    body_text = f"""
    Settlement Summary

    Hi {user.full_name or user.username},

    Here are your optimized payment suggestions for "{group_name}":

    {settlement_text}

    These payments will settle all your debts in this group.

    ---
    Expense Splitter
    """

    settlement_html = "".join([
        f"<p style='margin: 10px 0;'>→ Pay <strong>{s['payee_name']}</strong> "
        f"<strong>{s['amount']} {s['currency']}</strong></p>"
        for s in settlements
    ])

    body_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #667eea;">💸 Settlement Summary</h2>
            <p>Hi {user.full_name or user.username},</p>

            <p>Here are your optimized payment suggestions for <strong>"{group_name}"</strong>:</p>

            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                {settlement_html}
            </div>

            <p>These payments will settle all your debts in this group.</p>

            <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">Expense Splitter - Group Expense Management</p>
        </body>
    </html>
    """

    return send_email(subject, user.email, body_text, body_html)
