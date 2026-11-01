"""Upstream tools and machine prerequisites Agent Reach installs, at their declared versions.

Tools with `tested` are installed at that version, and `update` keeps them there. Each tool may set `floor`
(oldest version we accept) and `exclude` (known-bad versions, added in a release when an upstream breaks);
tools without `tested` use the newest version inside those limits. Existing user tools are not silently downgraded.
state.json records the version actually installed.

Kinds:
- npm: private, under ~/.agent-reach/tools/<name>/ (npm prefix).
  The user's own copy, if any, is untouched unless an upgrade is approved.
- singleton (npm): can only exist once per machine (OpenCLI owns a fixed daemon
  port and a Chrome extension). A user copy inside the limits is used as is; an
  out-of-limits user copy is upgraded only with explicit consent; when missing
  it is installed into ~/.agent-reach/tools/npm-global/ and recorded as ours.
- prerequisites (node, uv, ffmpeg, chrome): must be installed by the user.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from . import state
from .result import NEED_SETUP, TIMEOUT, UPSTREAM_BROKEN, ReachError, _clean

OURS = "agent-reach"
OPENCLI_TARBALL_URL = "https://registry.npmjs.org/@jackwener/opencli/-/opencli-1.8.7.tgz"
OPENCLI_INTEGRITY = "sha512-2M+oPc70R1jNGzKzNrsm3fN4/gdvxCKlla7s9eaaTjkDjlzHpoZFN1YdV01A185kwCTN/ChOg+rbO4epO73c3w=="


@dataclass(frozen=True)
class Tool:
    name: str
    kind: str                       # "pip" | "npm" | "ffmpeg" | "node" | "uv" | "chrome"
    package: str                    # pip requirement / npm package name ("" for prerequisites)
    commands: Tuple[str, ...]       # executables it provides
    singleton: bool = False
    floor: str = ""                 # oldest acceptable version
    exclude: Tuple[str, ...] = ()   # known-bad versions
    tested: str = ""                # reproducible default for newly installed tools
    needs: Tuple[str, ...] = ()     # tools that must be installed first


TOOLS: Dict[str, Tool] = {
    t.name: t
    for t in (
        Tool("opencli", "npm", "@jackwener/opencli", ("opencli",), singleton=True, floor="1.8.7", exclude=("1.8.8",), tested="1.8.7", needs=("node",)),
        Tool("ffmpeg", "ffmpeg", "", ("ffmpeg",)),
        Tool("node", "node", "", ("node", "npm", "npx")),
        Tool("uv", "uv", "", ("uv", "uvx")),
        Tool("chrome", "chrome", "", ()),
    )
}

#: Command name → tool, for resolving executables.
_BY_COMMAND = {c: t for t in TOOLS.values() for c in t.commands}

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_WIN = sys.platform == "win32"


def tools_root() -> Path:
    return state.root() / "tools"


def tool_dir(name: str) -> Path:
    return tools_root() / name


def npm_global_dir() -> Path:
    """Prefix for singletons we install (`npm -g --prefix`): no admin rights needed."""
    return tools_root() / "npm-global"


def _exe(name: str) -> str:
    return name + (".exe" if _WIN else "")


def _node_bin_dir() -> Path:
    base = tool_dir("node") / "current"
    return base if _WIN else base / "bin"


def _npm_global_bin() -> Path:
    return npm_global_dir() if _WIN else npm_global_dir() / "bin"


def _private_bin(tool: Tool, command: str) -> Path:
    base = tool_dir(tool.name)
    if tool.kind == "pip":
        return base / "venv" / ("Scripts" if _WIN else "bin") / _exe(command)
    if tool.kind == "npm":
        return base / "node_modules" / ".bin" / (command + (".cmd" if _WIN else ""))
    if tool.kind == "node":
        return _node_bin_dir() / (command + (".cmd" if _WIN and command != "node" else ".exe" if _WIN else ""))
    if tool.kind in ("uv", "ffmpeg"):
        return base / "bin" / _exe(command)
    return base / command


def bin_dirs() -> List[Path]:
    """Private npm bin folder; machine prerequisites must be on the user's PATH."""
    dirs = [_npm_global_bin()]
    return [d for d in dirs if d.is_dir()]


