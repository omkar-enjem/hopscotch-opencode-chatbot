from app.faq_search import get_index
from app.tools import (
    escalate_to_human,
    get_product,
    recommend_outfit,
    remember_child,
    run_tool,
    search_faq,
    search_products,
    start_return,
    suggest_size,
    track_order,
)


def test_search_products_by_age_and_gender():
    res = search_products(age=4, gender="girl", occasion="party")
    assert res["count"] > 0
    assert all("sku" in p for p in res["products"])


def test_search_products_price_filter():
    res = search_products(max_price=1000, limit=20)
    assert all(p["price"] <= 1000 for p in res["products"])


def test_get_product_by_sku():
    res = get_product("KF-DR-001")
    assert res["name"].startswith("Rainbow")


def test_get_product_missing():
    assert "error" in get_product("NOPE-999")


def test_recommend_outfit_returns_pieces():
    res = recommend_outfit(age=4, gender="girl", occasion="party")
    assert res["main_pieces"]


def test_suggest_size_by_height():
    res = suggest_size(height_cm=104)
    assert res["recommended_size"] == "4T"


def test_suggest_size_by_age():
    res = suggest_size(age=6)
    assert "recommended_size" in res


def test_track_order():
    res = track_order("KF10002")
    assert res["status"] == "in_transit"
    assert res["order_code"] == "KF10002"


def test_track_order_missing():
    assert "error" in track_order("KF99999")


def test_start_return():
    res = start_return("KF10001", reason="wrong size")
    assert res["return_status"] == "initiated"


def test_search_faq_shipping():
    hits = search_faq("do you deliver to pokhara")
    assert hits["results"]
    assert any("deliver" in h["answer"].lower() or "deliver" in h["question"].lower()
               for h in hits["results"])


def test_faq_index_retrieval():
    hits = get_index().search("return policy for sale items")
    assert hits
    assert hits[0].topic in ("returns", "product", "orders")


def test_session_tools_via_dispatch():
    sid = "test-session-tools"
    saved = run_tool("remember_child", {"age": 5, "height_cm": 110}, sid)
    assert saved["saved"] is True
    escalated = run_tool("escalate_to_human", {"reason": "test"}, sid)
    assert escalated["escalated"] is True


def test_remember_child_direct():
    res = remember_child("sess-direct", child_name="Maya", age=4, height_cm=104)
    assert "Maya" in res["profile"]


def test_escalate_direct():
    res = escalate_to_human("sess-esc", reason="wants manager")
    assert res["escalated"] is True
