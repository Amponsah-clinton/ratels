"""
Context processors for global template context.
"""
from django.conf import settings


def paystack_public_key(request):
    """Expose Paystack public key for donate modal and any page using Paystack inline."""
    try:
        from .views import _get_paystack_keys
        key, _ = _get_paystack_keys()
        return {"paystack_public_key": key}
    except Exception:
        key = getattr(settings, "PAYSTACK_PUBLIC_KEY", "pk_test_af37d26c0fa360522c4e66495f3877e498c18850")
        return {"paystack_public_key": key}
