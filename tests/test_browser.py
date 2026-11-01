"""System Chrome, pinned extension and cookie lifecycle."""

import hashlib
import json
import os
import shutil
import stat
import subprocess
import threading
import zipfile

import pytest

from agent_reach.runtime import browser, cdp


@pytest.fixture
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(browser, "is_running", lambda: False)
    return tmp_path


@pytest.fixture
def mac_chrome(home, monkeypatch):
    monkeypatch.setenv("HOME", str(home.resolve()))
    executable = home.resolve() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(browser.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(browser, "_system_chrome", lambda: str(executable))
    return executable


def _zip(path, files):
    with zipfile.ZipFile(path, "w") as zf:
        for name, (data, mode) in files.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (0o100000 | mode) << 16
            zf.writestr(info, data)
    return path


def test_domain_match_is_exact_or_subdomain():
    assert cdp.domain_matches(".reddit.com", "reddit.com")
    assert cdp.domain_matches("www.reddit.com", "reddit.com")
    assert not cdp.domain_matches("notreddit.com", "reddit.com")


@pytest.mark.parametrize('endpoint', [
    'ws://external.example:9222/devtools/browser/id',
    'ws://127.0.0.1:9999/devtools/browser/id',
    'ws://user:pass@127.0.0.1:9222/devtools/browser/id',
    'wss://127.0.0.1:9222/devtools/browser/id',
])
def test_cdp_rejects_external_or_wrong_port_before_transmitting_cookies(monkeypatch, endpoint):
    from agent_reach.runtime.result import ReachError
    monkeypatch.setattr(cdp, '_json', lambda path: {'webSocketDebuggerUrl': endpoint})
    monkeypatch.setattr(cdp.socket, 'create_connection', lambda *args, **kwargs: pytest.fail('opened socket'))
    with pytest.raises(ReachError, match='loopback endpoint'):
        cdp.call('Storage.setCookies', {'cookies': [{'value': 'private-cookie'}]})


def test_extension_installs_at_a_stable_path_from_the_tested_release(home, monkeypatch, tmp_path):
    manifest = lambda v: (json.dumps({"manifest_version": 3, "version": v}), 0o644)  # noqa: E731
    v1 = _zip(tmp_path / "v1.zip", {"manifest.json": manifest("1.0.23"), "dist/background.js": ("//", 0o644)})
    digest = hashlib.sha256(v1.read_bytes()).hexdigest()
    monkeypatch.setattr(browser, "OPENCLI_EXTENSION_SHA256", digest)
    downloads = []
    def download(url, dest, timeout=60.0):
        downloads.append(url)
        shutil.copy(v1, dest)
    monkeypatch.setattr(browser, "_download", download)
    from agent_reach.runtime.tools import TOOLS
    assert browser.OPENCLI_RELEASE_TAG == "v" + TOOLS["opencli"].tested == "v1.8.7"
    assert browser.OPENCLI_EXTENSION_URL.endswith("/v1.8.7/opencli-extension-v1.0.23.zip")

    assert browser.refresh_extension() == {"version": "1.0.23", "updated": True}
    assert (browser.extension_dir() / "dist" / "background.js").is_file()
    assert browser.refresh_extension() == {"version": "1.0.23", "updated": False}

    assert browser.refresh_extension(upgrade=True) == {"version": "1.0.23", "updated": True}
    assert browser._load_state()["extension_release"] == "v1.8.7"
    assert browser._load_state()["extension_sha256"] == digest
    assert downloads == [browser.OPENCLI_EXTENSION_URL] * 2


def test_extension_refresh_offline_keeps_the_current_copy(home, monkeypatch):
    browser.extension_dir().mkdir(parents=True)
    (browser.extension_dir() / "manifest.json").write_text(json.dumps({"version": "1.0.0"}))
    browser.update_state(extension_sha256=browser.OPENCLI_EXTENSION_SHA256)

    monkeypatch.setattr(browser, "_download", lambda *args: pytest.fail("downloaded verified extension"))
    assert browser.refresh_extension() == {"version": "1.0.0", "updated": False}


def test_unpinned_extension_cannot_be_reused_offline(home, monkeypatch):
    browser.extension_dir().mkdir(parents=True)
    (browser.extension_dir() / "manifest.json").write_text(json.dumps({"version": "9.9.9"}))
    browser.update_state(extension_release=browser.OPENCLI_RELEASE_TAG, extension_sha256="old-hash")
    monkeypatch.setattr(browser, "_download", lambda *args: (_ for _ in ()).throw(OSError("offline")))
    from agent_reach.runtime.result import ReachError
    with pytest.raises(ReachError, match="could not install"):
        browser.refresh_extension()


def test_ensure_browser_uses_system_chrome_not_a_recorded_executable(home, monkeypatch):
    binary = home / "untrusted-browser"
    binary.touch()
    browser.update_state(executable=str(binary))
    monkeypatch.setattr(browser, "_system_chrome", lambda: "/system/chrome")
    monkeypatch.setattr(browser.platform, "system", lambda: "Linux")
    assert browser.ensure_chrome() == "/system/chrome"
    assert browser._load_state()["backend"] == "chrome"


def test_missing_chrome_requires_manual_install_without_download(home, monkeypatch):
    from agent_reach.runtime.result import ReachError
    monkeypatch.setattr(browser, "_system_chrome", lambda: None)
    monkeypatch.setattr(browser, "_download", lambda *args: pytest.fail("downloaded browser"))
    with pytest.raises(ReachError) as error:
        browser.ensure_chrome()
    assert error.value.code == "NEED_SETUP" and "google.com/chrome" in error.value.hint


@pytest.mark.parametrize("identifier,team", [("com.google.Chrome", "OTHER"),
                                            ("com.google.Chrome", ""),
                                            ("com.google.OtherApp", "EQHXZ8M8AV")])
def test_macos_signature_failure_refuses_launch(home, mac_chrome, monkeypatch, identifier, team):
    from types import SimpleNamespace

    from agent_reach.runtime.result import ReachError
    def codesign(argv, **kwargs):
        requirement = next(arg for arg in argv if arg.startswith("-R="))
        assert 'identifier "com.google.Chrome"' in requirement
        assert 'certificate leaf[subject.OU] = "EQHXZ8M8AV"' in requirement
        return SimpleNamespace(returncode=int(identifier != "com.google.Chrome" or team != "EQHXZ8M8AV"))
    monkeypatch.setattr(browser.subprocess, "run", codesign)
    monkeypatch.setattr(browser.subprocess, "Popen", lambda *a, **kw: pytest.fail("launched unsigned browser"))
    with pytest.raises(ReachError) as error:
        browser._launch("about:blank")
    assert error.value.code == "NEED_SETUP"
    assert "not launched" in error.value.message


def test_macos_signature_requires_strict_verification_and_google_team(home, mac_chrome, monkeypatch):
    from types import SimpleNamespace

    calls = []
    executable = str(mac_chrome)
    def codesign(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="", stderr="TeamIdentifier=EQHXZ8M8AV\n")
    monkeypatch.setattr(browser.subprocess, "run", codesign)
    assert browser.ensure_chrome() == executable
    assert calls == [["/usr/bin/codesign", "--verify", "--deep",
                      '-R=identifier "com.google.Chrome" and anchor apple generic and certificate leaf[subject.OU] = "EQHXZ8M8AV"',
                      str(mac_chrome.parents[2])]]


@pytest.mark.parametrize("failure", [OSError("codesign unavailable"), subprocess.TimeoutExpired("codesign", 30)])
def test_macos_unavailable_signature_check_refuses_launch(home, mac_chrome, monkeypatch, failure):
    from agent_reach.runtime.result import ReachError

    def codesign(*args, **kwargs):
        raise failure
    monkeypatch.setattr(browser.subprocess, "run", codesign)
    monkeypatch.setattr(browser.subprocess, "Popen", lambda *a, **kw: pytest.fail("launched unverified browser"))
    with pytest.raises(ReachError) as error:
        browser._launch("about:blank")
    assert error.value.code == "NEED_SETUP"


@pytest.mark.parametrize("component", ["executable", "app", "applications"])
def test_macos_rejects_symlink_path_components(mac_chrome, monkeypatch, component):
    from agent_reach.runtime.result import ReachError

    path = {"executable": mac_chrome, "app": mac_chrome.parents[2],
            "applications": mac_chrome.parents[3]}[component]
    moved = path.with_name(path.name + "-moved")
    path.rename(moved)
    path.symlink_to(moved, target_is_directory=component != "executable")
    monkeypatch.setattr(browser.subprocess, "run", lambda *args, **kwargs: pytest.fail("verified symlink"))
    with pytest.raises(ReachError, match="non-symlink system Google Chrome path"):
        browser.verify_chrome(str(mac_chrome))


def test_macos_rejects_other_executable_inside_chrome_bundle(mac_chrome, monkeypatch):
    from agent_reach.runtime.result import ReachError

    other = mac_chrome.with_name("Other App")
    other.touch()
    monkeypatch.setattr(browser.subprocess, "run", lambda *args, **kwargs: pytest.fail("verified other executable"))
    with pytest.raises(ReachError, match="system Google Chrome path"):
        browser.verify_chrome(str(other))


@pytest.mark.parametrize("change", ["signature", "inode", "inode_between", "device"])
def test_watcher_reverifies_before_popen_and_rejects_changes(mac_chrome, monkeypatch, change):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from agent_reach.runtime import browser_watcher
    from agent_reach.runtime.result import ReachError

    calls = []
    def codesign(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 2 and change == "inode":
            replacement = mac_chrome.with_name("replacement")
            replacement.touch()
            os.replace(replacement, mac_chrome)
        return SimpleNamespace(returncode=int(len(calls) == 2 and change == "signature"))
    monkeypatch.setattr(browser.subprocess, "run", codesign)
    if change == "inode_between":
        original_verify = browser.verify_chrome
        def verify(executable):
            if calls:
                replacement = mac_chrome.with_name("replacement")
                replacement.touch()
                os.replace(replacement, mac_chrome)
            return original_verify(executable)
        monkeypatch.setattr(browser, "verify_chrome", verify)
    if change == "device":
        original_stat = type(mac_chrome).stat
        def changed_stat(path, *args, **kwargs):
            result = original_stat(path, *args, **kwargs)
            if path == mac_chrome and len(calls) >= 2:
                return SimpleNamespace(st_mode=result.st_mode, st_dev=result.st_dev + 1, st_ino=result.st_ino)
            return result
        monkeypatch.setattr(type(mac_chrome), "stat", changed_stat)
    popen = Mock()
    monkeypatch.setattr(browser_watcher.subprocess, "Popen", popen)
    with pytest.raises(ReachError, match="signature verification failed|executable changed"):
        browser_watcher._launch_with_pipe(str(mac_chrome), "about:blank")
    assert len(calls) == 2
    popen.assert_not_called()


@pytest.mark.parametrize("system", ["Darwin", "Linux", "Windows"])
@pytest.mark.parametrize("entry,mode", [("../escaped", stat.S_IFREG),
                                       ("nested/../../escaped", stat.S_IFREG),
                                       ("absolute", stat.S_IFREG),
                                       ("C:/escaped", stat.S_IFREG),
                                       ("..\\escaped", stat.S_IFREG),
                                       ("link", stat.S_IFLNK),
                                       ("pipe", stat.S_IFIFO),
                                       ("device", stat.S_IFCHR)])
def test_unzip_checks_every_entry_before_extracting(home, monkeypatch, system, entry, mode):
    archive = home / "unsafe.zip"
    outside = home / "escaped"
    dest = home / "unpacked"
    dest.mkdir()
    if entry == "absolute":
        entry = str(outside)
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", '{"version":"1.0.23"}')
        info = zipfile.ZipInfo(entry)
        info.external_attr = (mode | 0o644) << 16
        zf.writestr(info, str(outside))
    monkeypatch.setattr(browser.platform, "system", lambda: system)
    monkeypatch.setattr(browser.subprocess, "run", lambda *args, **kwargs: pytest.fail("used external unzip"))
    with pytest.raises(ValueError, match="unsafe"):
        browser._unzip(archive, dest)
    assert not outside.exists()
    assert list(dest.iterdir()) == []


@pytest.mark.parametrize("symlink", [False, True])
def test_unsafe_extension_never_reaches_loading(home, monkeypatch, symlink):
    from unittest.mock import Mock

    from agent_reach.runtime import browser_watcher
    from agent_reach.runtime.result import ReachError

    outside = home / "escaped"
    archive = home / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", '{"version":"1.0.23"}')
        info = zipfile.ZipInfo("link" if symlink else str(outside))
        info.external_attr = ((stat.S_IFLNK if symlink else stat.S_IFREG) | 0o644) << 16
        zf.writestr(info, str(outside))
    monkeypatch.setattr(browser, "OPENCLI_EXTENSION_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    monkeypatch.setattr(browser, "_download", lambda url, dest: shutil.copy(archive, dest))
    monkeypatch.setattr(browser_watcher.bridge, "start", lambda: None)
    load = Mock()
    launch = Mock()
    monkeypatch.setattr(browser_watcher, "_load_extension", load)
    monkeypatch.setattr(browser_watcher, "_launch_with_pipe", launch)
    with pytest.raises(ReachError, match="unsafe"):
        browser_watcher.watch(launch="about:blank", chrome="unused")
    assert not outside.exists()
    assert not browser.extension_dir().exists()
    assert not list(browser.browser_root().glob(".extension-*"))
    load.assert_not_called()
    launch.assert_not_called()


def test_watcher_refuses_an_extension_without_a_recorded_verified_hash(home):
    from unittest.mock import Mock

    from agent_reach.runtime import browser_watcher
    from agent_reach.runtime.result import ReachError

    browser.extension_dir().mkdir(parents=True)
    (browser.extension_dir() / "manifest.json").write_text('{"version":"1.0.23"}')
    connection = Mock()
    with pytest.raises(ReachError, match="verified hash"):
        browser_watcher._load_extension(connection)
    connection.call.assert_not_called()


@pytest.mark.parametrize("existing", [False, True])
def test_extension_hash_mismatch_refuses_unpack_and_reuse(home, monkeypatch, existing):
    from agent_reach.runtime.result import ReachError
    if existing:
        browser.extension_dir().mkdir(parents=True)
        (browser.extension_dir() / "manifest.json").write_text('{"version":"1.0.23"}')
        browser.update_state(extension_sha256=browser.OPENCLI_EXTENSION_SHA256)
    archives = []
    def download(url, dest):
        archives.append(dest)
        dest.write_bytes(b"corrupted")
    monkeypatch.setattr(browser, "_download", download)
    monkeypatch.setattr(browser, "_unzip", lambda *args: pytest.fail("unpacked unverified zip"))
    with pytest.raises(ReachError, match="SHA-256 mismatch"):
        browser.refresh_extension(upgrade=True)
    assert not archives[0].exists()
    assert bool(browser.extension_version()) == existing


def test_clear_site_expires_only_that_sites_cookies(home, monkeypatch):
    jar = [
        {"name": "a", "value": "1", "domain": ".reddit.com", "path": "/"},
        {"name": "b", "value": "2", "domain": "www.reddit.com", "path": "/"},
        {"name": "c", "value": "3", "domain": "notreddit.com", "path": "/"},
    ]

    def fake_call(method, params=None, **kwargs):
        if method == "Storage.getCookies":
            return {"cookies": list(jar)}
        if method == "Storage.clearDataForOrigin":
            assert "reddit.com" in params["origin"]
            return {}
        if method == "Storage.setCookies":
            for c in params["cookies"]:
                assert c["expires"] == 1
                jar[:] = [j for j in jar if (j["name"], j["domain"]) != (c["name"], c["domain"])]
            return {}
        raise AssertionError(method)

    browser.profile_dir().mkdir(parents=True)
    monkeypatch.setattr(browser, "ensure_running", lambda context=None: None)
    monkeypatch.setattr(cdp, "call", fake_call)
    monkeypatch.setattr(cdp, "_json", lambda *a: [])
    assert browser.clear_site(["reddit.com"]) == 2
    assert [c["name"] for c in jar] == ["c"]


def test_clear_site_never_opens_a_browser_that_was_never_used(home, monkeypatch):
    monkeypatch.setattr(browser, "ensure_running", lambda context=None: pytest.fail("opened the browser"))
    assert browser.clear_site(["reddit.com"]) == 0


def test_delete_profile_removes_the_browser_folder(home, monkeypatch):
    monkeypatch.setattr(browser, "stop", lambda timeout=10.0: True)
    browser.profile_dir().mkdir(parents=True)
    browser.touch()
    from agent_reach.runtime import state
    for path in (browser.profile_dir(), browser._last_used_path()):
        state.remember_path(path, "test browser")
    assert browser.delete_profile() is True
    assert not browser.browser_root().exists()
    assert browser.delete_profile() is False


def test_pipe_connection_matches_replies_and_notices_close():
    to_chrome_r, to_chrome_w = os.pipe()
    from_chrome_r, from_chrome_w = os.pipe()

    def fake_chrome():  # echoes each NUL-delimited command back as a reply, with an event first
        buf = b""
        while True:
            chunk = os.read(to_chrome_r, 4096)
            if not chunk:
                break
            buf += chunk
            while b"\0" in buf:
                raw, buf = buf.split(b"\0", 1)
                msg = json.loads(raw)
                os.write(from_chrome_w, json.dumps({"method": "Some.event"}).encode() + b"\0")
                os.write(from_chrome_w, json.dumps({"id": msg["id"], "result": {"id": msg["params"]["path"]}}).encode() + b"\0")
        os.close(from_chrome_w)  # Chrome exits when its input pipe closes
        os.close(to_chrome_r)

    t = threading.Thread(target=fake_chrome)
    t.start()
    conn = cdp.PipeConnection(to_chrome_w, from_chrome_r)
    assert conn.call("Extensions.loadUnpacked", {"path": "/ext"}) == {"id": 1, "result": {"id": "/ext"}}
    assert conn.call("Extensions.loadUnpacked", {"path": "/two"})["result"] == {"id": "/two"}
    conn.close()
    t.join(5)
    assert conn.closed.is_set()
    assert "error" in conn.call("Browser.close", timeout=1)


def test_chrome_queries_are_headless_and_human_login_is_visible():
    assert '--headless=new' in browser.chrome_argv('/chrome','about:blank',pipe=False)
    assert '--headless=new' not in browser.chrome_argv('/chrome','about:blank',pipe=False,headless=False)


def test_restore_failure_preserves_the_original_snapshot(home, monkeypatch):
    from agent_reach.runtime.result import ReachError
    browser.browser_root().mkdir(parents=True)
    path=browser.browser_root()/'session.json'
    original=json.dumps({'cookies':[{'name':'sid','value':'saved','domain':'example.test'}]})
    path.write_text(original)
    monkeypatch.setattr(cdp,'call',lambda method,*a,**k:{'cookies':[]}if method=='Storage.getCookies'else None)
    with pytest.raises(ReachError,match='retained'):
        browser.restore_session()
    assert path.read_text()==original