def extend_path() -> None:
    """Append our private bin folders to PATH (system copies still win), so that
    upstream scripts find node/uvx/ffmpeg and children we start inherit them."""
    parts = os.environ.get("PATH", "").split(os.pathsep)
    extra = [str(d) for d in bin_dirs() if str(d) not in parts]
    if extra:
        os.environ["PATH"] = os.pathsep.join([p for p in parts if p] + extra)


def resolve(command: str) -> Optional[str]:
    """Absolute path for `command`: our private copy first, then the user's PATH."""
    tool = _BY_COMMAND.get(command)
    if tool and not tool.singleton and tool.kind not in ("node", "uv", "ffmpeg"):
        private = _private_bin(tool, command)
        if private.exists():
            return str(private)
    found = shutil.which(command)
    if found or not tool or not tool.singleton:
        return found
    ours = _npm_global_bin() / (command + (".cmd" if _WIN else ""))
    return str(ours) if ours.exists() else None


def ffmpeg_path() -> Optional[str]:
    return resolve("ffmpeg")


def present(name: str) -> bool:
    """Is the tool usable right now (ours or the system's)? Offline."""
    tool = TOOLS[name]
    if tool.kind == "chrome":
        from .browser import chrome_binary

        return chrome_binary() is not None
    return all(resolve(c) for c in tool.commands)


# ── versions ──

def _version_tuple(text: str) -> tuple:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in m.groups()) if m else ()


def allowed(tool: Tool, version: Optional[str]) -> bool:
    v = _version_tuple(version or "")
    if not v:
        return False
    if tool.floor and v < _version_tuple(tool.floor):
        return False
    return not any(v == _version_tuple(x) for x in tool.exclude)


def install_spec(tool: Tool) -> str:
    """Tested version when known; otherwise the floor/exclude range."""
    if tool.tested:
        return tool.package + ("==" if tool.kind in ("pip", "ffmpeg") else "@") + tool.tested
    if tool.kind in ("pip", "ffmpeg"):
        cons = ([f">={tool.floor}"] if tool.floor else []) + [f"!={x}" for x in tool.exclude]
        if " @ " in tool.package or not cons:
            return tool.package
        return tool.package + ",".join(cons)
    # npm: a range made of the gaps between excluded versions
    bad = sorted(set(tool.exclude), key=_version_tuple)
    lower, parts = f">={tool.floor}" if tool.floor else ">=0.0.0", []
    for x in bad:
        parts.append(f"{lower} <{x}")
        lower = f">{x}"
    parts.append(lower)
    rng = " || ".join(parts)
    return tool.package if rng == ">=0.0.0" else f"{tool.package}@{rng}"


def _dist_name(tool: Tool) -> str:
    return re.split(r"[\s@<>=!~\[;]", tool.package, maxsplit=1)[0]


def _pip_version(tool: Tool) -> Optional[str]:
    want = re.sub(r"[-_.]+", "_", _dist_name(tool)).lower()
    venv = tool_dir(tool.name) / "venv"
    sites = [venv / "Lib" / "site-packages"] if _WIN else sorted((venv / "lib").glob("python*/site-packages"))
    for site in sites:
        for d in site.glob("*.dist-info"):
            name, _, ver = d.name[: -len(".dist-info")].partition("-")
            if re.sub(r"[-_.]+", "_", name).lower() == want:
                return ver
    return None


def _npm_version(prefix: Path, package: str) -> Optional[str]:
    """Version from package.json under a local prefix (node_modules) or an -g prefix (lib/node_modules)."""
    for base in (prefix / "node_modules", prefix / "lib" / "node_modules"):
        try:
            return json.loads((base / package / "package.json").read_text("utf-8")).get("version")
        except (OSError, ValueError):
            continue
    return None


def _command_version(exe: Optional[str]) -> Optional[str]:
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"\d+\.\d+\.\d+", out.stdout + out.stderr)
    return m.group(0) if m else None


def installed_version(tool: Tool) -> Optional[str]:
    """Version of the copy `resolve` would use (singletons: whichever is on PATH)."""
    return _command_version(resolve(tool.commands[0]))


