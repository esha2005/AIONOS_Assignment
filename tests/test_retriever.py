from backend.rag.retriever import PolicyRetriever


def _retrieve_ids(query: str, retriever: PolicyRetriever):
    out = retriever.retrieve(query=query, top_k=3, threshold=0.05)
    return [r["policy_id"] for r in out.get("results", [])]


def test_retriever_returns_kb02_for_vpn_issue():
    r = PolicyRetriever()
    ids = _retrieve_ids("My VPN stopped working", r)
    assert "KB-02" in ids, f"Expected KB-02 in results, got {ids}"


def test_retriever_returns_kb09_for_phishing():
    r = PolicyRetriever()
    ids = _retrieve_ids("I received a phishing email", r)
    assert "KB-09" in ids, f"Expected KB-09 in results, got {ids}"


def test_retriever_returns_kb07_for_guest_wifi():
    r = PolicyRetriever()
    ids = _retrieve_ids("I need guest Wi-Fi for a visitor", r)
    assert "KB-07" in ids, f"Expected KB-07 in results, got {ids}"


def test_retriever_returns_kb06_for_mailbox_full():
    r = PolicyRetriever()
    ids = _retrieve_ids("My mailbox is full", r)
    assert "KB-06" in ids, f"Expected KB-06 in results, got {ids}"


def test_retriever_returns_kb04_for_software_install():
    r = PolicyRetriever()
    ids = _retrieve_ids("I need to install software that is not in the catalog", r)
    assert "KB-04" in ids, f"Expected KB-04 in results, got {ids}"


def test_retriever_no_false_positive_for_unrelated_query():
    r = PolicyRetriever()
    out = r.retrieve(query="What is the weather today?", top_k=3, threshold=0.15)
    assert out.get("found") is False, f"Expected found=False for weather query, got {out}"
    assert out.get("results") == []
