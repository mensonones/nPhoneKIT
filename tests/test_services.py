from types import SimpleNamespace

from nphonekit_services import FeedbackClient, TelemetryClient, UpdateClient, public_hardware_uuid


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


def test_update_client_reads_release_tag_and_strips_both_v_prefixes():
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"tag_name": "v1.7.0"}'

    calls = []
    client = UpdateClient(
        urlopen=lambda url, timeout: calls.append((url, timeout)) or Response()
    )

    assert client.latest() == ("v1.7.0", "1.7.0")
    assert calls == [
        ("https://api.github.com/repos/nlckysolutions/nPhoneKIT/releases/latest", 4)
    ]


def test_public_hardware_uuid_is_stable_and_hashed():
    first = public_hardware_uuid(12345)
    second = public_hardware_uuid(12345)

    assert first == second
    assert str(first) != "12345"


def test_telemetry_client_does_not_post_when_disabled(tmp_path):
    calls = []
    client = TelemetryClient(
        "https://example.test", False, True, "1.2.3",
        post=lambda *args, **kwargs: calls.append((args, kwargs)),
        marker_path=tmp_path / ".notfirst",
    )

    client.submit("UUID", None, "ACTION", "Success")

    assert calls == []


def test_telemetry_client_posts_first_payload(tmp_path):
    calls = []
    client = TelemetryClient(
        "https://example.test", True, True, "1.2.3",
        post=lambda url, **kwargs: calls.append((url, kwargs)),
        pull_errors=lambda: "output",
        marker_path=tmp_path / ".notfirst",
        clock=lambda: 123.0,
    )

    client.submit("UUID", None, "ACTION", "Success")

    assert calls == [(
        "https://example.test/success_checks_v2.json",
        {"json": {
            "timestamp": 123.0, "uuid": "UUID", "model": "Unknown",
            "action": "ACTION", "status": "Success",
            "phoneKITversion": "1.2.3", "errors": "output",
        }},
    )]


def test_telemetry_client_uses_model_string_verbatim(tmp_path):
    # model is now a plain string (from nphonekit_core.parse_model), not a
    # regex match object, so it must be sent as-is.
    calls = []
    client = TelemetryClient(
        "https://example.test", True, True, "1.2.3",
        post=lambda url, **kwargs: calls.append((url, kwargs)),
        pull_errors=lambda: "",
        marker_path=tmp_path / ".notfirst",
        clock=lambda: 1.0,
    )

    client.submit("UUID", "SM-G991B", "ACTION", "Success")

    assert calls[0][1]["json"]["model"] == "SM-G991B"
