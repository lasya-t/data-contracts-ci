from contracts.model import Contract
from contracts.validate import validate_batch

C = Contract.load("contracts/orders.yaml")
GOOD = {"order_id": "O0000001", "customer_id": "C1", "created_at": "2025-01-01T10:00:00",
        "status": "paid", "amount": 10.5, "currency": "USD", "channel": "web"}


def test_good_record_passes_with_optional_fields_defaulted():
    r = validate_batch(C, [GOOD])
    assert len(r.valid) == 1 and r.valid[0]["promo_code"] is None


def test_each_violation_is_reported():
    bad = [
        {**GOOD, "status": "on_hold"},
        {**GOOD, "amount": -3},
        {**GOOD, "order_id": "12345"},
        {k: v for k, v in GOOD.items() if k != "channel"},
        {**GOOD, "surprise_field": 1},
        {**GOOD, "created_at": "yesterday"},
    ]
    r = validate_batch(C, bad)
    assert len(r.rejected) == 6 and r.reject_rate == 1.0
    reasons = " ".join(r.reasons)
    for expected in ("status: literal_error", "amount: greater_than_equal", "order_id: string_pattern_mismatch",
                     "channel: missing", "surprise_field: extra_forbidden", "created_at: datetime"):
        assert expected in reasons
