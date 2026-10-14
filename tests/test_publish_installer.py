"""Publishing the paid build: the object name, the URL, and what is refused.

The four values this prints go straight onto the download page, and the page
promises that the file behind its link is the one those numbers describe.  So the
parts worth pinning down are the ones that decide *what* is published and *where*
it lands: the object name, the public URL built from it, and the upload's
headers, which are the difference between a download and a corrupt file.

Offline: the upload is mocked, and the dry run is asserted not to call it.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publish = _load("publish_installer")

INSTALLER_BYTES = b"MZ" + bytes(range(256)) * 8
STORAGE_FLAGS = [
    "--bucket", "buttcrack-downloads",
    "--endpoint", "https://acct.r2.cloudflarestorage.com",
    "--base-url", "https://downloads.example.com",
]

#: The same five names the workflow checks for.
STORAGE_ENV = {
    "BUTTCRACK_DELIVERY_BUCKET": "buttcrack-downloads",
    "BUTTCRACK_DELIVERY_ENDPOINT": "https://acct.r2.cloudflarestorage.com",
    "BUTTCRACK_DELIVERY_BASE_URL": "https://downloads.example.com",
}


@contextlib.contextmanager
def captured_stdout():
    """Stdout of a `main` call, so its contract can be asserted on."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        yield buffer


def fake_upload():
    """A stand-in for the `aws s3 cp` subprocess, recording what it was asked."""
    result = mock.Mock(returncode=0, stdout="upload: ...", stderr="")

    def run(command, capture_output=True, text=True, env=None):
        return result

    return mock.Mock(side_effect=run)


class ObjectNaming(unittest.TestCase):
    def test_version_comes_out_of_the_installer_name(self):
        self.assertEqual(publish.parse_version("buttcrack-setup-1.2.0.exe"), "1.2.0")
        self.assertEqual(publish.parse_version("/tmp/dist/buttcrack-setup-10.0.3.exe"), "10.0.3")

    def test_anything_else_is_refused(self):
        for name in ("buttcrack.exe", "buttcrack-setup.exe", "buttcrack-setup-beta.exe", "notes.txt"):
            with self.subTest(name=name), self.assertRaises(SystemExit):
                publish.parse_version(name)

    def test_the_token_is_unguessable_and_sixteen_hex_digits(self):
        tokens = {publish.new_token() for _ in range(50)}
        self.assertEqual(len(tokens), 50, "a token that repeats is not a paywall")
        for token in tokens:
            self.assertRegex(token, re.compile(r"^[0-9a-f]{16}$"))

    def test_the_object_name_carries_the_version_and_the_token(self):
        self.assertEqual(
            publish.object_key("1.2.0", "7f3a9c2e51b04d88"),
            "buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe",
        )


class DeliveryUrl(unittest.TestCase):
    def test_base_url_and_object_name_are_joined(self):
        self.assertEqual(
            publish.delivery_url("https://downloads.example.com", "", "buttcrack-setup-1.2.0-abc.exe"),
            "https://downloads.example.com/buttcrack-setup-1.2.0-abc.exe",
        )

    def test_a_prefix_becomes_one_clean_path(self):
        for prefix in ("releases", "/releases", "releases/", "/releases/"):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    publish.delivery_url("https://downloads.example.com/", prefix, "app.exe"),
                    "https://downloads.example.com/releases/app.exe",
                )

    def test_no_base_url_means_no_url_rather_than_a_broken_one(self):
        self.assertEqual(publish.delivery_url("", "", "app.exe"), "")


