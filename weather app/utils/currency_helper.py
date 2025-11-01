"""
Currency utility functions
"""
from config import Config


def format_currency(amount, currency='INR'):
    """
    Format amount with currency symbol
    
    Args:
        amount: Float amount to format
        currency: Currency code (default: INR)
        
    Returns:
        Formatted string like "₹1,234.56"
    """
    symbol = Config.CURRENCY_SYMBOLS.get(currency, currency)
    
    # Format with commas for Indian numbering system for INR
    if currency == 'INR':
        # Indian numbering: 1,23,456.78
        amount_str = f"{amount:,.2f}"
        parts = amount_str.split('.')
        integer_part = parts[0].replace(',', '')
        
        # Format Indian style
        if len(integer_part) > 3:
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            # Add commas every 2 digits from right in remaining part
            formatted = ''
            for i, digit in enumerate(reversed(remaining)):
                if i > 0 and i % 2 == 0:
                    formatted = ',' + formatted
                formatted = digit + formatted
            integer_part = formatted + ',' + last_three
        
        decimal_part = parts[1] if len(parts) > 1 else '00'
        return f"{symbol}{integer_part}.{decimal_part}"
    else:
        # Western numbering: 1,234.56
        return f"{symbol}{amount:,.2f}"


def get_currency_symbol(currency='INR'):
    """
    Get currency symbol
    
    Args:
        currency: Currency code
        
    Returns:
        Currency symbol string
    """
    return Config.CURRENCY_SYMBOLS.get(currency, currency)


def convert_currency(amount, from_currency, to_currency, rates=None):
    """
    Convert amount between currencies
    Note: This is a placeholder. In production, use a real exchange rate API
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code
        to_currency: Target currency code
        rates: Optional dict of exchange rates
        
    Returns:
        Converted amount
    """
    if from_currency == to_currency:
        return amount
    
    # Placeholder conversion rates (relative to INR)
    # In production, use a real API like exchangerate-api.com or fixer.io
    default_rates = {
        'INR': 1.0,
        'USD': 0.012,  # 1 INR = 0.012 USD
        'EUR': 0.011,
        'GBP': 0.0095,
        'AED': 0.044,
        'SGD': 0.016,
        'AUD': 0.018,
        'CAD': 0.016,
        'JPY': 1.79,
        'CNY': 0.086,
        'THB': 0.42,
        'MYR': 0.054
    }
    
    rates = rates or default_rates
    
    # Convert to INR first, then to target currency
    amount_in_inr = amount / rates.get(from_currency, 1.0)
    converted_amount = amount_in_inr * rates.get(to_currency, 1.0)
    
    return round(converted_amount, 2)


def validate_currency(currency):
    """
    Check if currency code is supported
    
    Args:
        currency: Currency code to validate
        
    Returns:
        Boolean
    """
    return currency in Config.SUPPORTED_CURRENCIES
