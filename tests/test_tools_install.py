"""Download diagnostics and repeatable setup, without network access."""

import base64
import hashlib
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_reach import __version__
from agent_reach.runtime import tools
from agent_reach.runtime.result import TIMEOUT, ReachError


def _no_proxy(monkeypatch):
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(tools, "extend_path", lambda: None)


def test_package_version_matches_runtime_version():
    # The package metadata and --version must describe the same release.
    import re

    project = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    assert re.search(r'^version = "([^"]+)"', project, re.MULTILINE).group(1) == __version__


def test_pinned_artifact_provenance():
    from agent_reach.runtime import browser

    assert tools.OPENCLI_TARBALL_URL == "https://registry.npmjs.org/@jackwener/opencli/-/opencli-1.8.7.tgz"
    assert tools.OPENCLI_INTEGRITY == "sha512-2M+oPc70R1jNGzKzNrsm3fN4/gdvxCKlla7s9eaaTjkDjlzHpoZFN1YdV01A185kwCTN/ChOg+rbO4epO73c3w=="
    assert browser.OPENCLI_EXTENSION_URL == "https://github.com/jackwener/OpenCLI/releases/download/v1.8.7/opencli-extension-v1.0.23.zip"
    assert browser.OPENCLI_EXTENSION_SHA256 == "e3399db1e9dd626519a8719d638d3c3813494d1f030c1e96799e05ebe7ba5340"


def test_download_env_copies_system_proxy_for_both_install_stages(monkeypatch):
    _no_proxy(monkeypatch)
    monkeypatch.setattr(tools.urllib.request, "getproxies", lambda: {"https": "http://127.0.0.1:8899", "no": "localhost"})
    env = tools.install_env()
    assert env["HTTPS_PROXY"] == env["HTTP_PROXY"] == "http://127.0.0.1:8899"
    assert env["NO_PROXY"] == "localhost"
    assert "HTTPS_PROXY" not in os.environ


@pytest.mark.parametrize("key", ["https_proxy", "HTTP_PROXY", "ALL_PROXY"])
def test_explicit_proxy_is_kept_without_consulting_system(monkeypatch, key):
    _no_proxy(monkeypatch)
    monkeypatch.setenv(key, "http://127.0.0.1:7788")
    monkeypatch.setattr(tools.urllib.request, "getproxies", lambda: pytest.fail("explicit proxy must win"))
    env = tools.install_env()
    assert env["HTTPS_PROXY"] == env["HTTP_PROXY"] == "http://127.0.0.1:7788"


def test_npm_timeout_names_stage_and_redacts_proxy(monkeypatch):
    monkeypatch.setattr(tools, "_install_env", lambda: {"HTTPS_PROXY": "http://user:secret@127.0.0.1:7788"})

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(tools.subprocess, "run", timeout)
    with pytest.raises(ReachError) as err:
        tools._run(["npm", "install"], timeout=1, stage="opencli:npm_packages")
    assert err.value.code == TIMEOUT
    assert "opencli:npm_packages" in err.value.message
    assert "configured proxy" in err.value.hint
    assert "secret" not in str(err.value) + err.value.hint


def test_install_failure_scrubs_upstream_url_credentials(monkeypatch):
    monkeypatch.setattr(tools, "_install_env", lambda: {})
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=1, stdout="", stderr="Could not connect to https://user:secret@example.com/download?token=abc"))
    with pytest.raises(ReachError) as err:
        tools._run(["npm", "install", "opencli.tgz"], stage="opencli:npm_packages")
    assert "secret" not in str(err.value)
    assert "token=abc" not in str(err.value)
    assert "direct network" in err.value.hint


@pytest.mark.parametrize("scope", ["private", "owned-global", "user-global"])
def test_opencli_verifies_local_tarball_before_npm_without_hooks(monkeypatch, tmp_path, scope):
    payload = b"test tarball"
    digest = "sha512-" + base64.b64encode(hashlib.sha512(payload).digest()).decode("ascii")
    monkeypatch.setattr(tools, "OPENCLI_INTEGRITY", digest)
    calls = []
    downloads = []
    monkeypatch.setattr(tools, "_npm_cmd", lambda: "npm")
    monkeypatch.setattr(tools, "tool_dir", lambda name: tmp_path / name)
    def download(url, dest):
        downloads.append(url)
        dest.write_bytes(payload)
    def install(argv, **kwargs):
        assert Path(argv[-1]).read_bytes() == payload
        calls.append(argv)
        return ""
    monkeypatch.setattr(tools, "_download", download)
    monkeypatch.setattr(tools, "_run", install)
    prefix = tmp_path / "npm"
    tools._install_npm(tools.TOOLS["opencli"], global_prefix=prefix if scope == "owned-global" else None,
                       system_global=scope == "user-global")
    assert downloads == [tools.OPENCLI_TARBALL_URL]
    assert len(calls) == 1 and "--ignore-scripts" in calls[0]
    assert calls[0][-1].endswith("opencli-1.8.7.tgz")
    assert ("-g" in calls[0]) == (scope != "private")
    if scope == "owned-global":
        assert calls[0][calls[0].index("--prefix") + 1] == str(prefix)
    assert not Path(calls[0][-1]).exists()
    assert not tools.allowed(tools.TOOLS["opencli"], "1.8.8")


def test_opencli_hash_mismatch_deletes_archive_without_running_npm(monkeypatch):
    archives = []
    monkeypatch.setattr(tools, "_npm_cmd", lambda: "npm")
    def download(url, dest):
        archives.append(dest)
        dest.write_bytes(b"corrupted")
    monkeypatch.setattr(tools, "_download", download)
    monkeypatch.setattr(tools, "_run", lambda *a, **kw: pytest.fail("ran npm with unverified tarball"))
    with pytest.raises(ReachError, match="SHA-512 mismatch"):
        tools._install_npm(tools.TOOLS["opencli"])
    assert not archives[0].exists()


@pytest.mark.parametrize("name", ["node", "uv", "ffmpeg", "opencli"])
def test_missing_prerequisites_need_setup_without_download_or_install(monkeypatch, name):
    monkeypatch.setattr(tools.shutil, "which", lambda command: None)
    monkeypatch.setattr(tools, "_download", lambda *a: pytest.fail("downloaded prerequisite"))
    monkeypatch.setattr(tools, "_install", lambda *a, **kw: pytest.fail("installed prerequisite"))
    with pytest.raises(ReachError) as error:
        tools.ensure(name)
    assert error.value.code == "NEED_SETUP"
    assert "brew install" in error.value.hint


def test_node_requires_npm_as_well_as_node(monkeypatch):
    monkeypatch.setattr(tools.shutil, "which", lambda command: "/usr/bin/node" if command == "node" else None)
    monkeypatch.setattr(tools, "_download", lambda *a: pytest.fail("downloaded npm"))
    with pytest.raises(ReachError) as error:
        tools.ensure("opencli")
    assert error.value.code == "NEED_SETUP" and "npm" in error.value.message
