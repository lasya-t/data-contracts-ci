import copy

import pytest
import yaml

from contracts.compat import BREAKING, SAFE, diff, verdict
from contracts.model import Contract

BASE = yaml.safe_load(open("contracts/orders.yaml"))


def changed(version, edit):
    d = copy.deepcopy(BASE)
    d["version"] = version
    edit(d["fields"])
    return Contract.from_dict(d)


OLD = Contract.from_dict(BASE)


@pytest.mark.parametrize("edit,severity", [
    (lambda f: f.pop("device_sku"), BREAKING),
    (lambda f: f["amount"].update(type="string"), BREAKING),
    (lambda f: f["channel"].update(required=False), BREAKING),
    (lambda f: f["status"]["enum"].append("on_hold"), BREAKING),
    (lambda f: f["amount"].update(min=-100), BREAKING),
    (lambda f: f.update(gift_wrap={"type": "boolean", "required": False}), SAFE),
    (lambda f: f["status"]["enum"].remove("returned"), SAFE),
    (lambda f: f["promo_code"].update(required=True), SAFE),
    (lambda f: f["amount"].update(max=100000), SAFE),
])
def test_change_classification(edit, severity):
    changes = diff(OLD, changed("1.3.0", edit))
    assert len(changes) == 1 and changes[0].severity == severity


def test_breaking_change_needs_major_bump():
    ok, _, reason = verdict(OLD, changed("1.3.0", lambda f: f.pop("device_sku")))
    assert not ok and "major version" in reason
    ok, _, _ = verdict(OLD, changed("2.0.0", lambda f: f.pop("device_sku")))
    assert ok


def test_any_change_needs_a_version_bump():
    ok, _, reason = verdict(OLD, changed("1.2.0", lambda f: f.update(note={"type": "string", "required": False})))
    assert not ok and "did not increase" in reason


def test_no_change_is_fine():
    assert verdict(OLD, Contract.from_dict(copy.deepcopy(BASE)))[0]