def _private_version(tool: Tool) -> Optional[str]:
    if tool.kind in ("pip", "ffmpeg"):
        return _pip_version(tool)
    if tool.kind == "npm":
        return _npm_version(tool_dir(tool.name), tool.package)
    return _command_version(str(_private_bin(tool, tool.commands[0])))


# ── installing ──

def install_env() -> dict:
    """One proxy environment for package and browser-binary downloads.

    Explicit shell proxies win. A protocol with no explicit value inherits the
    other protocol, or ALL_PROXY; only then do we consult the OS proxy. This
    returns a copy and never changes the user's proxy settings.
    """
    extend_path()
    env = dict(os.environ)
    cache = state.root() / "cache" / "downloads"
    if cache.exists() and not state.owned_path(cache):
        raise ReachError(NEED_SETUP, "Unrecorded download cache left untouched; choose a clean Reach directory")
    from agent_reach.utils.paths import make_private_dir

    make_private_dir(cache)
    state.remember_path(cache, "download caches")
    # Older releases could claim an already existing cache parent. Preserve it;
    # only the newly created, dedicated child is eligible for recursive cleanup.
    state.mutate(lambda data: data.get("owned_paths", {}).pop("cache", None))
    env.update(PIP_CACHE_DIR=str(cache / "pip"), UV_CACHE_DIR=str(cache / "uv"),
               npm_config_cache=str(cache / "npm"), XDG_CACHE_HOME=str(cache))
    https = env.get("HTTPS_PROXY") or env.get("https_proxy")
    http = env.get("HTTP_PROXY") or env.get("http_proxy")
    all_proxy = env.get("ALL_PROXY") or env.get("all_proxy")
    if not (https or http or all_proxy):
        found = urllib.request.getproxies()
        https, http = found.get("https"), found.get("http")
        if found.get("no") and not (env.get("NO_PROXY") or env.get("no_proxy")):
            env["NO_PROXY"] = found["no"]
    proxy = https or http or all_proxy
    if proxy:
        env.setdefault("HTTPS_PROXY", https or proxy)
        env.setdefault("HTTP_PROXY", http or proxy)
    return env


def _install_env() -> dict:
    """Compatibility for installers that used the private helper."""
    return install_env()


def _run(argv, timeout: float = 600, env: Optional[dict] = None, *, stage: str = "tool_install") -> str:
    run_env = _install_env()
    run_env.update(env or {})
    proxy_mode = "configured proxy" if any(run_env.get(k) for k in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy")) else "direct network"
    hint = f"Stage: {stage}; network: {proxy_mode}. Check this download path, then rerun setup; installed packages and download caches are reused."
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=run_env)
    except FileNotFoundError:
        raise ReachError(NEED_SETUP, f"{Path(argv[0]).name} is not installed") from None
    except subprocess.TimeoutExpired:
        raise ReachError(TIMEOUT, f"{stage} timed out after {timeout:.0f}s", hint=hint) from None
    if proc.returncode != 0:
        output = proc.stderr or proc.stdout
        last = next((ln for ln in reversed(output.splitlines()) if ln.strip()), "")
        raise ReachError(UPSTREAM_BROKEN, f"{stage} failed: {_clean(last) or 'no error output'}", hint=hint)
    return proc.stdout


def _download(url: str, dest: Path, timeout: float = 600) -> None:
    proxy = _install_env().get("HTTPS_PROXY")
    handlers = [urllib.request.ProxyHandler({"https": proxy, "http": proxy})] if proxy else []
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": "agent-reach"})
    try:
        with opener.open(req, timeout=timeout) as resp, open(dest, "wb") as fh:
            shutil.copyfileobj(resp, fh, 1024 * 1024)
    except OSError as exc:
        raise ReachError(UPSTREAM_BROKEN, _clean(f"download failed: {url}: {exc}")) from None


def _npm_cmd() -> str:
    npm = resolve("npm")
    if not npm:
        raise ReachError(NEED_SETUP, "npm is not installed; automatic downloads are disabled",
                         hint="Install Node.js and npm yourself (macOS: brew install node), then rerun setup.")
    return npm


