from decimal import Decimal


TIER_LIMITS = {
    "tier1": {
        "min_transaction": Decimal("100"),
        "max_single_transfer": Decimal("100000"),
        "max_single_withdrawal": Decimal("50000"),
        "max_daily_transfer": Decimal("200000"),
        "max_daily_withdrawal": Decimal("100000"),
    },
    "tier2": {
        "min_transaction": Decimal("100"),
        "max_single_transfer": Decimal("500000"),
        "max_single_withdrawal": Decimal("200000"),
        "max_daily_transfer": Decimal("1000000"),
        "max_daily_withdrawal": Decimal("500000"),
    },
    "tier3": {
        "min_transaction": Decimal("100"),
        "max_single_transfer": Decimal("2000000"),
        "max_single_withdrawal": Decimal("1000000"),
        "max_daily_transfer": Decimal("5000000"),
        "max_daily_withdrawal": Decimal("2000000"),
    }
}


def get_limits(tier: str) -> dict:
    return TIER_LIMITS.get(tier, TIER_LIMITS["tier1"])