class Upload(unittest.TestCase):
    def test_the_upload_sets_the_headers_the_download_depends_on(self):
        command = publish.aws_command(Path("buttcrack-setup-1.2.0.exe"), "bucket", "key.exe", "https://acct.r2.example")
        joined = " ".join(command)
        self.assertEqual(command[0], "aws")
        self.assertIn("s3://bucket/key.exe", joined)
        self.assertIn("--endpoint-url https://acct.r2.example", joined)
        # Served as text/html an .exe arrives corrupt; without the
        # content-disposition a browser may try to render it instead of saving it.
        self.assertIn("--content-type application/octet-stream", joined)
        self.assertIn("--content-disposition", joined)
        self.assertIn("immutable", joined)

    def test_an_r2_endpoint_gets_the_region_the_cli_refuses_to_sign_without(self):
        env = publish.upload_env("https://abc123.r2.cloudflarestorage.com")
        self.assertEqual(env["AWS_DEFAULT_REGION"], "auto")

    def test_an_explicit_region_always_wins(self):
        with mock.patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-west-004"}):
            env = publish.upload_env("https://abc123.r2.cloudflarestorage.com")
        self.assertEqual(env["AWS_DEFAULT_REGION"], "us-west-004")

    def test_other_hosts_are_not_given_a_region_that_would_break_their_signing(self):
        # S3 and B2 both sign a real region; inventing one for them turns a
        # missing setting into a signature error that reads like a bad key.
        for endpoint in ("https://s3.us-east-1.amazonaws.com", "https://s3.us-west-004.backblazeb2.com"):
            with self.subTest(endpoint=endpoint), mock.patch.dict(os.environ, {}, clear=True):
                self.assertNotIn("AWS_DEFAULT_REGION", publish.upload_env(endpoint))

    def test_the_region_is_passed_to_the_upload_subprocess(self):
        run = fake_upload()
        with mock.patch.object(publish.subprocess, "run", run), mock.patch.object(
            publish.shutil, "which", return_value="/usr/bin/aws"
        ), mock.patch.dict(os.environ, {}, clear=True), captured_stdout():
            publish.run_upload(Path("x.exe"), "bucket", "key", "https://abc.r2.cloudflarestorage.com")
        self.assertEqual(run.call_args.kwargs["env"]["AWS_DEFAULT_REGION"], "auto")

    def test_a_missing_aws_cli_says_how_to_get_it(self):
        with mock.patch.object(publish.shutil, "which", return_value=None), self.assertRaises(SystemExit) as caught:
            publish.run_upload(Path("x.exe"), "bucket", "key", "https://endpoint")
        self.assertIn("pip install awscli", str(caught.exception))


