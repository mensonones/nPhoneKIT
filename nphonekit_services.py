"""Small service clients used by the nPhoneKIT application."""

import time
import json
import hashlib
import urllib.request
from pathlib import Path
import uuid as uuid_module

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


class UpdateClient:
    """Read the latest GitHub release for the application."""

    def __init__(self, repository="nlckysolutions/nPhoneKIT", urlopen=urllib.request.urlopen):
        self.url = f"https://api.github.com/repos/{repository}/releases/latest"
        self.urlopen = urlopen

    def latest(self):
        with self.urlopen(self.url, timeout=4) as response:
            data = json.loads(response.read().decode())
        raw_version = data["tag_name"]
        version = raw_version.lstrip("v").lstrip("ⅴ")
        return raw_version, version


def public_hardware_uuid(node=None):
    """Return the stable, hashed hardware identifier used by telemetry."""
    mac = uuid_module.getnode() if node is None else node
    hashed = hashlib.sha256(str(mac).encode("utf-8")).hexdigest()
    return uuid_module.UUID(hashlib.md5(hashed.encode()).hexdigest())


class TelemetryClient:
    """Submit optional, anonymized success telemetry."""

    def __init__(self, base_url, enabled, basic, version, post=None,
                 pull_errors=lambda: "", get_os_info=lambda: {}, marker_path=None,
                 clock=time.time):
        self.base_url = base_url.rstrip("/")
        self.enabled = enabled
        self.basic = basic
        self.version = version
        self.post = post
        self.pull_errors = pull_errors
        self.get_os_info = get_os_info
        self.marker_path = Path(marker_path or ".notfirst")
        self.clock = clock

    def _post(self, endpoint, data):
        post = self.post or (requests.post if requests is not None else None)
        if post is None:
            return
        try:
            post(f"{self.base_url}/{endpoint}.json", json=data)
        except Exception:
            pass

    def submit(self, identifier, model, action, status, first=True):
        if not self.enabled or not self.basic:
            return
        if first:
            self._post("success_checks_v2", {
                "timestamp": self.clock(), "uuid": str(identifier),
                "model": model if model else "Unknown",
                "action": action, "status": status,
                "phoneKITversion": self.version, "errors": self.pull_errors(),
            })
            return
        self._post("success_checks", {
            "timestamp": self.clock(), "uuid": str(identifier),
            "model": "NOT_First", "action": "NOT_First", "status": "Success",
            "phoneKITversion": self.version,
        })
        if not self.marker_path.is_file():
            self._post("success_checks+oi", {
                "timestamp": self.clock(), "uuid": str(identifier),
                "osinfo": json.dumps(self.get_os_info()),
            })
            try:
                self.marker_path.touch()
            except OSError:
                pass
