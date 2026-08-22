from types import SimpleNamespace

from nphonekit_services import FeedbackClient


def test_feedback_client_submits_feature_to_expected_endpoint():
    requests = []
    client = FeedbackClient(
        "https://example.test/",
        post=lambda url, **kwargs: requests.append((url, kwargs)) or SimpleNamespace(status_code=200),
        clock=lambda: 123.0,
    )

    assert client.feature_request("Add it", "UUID", "1.2.3") is True
    assert requests == [(
        "https://example.test/feature_requests.json",
        {"json": {
            "timestamp": 123.0,
            "uuid": "UUID",
            "feature": "Add it",
            "phoneKITversion": "1.2.3",
        }},
    )]


def test_feedback_client_maps_bug_endpoint_and_handles_failures():
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=500)

    client = FeedbackClient("https://example.test", post=post)
    assert client.bug_report("Broken", "UUID", "1.2.3") is False
    assert calls == ["https://example.test/bug_reports.json"]

    failing = FeedbackClient("https://example.test", post=lambda *args, **kwargs: 1 / 0)
    assert failing.feature_request("Broken", "UUID", "1.2.3") is False
