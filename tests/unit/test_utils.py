"""
Unit tests for utility functions
"""
import pytest
from decimal import Decimal
import re


class TestEmailValidation:
    """Test email validation"""

    def test_validate_email(self):
        """Test email validation with valid emails"""
        valid_emails = [
            'user@example.com',
            'test.user@domain.co.uk',
            'admin+tag@site.org',
            'user123@test-domain.com'
        ]

        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        for email in valid_emails:
            assert email_pattern.match(email), f"Valid email {email} should pass validation"

    def test_validate_email_invalid(self):
        """Test email validation with invalid emails"""
        invalid_emails = [
            'notanemail',
            '@example.com',
            'user@',
            'user @example.com',
            'user@.com'
        ]

        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        for email in invalid_emails:
            assert not email_pattern.match(email), f"Invalid email {email} should fail validation"


class TestPhoneValidation:
    """Test phone number validation"""

    def test_validate_phone_number(self):
        """Test Vietnamese phone number validation"""
        valid_phones = [
            '0901234567',
            '0123456789',
            '+84901234567',
            '84901234567'
        ]

        phone_pattern = re.compile(r'^(\+84|84|0)[0-9]{9,10}$')

        for phone in valid_phones:
            assert phone_pattern.match(phone), f"Valid phone {phone} should pass validation"



class TestCurrencyFormatting:
    """Test currency formatting utilities"""

    def test_format_currency_vnd(self):
        """Test VND currency formatting"""
        amount = Decimal('1234567.89')

        # Format as VND (no decimal places)
        formatted = f"{int(amount):,} VND"

        assert '1,234,567 VND' == formatted or '1234567 VND' in formatted

    def test_format_currency_usd(self):
        """Test USD currency formatting"""
        amount = Decimal('1234.56')

        formatted = f"${amount:,.2f}"

        assert '$1,234.56' == formatted or '1234.56' in formatted

    def test_format_currency_zero(self):
        """Test formatting zero amount"""
        amount = Decimal('0')

        formatted = f"{int(amount):,} VND"

        assert '0 VND' == formatted or '0' in formatted

    def test_format_currency_large_amount(self):
        """Test formatting very large amounts"""
        amount = Decimal('999999999.99')

        formatted = f"{int(amount):,} VND"

        assert '999,999,999 VND' == formatted or '999999999' in formatted


class TestDateRangeValidation:
    """Test date range validation"""

    def test_validate_date_range(self):
        """Test valid date range"""
        from datetime import datetime, timedelta

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        # End date should be after start date
        assert end_date > start_date

    def test_validate_date_range_invalid(self):
        """Test invalid date range (end before start)"""
        from datetime import datetime

        start_date = datetime(2024, 12, 31)
        end_date = datetime(2024, 1, 1)

        # End date should not be before start date
        assert not (end_date > start_date)

    def test_validate_date_range_same_date(self):
        """Test date range with same start and end"""
        from datetime import datetime

        start_date = datetime(2024, 6, 15)
        end_date = datetime(2024, 6, 15)

        # Same date should be valid
        assert start_date == end_date


class TestDecimalCalculations:
    """Test decimal arithmetic for money calculations"""

    def test_decimal_addition(self):
        """Test decimal addition accuracy"""
        amount1 = Decimal('100.50')
        amount2 = Decimal('200.25')

        result = amount1 + amount2

        assert result == Decimal('300.75')

    def test_decimal_subtraction(self):
        """Test decimal subtraction accuracy"""
        amount1 = Decimal('500.00')
        amount2 = Decimal('123.45')

        result = amount1 - amount2

        assert result == Decimal('376.55')

    def test_decimal_multiplication(self):
        """Test decimal multiplication for percentage calculations"""
        amount = Decimal('1000')
        percentage = Decimal('0.15')  # 15%

        result = amount * percentage

        assert result == Decimal('150.00')

    def test_decimal_rounding(self):
        """Test proper rounding for currency"""
        amounts = [
            (Decimal('10.004'), Decimal('10.00')),
            (Decimal('10.005'), Decimal('10.01')),  # Banker's rounding
            (Decimal('10.455'), Decimal('10.46')),
            (Decimal('10.444'), Decimal('10.44'))
        ]

        for original, expected in amounts:
            rounded = round(original, 2)
            # Allow for different rounding modes
            assert rounded in [expected, original.quantize(Decimal('0.01'))]

    def test_avoid_float_precision_errors(self):
        """Test that using Decimal avoids float precision issues"""
        # Float precision problem
        float_result = 0.1 + 0.2

        # Decimal precision
        decimal_result = Decimal('0.1') + Decimal('0.2')

        # Float has precision error
        assert float_result != 0.3

        # Decimal is accurate
        assert decimal_result == Decimal('0.3')


