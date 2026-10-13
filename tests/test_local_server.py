"""What the local server refuses, and how a running search is stopped.

The desktop app is a web server on 127.0.0.1 and the page that talks to it runs
in whatever browser the user already has open -- alongside every other tab they
are looking at.  Without a ``Host`` check that server answers to any name that
resolves to the loopback address, which is the whole mechanism of a DNS-rebinding
attack: the attacker's page is served from ``evil.example``, the browser is told
``evil.example`` is 127.0.0.1, and the same-origin policy then permits the page
to read every reply.  Both halves of the defence are checked here, because both
are the kind of thing a later refactor removes without noticing:

* the ``Host`` header must be a name this server is reachable as, and an
  ``Origin`` header must agree with it;
* the page is served with a policy that only permits its own origin's assets.

The same file covers stopping a running search, which is the other half of "the
user is in control": a job is cancelled through its progress callback, so the
test that matters is that the callback really unwinds the search rather than
being swallowed by the engine's own error handling.
"""

from __future__ import annotations

import http.client
import json
import time
import unittest
from unittest import mock

from buttcrack import server
from buttcrack.desktop import LocalApp


def headers_of(port: int, method: str, path: str, extra: dict[str, str] | None = None, body: bytes | None = None):
    """One raw request, so the test controls the Host header itself."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        connection.request(method, path, body=body, headers=extra or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


class HostHeaderTests(unittest.TestCase):
    """The rule, without a socket in the way."""

    def test_loopback_names_are_accepted_on_a_loopback_bind(self):
        for name in ("127.0.0.1", "127.0.0.1:8099", "localhost", "localhost:8099", "[::1]:8099"):
            self.assertTrue(server.host_is_allowed(name, "127.0.0.1"), name)

    def test_a_rebound_name_is_refused(self):
        # The attack, in one line: the DNS answer points at 127.0.0.1 and the
        # request still arrives under the attacker's own name.
        for name in ("evil.example", "evil.example:8099", "buttcrack.local", "127.0.0.1.evil.example"):
            self.assertFalse(server.host_is_allowed(name, "127.0.0.1"), name)

    def test_a_missing_or_broken_host_is_refused(self):
        for name in ("", "   ", ":", "http://", "null"):
            self.assertFalse(server.host_is_allowed(name, "127.0.0.1"), name)

    def test_a_lan_bind_accepts_addresses_but_not_names(self):
        # `serve` is deliberately reachable, so the person who typed the LAN
        # address must get in.  A name still is not allowed: only the rebound
        # request arrives under a name somebody else chose.
        self.assertTrue(server.host_is_allowed("192.168.1.5:8080", "0.0.0.0"))
        self.assertTrue(server.host_is_allowed("[2001:db8::1]:8080", "0.0.0.0"))
        self.assertTrue(server.host_is_allowed("localhost:8080", "0.0.0.0"))
        self.assertFalse(server.host_is_allowed("evil.example", "0.0.0.0"))

    def test_a_specific_bind_answers_for_itself(self):
        self.assertTrue(server.host_is_allowed("192.168.1.5:8080", "192.168.1.5"))
        self.assertFalse(server.host_is_allowed("192.168.1.6:8080", "192.168.1.5"))

    def test_an_origin_is_read_the_same_way_as_a_host(self):
        self.assertEqual(server._authority("http://127.0.0.1:8099"), ("127.0.0.1", 8099))
        self.assertEqual(server._authority("127.0.0.1:8099"), ("127.0.0.1", 8099))
        self.assertEqual(server._authority("localhost"), ("localhost", None))
        self.assertIsNone(server._authority("null"))
        self.assertIsNone(server._authority(""))


class LocalServerRefusalTests(unittest.TestCase):
    """The same rule, through a real request against a real LocalApp."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = LocalApp(port=0)
        cls.app.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.stop()

    def test_a_rebound_host_header_is_refused(self):
        status, _headers, body = headers_of(self.app.port, "GET", "/api/health", {"Host": "evil.example"})
        self.assertEqual(status, 403, body)
        self.assertIn("Host", json.loads(body)["error"])

    def test_the_ordinary_request_still_works(self):
        status, _headers, body = headers_of(self.app.port, "GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["name"], "buttcrack")

    def test_a_cross_origin_post_is_refused_even_though_the_body_is_json(self):
        payload = json.dumps({"text": "Wkh txlfn eurzq ira"}).encode("utf-8")
        status, _headers, body = headers_of(
            self.app.port,
            "POST",
            "/api/identify",
            {"Content-Type": "application/json", "Origin": "https://evil.example"},
            payload,
        )
        self.assertEqual(status, 403, body)
        self.assertIn("cross-origin", json.loads(body)["error"])

    def test_a_same_origin_post_is_accepted(self):
        payload = json.dumps({"text": "Wkh txlfn eurzq ira"}).encode("utf-8")
        host = f"127.0.0.1:{self.app.port}"
        status, _headers, body = headers_of(
            self.app.port,
            "POST",
            "/api/identify",
            {"Content-Type": "application/json", "Origin": f"http://{host}"},
            payload,
        )
        self.assertEqual(status, 200, body)
        self.assertIn("hypotheses", json.loads(body))

    def test_a_browser_shaped_post_without_json_is_refused(self):
        # `text/plain` is a CORS *simple* request: no preflight, so the server
        # is the only thing that can refuse it.  A command-line client sends no
        # Origin and keeps working, which is why the rule keys off Origin.
        status, _headers, body = headers_of(
            self.app.port,
            "POST",
            "/api/identify",
            {"Content-Type": "text/plain", "Origin": f"http://127.0.0.1:{self.app.port}"},
            b'{"text":"Wkh txlfn"}',
        )
        self.assertEqual(status, 415, body)

    def test_the_page_is_served_with_a_content_security_policy(self):
        status, headers, body = headers_of(self.app.port, "GET", "/")
        self.assertEqual(status, 200)
        policy = headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", policy)
        self.assertIn("img-src 'self' data:", policy)  # the favicon is a data: URI
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertIn(b"<html", body.lower())

    def test_the_static_assets_do_not_carry_the_page_policy(self):
        # A policy on a stylesheet or a script would be noise, and noise is what
        # gets deleted by whoever next tidies the headers.
        _status, headers, _body = headers_of(self.app.port, "GET", "/app.js")
        self.assertNotIn("Content-Security-Policy", headers)


class CancelTests(unittest.TestCase):
    """Stopping a search that is already running."""

    def setUp(self) -> None:
        self.store = server.JobStore()

    def test_cancelling_an_unknown_job_says_so(self):
        self.assertFalse(self.store.cancel("no-such-job"))

    def _cancel_through_a_fake_solver(self) -> dict:
        """Run a job whose search reports progress, then stop it."""
        steps = {"count": 0}

        def fake_solve(_text, **kwargs):  # noqa: ANN001 - stands in for solve()
            progress = kwargs.get("progress")
            for index in range(400):  # 400 x 5 ms: bounded, so a failure ends
                steps["count"] = index
                if progress:
                    progress(f"step {index}", index / 400, {})
                time.sleep(0.005)
            raise AssertionError("the search was not cancelled")

        with mock.patch.object(server, "solve", fake_solve):
            job_id = self.store.create({"text": "X", "budget": 60.0, "workers": 1})
            deadline = time.time() + 10
            while time.time() < deadline and steps["count"] < 3:
                time.sleep(0.01)
            self.assertTrue(self.store.cancel(job_id), "the job vanished before it could be cancelled")
            while time.time() < deadline:
                job = self.store.get(job_id)
                if job and job["done"]:
                    return job
                time.sleep(0.02)
        self.fail("a cancelled job never finished")

    def test_a_cancelled_job_stops_and_says_so(self):
        job = self._cancel_through_a_fake_solver()
        self.assertTrue(job["cancelled"])
        self.assertTrue(job["done"])
        self.assertIsNone(job["error"], "stopping at the user's request is not an error")
        self.assertIsNone(job["report"])
        self.assertIn("cancelled by request", [line["message"] for line in job["progress"]])

    def test_the_poller_can_see_that_the_stop_was_heard(self):
        # The UI polls this endpoint, and "have you heard me yet?" is what keeps
        # the button from looking broken during the moment before the search
        # reaches its next milestone.
        def fake_solve(_text, **kwargs):  # noqa: ANN001 - stands in for solve()
            progress = kwargs["progress"]
            for index in range(300):
                progress(f"step {index}", 0.0, {})
                time.sleep(0.01)

        with mock.patch.object(server, "solve", fake_solve):
            job_id = self.store.create({"text": "X", "budget": 60.0, "workers": 1})
            time.sleep(0.2)
            self.store.cancel(job_id)
            self.assertTrue(self.store.get(job_id)["cancel_requested"])

    def test_cancelling_a_finished_job_changes_nothing(self):
        job_id = self.store.create({"text": "X", "budget": 0.5, "workers": 1})
        deadline = time.time() + 30
        while time.time() < deadline and not self.store.get(job_id)["done"]:
            time.sleep(0.05)
        self.assertTrue(self.store.get(job_id)["done"])
        self.assertTrue(self.store.cancel(job_id), "a finished job is still a known job")
        self.assertFalse(self.store.get(job_id)["cancelled"])


class CancelRouteTests(unittest.TestCase):
    """The endpoint the page calls."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = LocalApp(port=0)
        cls.app.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.stop()

    def test_cancelling_an_unknown_job_is_a_404(self):
        status, _headers, body = headers_of(
            self.app.port,
            "POST",
            "/api/job/deadbeefcafe/cancel",
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 404, body)

    def test_the_endpoint_answers_for_a_known_job(self):
        job_id = server.JOBS.create({"text": "Wkh txlfn", "budget": 0.5, "workers": 1})
        status, _headers, body = headers_of(
            self.app.port,
            "POST",
            f"/api/job/{job_id}/cancel",
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["job"], job_id)


if __name__ == "__main__":
    unittest.main()
