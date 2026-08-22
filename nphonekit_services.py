"""Small service clients used by the nPhoneKIT application."""

import time

try:
    import requests
except ModuleNotFoundError:  # Tests can inject a transport without requests installed.
    requests = None


class FeedbackClient:
    """Submit feature requests and bug reports to the configured backend."""

    def __init__(self, base_url, post=None, clock=time.time):
        self.base_url = base_url.rstrip("/")
        if post is None:
            if requests is None:
                raise RuntimeError("requests is required to submit feedback")
            post = requests.post
        self.post = post
        self.clock = clock

    def submit(self, kind, description, uuid, version):
        endpoints = {"feature": "feature_requests", "bug": "bug_reports"}
        data = {
            "timestamp": self.clock(),
            "uuid": str(uuid),
            kind: description,
            "phoneKITversion": version,
        }
        try:
            response = self.post(f"{self.base_url}/{endpoints[kind]}.json", json=data)
        except Exception:
            return False
        return response.status_code == 200

    def feature_request(self, description, uuid, version):
        return self.submit("feature", description, uuid, version)

    def bug_report(self, description, uuid, version):
        return self.submit("bug", description, uuid, version)