def _install_npm(tool: Tool, *, global_prefix: Optional[Path] = None, system_global: bool = False) -> None:
    npm = _npm_cmd()
    if tool.name != "opencli":
        raise ReachError(NEED_SETUP, f"No pinned npm artifact for {tool.name}; installation refused")
    from agent_reach.utils.paths import private_temporary_directory

    with private_temporary_directory(prefix="opencli-") as tmp:
        archive = Path(tmp) / "opencli-1.8.7.tgz"
        _download(OPENCLI_TARBALL_URL, archive)
        integrity = "sha512-" + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode("ascii")
        if integrity != OPENCLI_INTEGRITY:
            archive.unlink()
            raise ReachError(UPSTREAM_BROKEN, "OpenCLI SHA-512 mismatch; archive deleted and installation refused")
        argv = [npm, "install", "--ignore-scripts", "--no-fund", "--no-audit"]
        if system_global:
            argv += ["-g"]
        elif global_prefix is not None:
            global_prefix.mkdir(parents=True, exist_ok=True)
            argv += ["-g", "--prefix", str(global_prefix)]
        else:
            prefix = tool_dir(tool.name)
            prefix.mkdir(parents=True, exist_ok=True)
            argv += ["--prefix", str(prefix)]
        _run([*argv, str(archive)], stage="opencli:npm_packages")


def _install(tool: Tool, *, global_: bool = False) -> None:
    """Install (or upgrade) one tool. Singletons: global_=True (our npm -g prefix)."""
    folder = npm_global_dir() if global_ else tool_dir(tool.name)
    if folder.exists() and not state.owned_path(folder) and state.load()["tools"].get(tool.name, {}).get("owner") != OURS:
        raise ReachError(NEED_SETUP, f"Unrecorded files occupy the {tool.name} install directory; left untouched")
    state.remember_path(folder, "installed dependency")
    if tool.kind == "npm":
        _install_npm(tool, global_prefix=npm_global_dir() if global_ else None)
    else:
        raise ReachError(UPSTREAM_BROKEN, f"no installer for {tool.name}")
    extend_path()


def _upgrade_user_singleton(tool: Tool) -> None:
    """Upgrade the user's own global copy in place (only with consent)."""
    _install_npm(tool, system_global=True)


def record(name: str, version: Optional[str], *, owner: str = OURS, scope: str = "private", **extra) -> dict:
    """Record a tool in state.json."""
    data = state.load()
    entry = {"owner": owner, "scope": scope, "version": version, **extra}
    data["tools"][name] = entry
    state.save(data)
    return {"tool": name, **entry}


def ensure(name: str, *, allow_upgrade: bool = False, upgrade: bool = False) -> dict:
    """Make sure the tool is installed inside its limits; record it in state.

    `upgrade`: reinstall our private copy at its install spec (update/sync): the tested
    version when declared, otherwise the newest version inside floor/exclude.
    Returns {"tool", "owner", "scope", "version"}; owner "system" = not ours, not recorded.
    """
    tool = TOOLS[name]
    if tool.kind in ("node", "uv", "ffmpeg"):
        if not all(shutil.which(command) for command in tool.commands):
            raise ReachError(NEED_SETUP, f"{name} prerequisites ({', '.join(tool.commands)}) are not installed; automatic downloads are disabled",
                             hint=f"Install them yourself (macOS: brew install {name}), then rerun setup.")
        return {"tool": name, "owner": "system", "scope": "system", "version": None}
    for dep in tool.needs:
        ensure(dep)  # callers that upgrade list the dependency themselves (manage.sync)
    entry = state.load()["tools"].get(name) or {}
    ours = entry.get("owner") == OURS

    if tool.kind == "chrome":
        from . import browser

        browser.ensure_chrome()
        return {"tool": name, "owner": "system", "scope": "system", "version": None}

    if tool.singleton:
        current = installed_version(tool)
        if current is None:
            _install(tool, global_=True)
            return record(name, installed_version(tool), scope="global", prefix=str(npm_global_dir()))
        if allowed(tool, current) and not (upgrade and ours):
            if not entry:
                return record(name, current, owner="user", scope="global")
            if entry.get("version") != current:
                return record(name, current, **{k: v for k, v in entry.items() if k != "version"})
            return {"tool": name, **entry}
        if ours and (upgrade or allow_upgrade):
            if entry.get("prefix"):
                _install(tool, global_=True)
            else:
                _upgrade_user_singleton(tool)
            return record(name, installed_version(tool), **{k: v for k, v in entry.items() if k != "version"})
        if not allow_upgrade:
            raise ReachError(
                NEED_SETUP,
                f"{name} {current} is outside the supported versions (needs >= {tool.floor or 'any'}"
                + (f", not {', '.join(tool.exclude)}" if tool.exclude else "") + ")",
                hint=f"Ask the user whether to upgrade their {name}; if yes, rerun with --allow-upgrade.",
            )
        _upgrade_user_singleton(tool)
        return record(name, installed_version(tool), owner=entry.get("owner", "user"), scope="global")

    private_ok = all(_private_bin(tool, c).exists() for c in tool.commands)
    if not private_ok or not ours or upgrade:
        _install(tool)
    elif entry.get("version"):
        return {"tool": name, **entry}
    # fresh install, or a record from an older Agent Reach without a version
    return record(name, _private_version(tool))


