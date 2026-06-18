"""
Seed test data for the Samanvaya + OpenIMIS test harness.
Creates mock claims (approved in OpenIMIS) + gateway config.
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openimis_test.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from openimis_test.claim.models import Claim, HealthFacility
from samanvaya.models import GatewayConfig


def seed():
    # Create health facilities
    hospitals = [
        ("HF-001", "Bir Hospital", "Kathmandu"),
        ("HF-002", "Civil Hospital", "Lalitpur"),
        ("HF-003", "Patan Hospital", "Lalitpur"),
        ("HF-004", "Nepal Medical College", "Kathmandu"),
        ("HF-005", "Grande International Hospital", "Kathmandu"),
    ]
    hf_objs = {}
    for code, name, district in hospitals:
        hf, _ = HealthFacility.objects.get_or_create(
            code=code, defaults={"name": name, "district": district}
        )
        hf_objs[code] = hf

    # Create claims — mix of statuses
    claims_data = [
        ("CLM-2024-001", "HF-001", "Ram Bahadur Thapa", 45000, 42000, Claim.STATUS_CHECKED),
        ("CLM-2024-002", "HF-002", "Sita Kumari Shrestha", 12500, 12500, Claim.STATUS_CHECKED),
        ("CLM-2024-003", "HF-003", "Hari Prasad Pokharel", 78000, 75000, Claim.STATUS_CHECKED),
        ("CLM-2024-004", "HF-004", "Gita Devi Maharjan", 8500, 8500, Claim.STATUS_CHECKED),
        ("CLM-2024-005", "HF-005", "Krishna Bahadur Gurung", 125000, 120000, Claim.STATUS_CHECKED),
        ("CLM-2024-006", "HF-001", "Anita Tamang", 33000, 33000, Claim.STATUS_CHECKED),
        ("CLM-2024-007", "HF-002", "Bijay Rai", 5600, 5600, Claim.STATUS_PROCESSED),
        ("CLM-2024-008", "HF-003", "Kamala Basnet", 92000, 88000, Claim.STATUS_CHECKED),
        ("CLM-2024-009", "HF-004", "Deepak Adhikari", 15000, 15000, Claim.STATUS_ENTERED),
        ("CLM-2024-010", "HF-005", "Sunita Lama", 67000, 65000, Claim.STATUS_CHECKED),
    ]

    for code, hf_code, name, claimed, approved, status in claims_data:
        Claim.objects.get_or_create(
            code=code,
            defaults={
                "health_facility": hf_objs[hf_code],
                "insuree_name": name,
                "claimed": claimed,
                "approved": approved,
                "status": status,
            },
        )

    # Create gateway config
    GatewayConfig.objects.get_or_create(
        name="mock_bank",
        defaults={
            "is_active": True,
            "api_endpoint": "http://localhost:8001",
            "config": {"base_url": "http://localhost:8001"},
        },
    )

    approved = Claim.objects.filter(status=Claim.STATUS_CHECKED).count()
    total = Claim.objects.count()
    print(f"Seeded {total} claims ({approved} approved/CHECKED) + 1 gateway config.")


if __name__ == "__main__":
    seed()
