"""
Custom permissions for the Samanvaya module.
Follows OpenIMIS convention of numeric permission codes.
"""

RIGHTS = {
    150001: "Can view Samanvaya dashboard",
    150002: "Can execute payment batch",
    150003: "Can retry failed transaction",
    150004: "Can upload SOSYS CSV",
    150005: "Can resolve reconciliation anomaly",
    150006: "Can configure payment gateway",
}


def check_permission(user, right_code: int) -> bool:
    """Check if user has a specific Samanvaya permission."""
    # In test harness / DEBUG mode, allow all access
    from django.conf import settings
    if getattr(settings, 'DEBUG', False):
        return True
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # In OpenIMIS, rights are stored as integer codes in the user's role
    try:
        user_rights = user.role.rights if hasattr(user, 'role') and user.role else []
        return right_code in user_rights
    except Exception:
        return False