# ── removing ──

def _uninstall_global(name: str, entry: dict, dry_run: bool) -> Optional[str]:
    """Uninstall a singleton we installed. Returns a description, or None if not ours."""
    tool = TOOLS.get(name)
    if not tool or not tool.singleton or entry.get("owner") != OURS:
        return None
    prefix = entry.get("prefix")
    desc = f"npm -g {tool.package}" + (f" (in {prefix})" if prefix else "")
    npm = resolve("npm")
    if not dry_run and npm:
        argv = [npm, "uninstall", "-g", "--ignore-scripts", "--no-audit", "--no-fund"] + (["--prefix", prefix] if prefix else []) + [tool.package]
        try:
            subprocess.run(argv, capture_output=True, timeout=300, env=_install_env())
        except (OSError, subprocess.TimeoutExpired):
            pass
    return desc


def remove_private(name: str) -> bool:
    """Delete one of our installs and its record. User/system copies are never touched."""
    data = state.load()
    entry = data["tools"].get(name)
    tool = TOOLS.get(name)
    if tool and tool.singleton:
        if entry is None:
            return False
        if entry.get("owner") == OURS:
            _uninstall_global(name, entry, dry_run=False)
        data["tools"].pop(name, None)
        state.save(data)
        return entry.get("owner") == OURS
    if not entry or entry.get("owner") != OURS:
        return False
    removed = data["tools"].pop(name, None) is not None
    if _SAFE_NAME.fullmatch(name) and tool_dir(name).exists():
        from agent_reach.utils.paths import ensure_no_symlink_path
        ensure_no_symlink_path(tool_dir(name), "private tool")
        shutil.rmtree(tool_dir(name))
        removed = True
    state.save(data)
    return removed


def closure(names: Iterable[str]) -> Set[str]:
    """The tools plus everything they need."""
    out: Set[str] = set()
    todo = [n for n in names if n in TOOLS]
    while todo:
        n = todo.pop()
        if n not in out:
            out.add(n)
            todo.extend(TOOLS[n].needs)
    return out


def prune(keep: Set[str]) -> List[str]:
    """Remove our tools not in `keep` (and drop records of user copies no channel uses)."""
    removed = []
    for name, entry in list(state.load()["tools"].items()):
        if name in keep:
            continue
        if entry.get("owner") != OURS:
            data = state.load()
            data["tools"].pop(name, None)
            state.save(data)
            continue
        if name not in TOOLS and not _SAFE_NAME.match(name):
            continue
        if name == "chrome":
            from . import browser

            browser.stop()
        if remove_private(name):
            removed.append(name)
    return removed


def uninstall_global_owned(dry_run: bool) -> list:
    """Global singletons we installed (owner agent-reach); uninstall them."""
    out = []
    for name, entry in state.load()["tools"].items():
        desc = _uninstall_global(name, entry, dry_run)
        if desc:
            out.append(desc)
    return out


def recorded() -> List[dict]:
    """Every tool in state.json with its installed version (for doctor)."""
    return [{"tool": n, **e} for n, e in sorted(state.load()["tools"].items())]