class MainBehaviour(unittest.TestCase):
    """`main` end to end, with the subprocess replaced by a mock."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.installer = Path(self.tmp.name) / "buttcrack-setup-1.2.0.exe"
        self.installer.write_bytes(INSTALLER_BYTES)
        # The fixture is deliberately a fixed 1.2.0 so these tests do not churn
        # on every release. main() now compares the installer's version against
        # the checkout's, so pin the checkout to the fixture rather than let the
        # comparison depend on whatever version the repository happens to be at.
        # VersionGuard below tests the comparison itself, unpinned.
        patcher = mock.patch.object(publish, "repo_version", return_value="1.2.0")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _main(self, *args: str) -> tuple[int, str]:
        """Run `main` with the upload mocked; return its code and its stdout."""
        with mock.patch.object(publish.subprocess, "run", fake_upload()), mock.patch.object(
            publish.shutil, "which", return_value="/usr/bin/aws"
        ), captured_stdout() as out:
            code = publish.main([str(self.installer), *args])
        return code, out.getvalue()

    def test_dry_run_uploads_nothing_and_still_shows_the_link(self):
        run = fake_upload()
        with mock.patch.object(publish.subprocess, "run", run), mock.patch.object(
            publish.shutil, "which"
        ), captured_stdout() as out:
            code = publish.main([str(self.installer), "--dry-run", "--token", "7f3a9c2e51b04d88", *STORAGE_FLAGS])
        self.assertEqual(code, 0)
        run.assert_not_called()
        self.assertIn("https://downloads.example.com/buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe", out.getvalue())
        self.assertIn('"version": "1.2.0"', out.getvalue())

    def test_a_publish_uploads_and_prints_the_site_json_fields(self):
        code, output = self._main("--token", "7f3a9c2e51b04d88", "--annotate", *STORAGE_FLAGS)
        self.assertEqual(code, 0)
        self.assertIn(
            "::notice title=installer published::https://downloads.example.com/buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe",
            output,
        )
        self.assertIn(publish.sha256_of(self.installer), output)
        self.assertIn('"delivery_url":', output)
        self.assertIn("windows-app.html -> Stripe Payment Link", output)

    def test_the_url_changes_with_the_token_and_only_with_it(self):
        urls = []
        for token in ("aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb"):
            _, output = self._main("--token", token, *STORAGE_FLAGS)
            urls.append(re.search(r"published (\S+)", output).group(1))
        self.assertNotEqual(urls[0], urls[1], "a fixed URL is a URL anyone can pass around")
        self.assertTrue(all("buttcrack-setup-1.2.0-" in url for url in urls))

    def test_a_sidecar_that_disagrees_stops_the_publish(self):
        Path(f"{self.installer}.sha256").write_text("00" * 32 + "  buttcrack-setup-1.2.0.exe", encoding="utf-8")
        run = fake_upload()
        with (
            mock.patch.object(publish.subprocess, "run", run),
            mock.patch.object(publish.shutil, "which", return_value="/usr/bin/aws"),
            captured_stdout(),
            self.assertRaises(SystemExit) as caught,
        ):
            publish.main([str(self.installer), *STORAGE_FLAGS])
        self.assertIn("not the same build", str(caught.exception))
        run.assert_not_called()

    def test_a_matching_sidecar_is_uploaded_beside_it(self):
        Path(f"{self.installer}.sha256").write_text(
            f"{publish.sha256_of(self.installer)}  buttcrack-setup-1.2.0.exe", encoding="utf-8"
        )
        run = fake_upload()
        with mock.patch.object(publish.subprocess, "run", run), mock.patch.object(
            publish.shutil, "which", return_value="/usr/bin/aws"
        ), captured_stdout():
            publish.main([str(self.installer), "--token", "7f3a9c2e51b04d88", *STORAGE_FLAGS])
        self.assertEqual(run.call_count, 2)
        self.assertIn("buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe.sha256", " ".join(run.call_args_list[1].args[0]))

    def test_missing_storage_configuration_names_what_is_missing(self):
        with (
            mock.patch.dict(os.environ, dict.fromkeys(STORAGE_ENV, "")),
            captured_stdout(),
            self.assertRaises(SystemExit) as caught,
        ):
            publish.main([str(self.installer)])
        self.assertIn("BUTTCRACK_DELIVERY_BUCKET", str(caught.exception))

    def test_the_workflow_checks_for_the_same_names_this_script_reads(self):
        # The workflow's "are the storage secrets set?" step is a list of names,
        # and a name that drifts apart from this script fails at the upload
        # instead of before it.
        workflow = (ROOT / ".github" / "workflows" / "publish-installer.yml").read_text(encoding="utf-8")
        for name in STORAGE_ENV:
            with self.subTest(name=name):
                self.assertIn(name, workflow)
        self.assertIn("AWS_ACCESS_KEY_ID", workflow)

    def test_a_file_that_is_not_there_is_named(self):
        with captured_stdout(), self.assertRaises(SystemExit) as caught:
            publish.main([str(Path(self.tmp.name) / "nope.exe"), "--dry-run"])
        self.assertIn("no such file", str(caught.exception))

    def test_update_site_json_writes_the_values_when_a_real_publish_happens(self):
        site = Path(self.tmp.name) / "site.json"
        site.write_text(json.dumps({"_note": "hand-maintained", "windows_app": {"sku": "winapp"}}), encoding="utf-8")
        code, _ = self._main("--token", "7f3a9c2e51b04d88", "--update-site-json", str(site), *STORAGE_FLAGS)
        self.assertEqual(code, 0)
        document = json.loads(site.read_text(encoding="utf-8"))
        app = document["windows_app"]
        self.assertEqual(app["version"], "1.2.0")
        self.assertTrue(app["delivery_url"].endswith("-7f3a9c2e51b04d88.exe"))
        self.assertEqual(app["sha256"], publish.sha256_of(self.installer))
        self.assertEqual(app["size"], publish.human_megabytes(self.installer.stat().st_size))
        # Everything it does not own is left alone.
        self.assertEqual(app["sku"], "winapp")
        self.assertEqual(document["_note"], "hand-maintained")
        self.assertTrue(site.read_text(encoding="utf-8").endswith("\n"))

    def test_a_dry_run_does_not_touch_site_json(self):
        site = Path(self.tmp.name) / "site.json"
        original = json.dumps({"windows_app": {"delivery_url": "", "version": "1.2.0"}}, indent=2) + "\n"
        site.write_text(original, encoding="utf-8")
        with mock.patch.object(publish.subprocess, "run", fake_upload()), mock.patch.object(
            publish.shutil, "which"
        ), captured_stdout() as out:
            code = publish.main([str(self.installer), "--dry-run", "--update-site-json", str(site), *STORAGE_FLAGS])
        self.assertEqual(code, 0)
        self.assertEqual(site.read_text(encoding="utf-8"), original)
        self.assertIn("site.json", out.getvalue())


class VersionGuard(unittest.TestCase):
    """A stale installer must not be publishable as the current release.

    The workflow picks "the newest live artifact", and an ordinary push or
    pull-request run withdraws its own installer, so the newest live one is
    routinely the last *manually dispatched* build -- which can be a version
    behind the checkout doing the publishing. That published a 1.2.1 installer
    from a 1.2.2 tree and reported success, so the check now lives here, at the
    one point that touches production storage.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.installer = Path(self.tmp.name) / "buttcrack-setup-1.2.0.exe"
        self.installer.write_bytes(INSTALLER_BYTES)

    def _main(self, *args: str, checkout_version: str = "9.9.9") -> tuple[int, str]:
        with mock.patch.object(publish, "repo_version", return_value=checkout_version), mock.patch.object(
            publish.subprocess, "run", fake_upload()
        ), mock.patch.object(publish.shutil, "which", return_value="/usr/bin/aws"), captured_stdout() as out:
            code = publish.main([str(self.installer), *args])
        return code, out.getvalue()

    def test_repo_version_reads_the_checkout(self):
        version = publish.repo_version()
        self.assertRegex(version, r"^\d+(\.\d+)+$", "pyproject.toml has no usable version")

    def test_a_missing_pyproject_skips_the_check_rather_than_guessing(self):
        self.assertEqual(publish.repo_version(Path(self.tmp.name)), "")

    def test_a_stale_installer_is_refused(self):
        with self.assertRaises(SystemExit) as caught:
            self._main(*STORAGE_FLAGS)
        message = str(caught.exception)
        self.assertIn("1.2.0", message)
        self.assertIn("9.9.9", message)
        # The remedy has to be in the message: the cause is a build that was
        # never kept, and the fix is a dispatch, not an edit.
        self.assertIn("gh workflow run 'Release artifacts'", message)

    def test_the_refusal_happens_before_anything_is_uploaded(self):
        run = fake_upload()
        with mock.patch.object(publish, "repo_version", return_value="9.9.9"), mock.patch.object(
            publish.subprocess, "run", run
        ), mock.patch.object(publish.shutil, "which", return_value="/usr/bin/aws"), captured_stdout(), self.assertRaises(
            SystemExit
        ):
            publish.main([str(self.installer), *STORAGE_FLAGS])
        run.assert_not_called()

    def test_a_dry_run_is_refused_too(self):
        # A dry run that would publish the wrong version should say so now, not
        # after the real one has already put the file on the shelf.
        with self.assertRaises(SystemExit):
            self._main("--dry-run", *STORAGE_FLAGS)

    def test_the_override_still_publishes_an_older_version(self):
        code, output = self._main("--allow-version-mismatch", "--token", "7f3a9c2e51b04d88", *STORAGE_FLAGS)
        self.assertEqual(code, 0)
        self.assertIn("buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe", output)

    def test_a_matching_version_needs_no_override(self):
        code, output = self._main("--token", "7f3a9c2e51b04d88", *STORAGE_FLAGS, checkout_version="1.2.0")
        self.assertEqual(code, 0)
        self.assertIn("published https://downloads.example.com/buttcrack-setup-1.2.0-7f3a9c2e51b04d88.exe", output)


