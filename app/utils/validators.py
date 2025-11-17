import re


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate phone number format (Vietnamese)"""
    if not phone:
        return True  # Phone is optional
    # Vietnamese phone format: 10-11 digits, starts with 0
    pattern = r'^0\d{9,10}$'
    return re.match(pattern, phone) is not None


def validate_currency(currency):
    """Validate currency code"""
    supported = ['VND', 'USD', 'EUR']
    return currency in supported


def validate_split_type(split_type):
    """Validate expense split type"""
    valid_types = ['equal', 'unequal', 'custom']
    return split_type in valid_types
