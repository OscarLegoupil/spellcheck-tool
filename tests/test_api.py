import json
import time

from fastapi.testclient import TestClient
from test_annotations import make_pdf

from spellcheck_tool.app import create_app
from spellcheck_tool.models import Finding


class FixtureEngines:
    def status(self):
        return {"finnish": True, "english": True}

    def check(self, segment, options):
        if "recieve" not in segment.text:
            return []
        start = segment.text.index("recieve")
        return [
            Finding(
                segment.id, start, start + 7, "recieve", ["receive"], "FIXTURE", "spelling", "test"
            )
        ]

    def close(self):
        pass


def test_auth_upload_review_and_export():
    app = create_app("secret", FixtureEngines())
    headers = {"Authorization": "Bearer secret"}
    with TestClient(app) as c:
        assert c.get("/api/status").status_code == 401
        assert c.get("/api/status", headers=headers).status_code == 200
        r = c.post(
            "/api/reviews",
            headers=headers,
            files={"file": ("example.pdf", make_pdf(), "application/pdf")},
            data={"settings": json.dumps({"language": "en"})},
        )
        assert r.status_code == 200
        key = r.json()["id"]
        for _ in range(100):
            result = c.get("/api/reviews/" + key, headers=headers).json()
            if result["state"] in ("complete", "failed"):
                break
            time.sleep(0.01)
        assert result["state"] == "complete", result
        f = result["result"]["findings"][0]
        output = c.post(
            "/api/reviews/" + key + "/export",
            headers=headers,
            json={"choices": [{"id": f["id"], "correction": "receive"}]},
        )
        assert output.status_code == 200
        assert output.content.startswith(b"%PDF")
        assert c.delete("/api/reviews/" + key, headers=headers).status_code == 200
        assert c.get("/api/reviews/" + key, headers=headers).status_code == 404


def test_invalid_options_and_file_type():
    with TestClient(create_app("secret", FixtureEngines())) as c:
        headers = {"Authorization": "Bearer secret"}
        r = c.post(
            "/api/reviews",
            headers=headers,
            files={"file": ("x.pdf", make_pdf())},
            data={"settings": '{"language":"fr"}'},
        )
        assert r.status_code == 400
        r = c.post("/api/reviews", headers=headers, files={"file": ("x.exe", b"hello")})
        assert r.status_code == 400
