from app.services.version_regression import diff_operations, localize_from_diff


def test_diff_added_changed_removed():
    old = [
        {"method": "GET", "path": "/pets/{id}", "summary": "get", "status_codes": ["200"]},
        {"method": "POST", "path": "/pets", "summary": "create", "status_codes": ["201"]},
    ]
    new = [
        {"method": "GET", "path": "/pets/{id}", "summary": "get pet", "status_codes": ["200", "404"]},
        {"method": "DELETE", "path": "/pets/{id}", "summary": "delete", "status_codes": ["204"]},
    ]
    d = diff_operations(old, new)
    assert len(d["added"]) == 1
    assert d["added"][0]["method"] == "DELETE"
    assert len(d["removed"]) == 1
    assert d["removed"][0]["method"] == "POST"
    assert len(d["changed"]) == 1
    loc = localize_from_diff(d)
    tracks = {x["reason"] for x in loc}
    assert any("新增" in t for t in tracks)
    assert any("变化" in t for t in tracks)
    assert any("删除" in t for t in tracks)