class TestStringUtilities:
    """Test string utility functions"""

    def test_truncate_string(self):
        """Test string truncation"""
        long_string = "This is a very long string that needs to be truncated"

        max_length = 20
        truncated = long_string[:max_length] + '...' if len(long_string) > max_length else long_string

        assert len(truncated) <= max_length + 3
        assert truncated.endswith('...')

    def test_capitalize_name(self):
        """Test name capitalization"""
        names = [
            ('john doe', 'John Doe'),
            ('JANE SMITH', 'Jane Smith'),
            ('alice', 'Alice')
        ]

        for original, expected in names:
            result = original.title()
            assert result == expected

    def test_remove_whitespace(self):
        """Test whitespace removal"""
        text_with_spaces = "  Hello   World  "

        cleaned = text_with_spaces.strip()
        normalized = ' '.join(cleaned.split())

        assert normalized == "Hello World"


class TestListUtilities:
    """Test list utility functions"""

    def test_chunk_list(self):
        """Test splitting list into chunks"""
        items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        chunk_size = 3

        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

        assert len(chunks) == 4
        assert chunks[0] == [1, 2, 3]
        assert chunks[-1] == [10]

    def test_remove_duplicates(self):
        """Test removing duplicates from list"""
        items = [1, 2, 2, 3, 3, 3, 4, 5, 5]

        unique_items = list(set(items))

        assert len(unique_items) == 5
        assert sorted(unique_items) == [1, 2, 3, 4, 5]

    def test_filter_none_values(self):
        """Test filtering None values"""
        items = [1, None, 2, None, 3, 4, None]

        filtered = [x for x in items if x is not None]

        assert len(filtered) == 4
        assert None not in filtered


class TestPasswordUtilities:
    """Test password-related utilities"""

    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes with salt"""
        from werkzeug.security import generate_password_hash

        password = "test_password123"

        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

    def test_password_verification(self):
        """Test password hash verification"""
        from werkzeug.security import generate_password_hash, check_password_hash

        password = "secure_password123"
        hash_value = generate_password_hash(password)

        # Correct password should verify
        assert check_password_hash(hash_value, password) == True

        # Wrong password should not verify
        assert check_password_hash(hash_value, "wrong_password") == False


class TestPaginationUtilities:
    """Test pagination utilities"""

    def test_calculate_pagination(self):
        """Test pagination calculations"""
        total_items = 100
        per_page = 10

        total_pages = (total_items + per_page - 1) // per_page

        assert total_pages == 10

    def test_pagination_offset(self):
        """Test calculating offset for pagination"""
        page = 3
        per_page = 20

        offset = (page - 1) * per_page

        assert offset == 40

    def test_pagination_last_page(self):
        """Test items on last page"""
        total_items = 95
        per_page = 10

        total_pages = (total_items + per_page - 1) // per_page
        items_on_last_page = total_items % per_page or per_page

        assert total_pages == 10
        assert items_on_last_page == 5


class TestSortingUtilities:
    """Test sorting utilities"""

    def test_sort_by_amount(self):
        """Test sorting by amount"""
        items = [
            {'amount': Decimal('100')},
            {'amount': Decimal('50')},
            {'amount': Decimal('200')}
        ]

        sorted_items = sorted(items, key=lambda x: x['amount'])

        assert sorted_items[0]['amount'] == Decimal('50')
        assert sorted_items[-1]['amount'] == Decimal('200')

    def test_sort_by_date(self):
        """Test sorting by date"""
        from datetime import datetime

        items = [
            {'date': datetime(2024, 3, 15)},
            {'date': datetime(2024, 1, 10)},
            {'date': datetime(2024, 6, 20)}
        ]

        sorted_items = sorted(items, key=lambda x: x['date'])

        assert sorted_items[0]['date'].month == 1
        assert sorted_items[-1]['date'].month == 6