class SiteJsonEditing(unittest.TestCase):
    """`update_site_json` on its own: what it refuses, and what it preserves."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = Path(self.tmp.name) / "site.json"

    def test_a_second_run_reports_no_change_rather_than_rewriting(self):
        self.site.write_text(json.dumps({"windows_app": {}}), encoding="utf-8")
        first = publish.update_site_json(self.site, "https://d.example/a.exe", "1.2.0", 15_558_568, "ab" * 32)
        self.assertEqual(len(first), 4)
        second = publish.update_site_json(self.site, "https://d.example/a.exe", "1.2.0", 15_558_568, "ab" * 32)
        self.assertEqual(second, [])

    def test_an_empty_url_is_refused_because_the_page_would_link_nowhere(self):
        self.site.write_text("{}", encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            publish.update_site_json(self.site, "", "1.2.0", 1, "ab" * 32)
        self.assertIn("no delivery URL", str(caught.exception))

    def test_it_creates_the_windows_app_object_when_there_is_none(self):
        self.site.write_text(json.dumps({"site_name": "x"}), encoding="utf-8")
        publish.update_site_json(self.site, "https://d.example/a.exe", "1.2.0", 1, "ab" * 32)
        document = json.loads(self.site.read_text(encoding="utf-8"))
        self.assertEqual(document["site_name"], "x")
        self.assertEqual(document["windows_app"]["delivery_url"], "https://d.example/a.exe")

    def test_a_missing_file_is_named_not_created(self):
        with self.assertRaises(SystemExit) as caught:
            publish.update_site_json(self.site, "https://d.example/a.exe", "1.2.0", 1, "ab" * 32)
        self.assertIn("no such file", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
