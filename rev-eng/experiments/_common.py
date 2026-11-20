"""Shared helpers for the supervised CLO live experiments (stdlib only, Python 3.12).

NOT run by anyone automatically. Every experiment script imports this by sibling path.

REST facts (from clo_workspace/windows/RestPlugin_windows.cpp, read 2026-10-29):
  * Server: http://127.0.0.1:50505 (override with env MIRRA_CLO_URL). NO authentication:
    neither the plugin nor clo_avatar_generation/avatar_runtime/client.py uses a token or
    token env var.
  * Mutating routes are QUEUED: POST route -> POST /execute -> poll GET /status until idle.
    /status.last_results holds the results of the most recent drained batch (cleared at
    drain start), so these scripts send ONE command per batch to get an exact result.
  * Sync reads: GET /avatars/state, /patterns/count, /patterns/<i>, /patterns/<i>/bbox,
    /patterns/<i>/input, /fabric-status, /health, /capabilities.
  * There is NO generic "run SDK function X" route. Anything not in the list above
    (GetAvatarMeasurements, grading getters, GetFabricPBRMaterialBaseColor,
    ExportGLTF component lists, Simulate vertex read-back ...) needs a new plugin command.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")
REV_ENG = os.path.dirname(HERE)
BASE_URL = os.environ.get("MIRRA_CLO_URL", "http://127.0.0.1:50505").rstrip("/")


class MissingPluginCommand(RuntimeError):
    """Raised (fail fast) when an experiment needs a plugin command that does not exist."""


def todo_missing_command(sdk_call: str, proposed_route: str, why: str = "") -> None:
    msg = (f"TODO / BLOCKED: plugin has no REST route for {sdk_call}. Proposed new route: "
           f"{proposed_route}. {why} Not guessing; add the command to RestPlugin_windows.cpp "
           f"(a dispatchSyncRead branch) and rebuild before running this step.")
    raise MissingPluginCommand(msg)


def now_tag() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def load_module_by_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def avs_grammar():
    return load_module_by_path("avs_grammar", os.path.join(REV_ENG, "scripts", "avs_grammar.py"))


def glb_probe():
    return load_module_by_path("glb_probe", os.path.join(REV_ENG, "scripts", "glb_probe.py"))


def _req(method: str, route: str, payload, timeout: float) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    r = urllib.request.Request(BASE_URL + route, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"success": False, "http_status": e.code, "error": str(e)}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


def get(route: str, timeout: float = 60) -> dict:
    return _req("GET", route, None, timeout)


def post(route: str, payload=None, timeout: float = 60) -> dict:
    return _req("POST", route, payload or {}, timeout)


class Recorder:
    """Collects every step; writes experiments/out/<exp>_<ts>.json at the end (or on abort)."""

    def __init__(self, exp: str, args=None):
        os.makedirs(OUT_DIR, exist_ok=True)
        self.exp, self.t0 = exp, time.time()
        self.path = os.path.join(OUT_DIR, f"{exp}_{now_tag()}.json")
        self.data = {"experiment": exp, "started": _dt.datetime.now().isoformat(),
                     "args": vars(args) if args else {}, "steps": [], "notes": [], "verdict": None}

    def step(self, name: str, **kw):
        row = {"t": round(time.time() - self.t0, 2), "step": name, **kw}
        self.data["steps"].append(row)
        print(f"[{row['t']:7.1f}s] {name}: " + json.dumps(kw, default=str)[:600])
        return row

    def note(self, text: str):
        self.data["notes"].append(text)
        print("NOTE:", text)

    def finish(self, verdict=None):
        self.data["verdict"] = verdict
        self.data["finished"] = _dt.datetime.now().isoformat()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1, default=str)
        print("results written:", self.path)


def standard_args(desc: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true",
                    help="actually contact the plugin. Without it the script only prints its plan and exits (default).")
    ap.add_argument("--queue-timeout", type=float, default=120.0,
                    help="seconds to wait for one queued command; a timeout usually means a MODAL DIALOG is open.")
    return ap


def preflight(rec: Recorder) -> dict:
    """Refuse to continue unless CLO is up and host_matches_sdk is true (R1: ABI skew crashes)."""
    h = get("/health", timeout=10)
    rec.step("health", **{k: h.get(k) for k in ("status", "plugin_built_at", "sdk_clo_version",
                                                "host_app_version", "host_matches_sdk", "error")})
    if h.get("status") != "ok":
        raise SystemExit("ABORT: /health not ok (is CLO running with the plugin loaded?)")
    if not h.get("host_matches_sdk"):
        raise SystemExit("ABORT: host_matches_sdk is false; plugin SDK != installed CLO. Rebuild first "
                         "(mismatch is known to crash CLO in import/delete/simulate).")
    cap = get("/capabilities", timeout=10)
    rec.step("capabilities", **{k: v for k, v in cap.items() if k.startswith("has_")})
    st = get("/status", timeout=10)
    rec.step("status", queue_size=st.get("queue_size"), queue_processing=st.get("queue_processing"))
    if st.get("queue_size") or st.get("queue_processing"):
        raise SystemExit("ABORT: command queue not idle at start.")
    return h


def run_cmd(rec: Recorder, name: str, route: str, payload, timeout: float = 120.0) -> dict:
    """POST a queued command, trigger /execute, wait for idle, return the batch's last_results."""
    first = post(route, payload)
    if not first.get("success"):
        rec.step(name, queued=False, response=first)
        return {"queued": False, "response": first, "results": [], "ok": False}
    ex = post("/execute")
    deadline, idle_hits, st = time.time() + timeout, 0, {}
    time.sleep(0.4)
    done = False
    while time.time() < deadline:
        st = get("/status", timeout=10)
        if st.get("queue_size", 1) == 0 and not st.get("queue_processing", True):
            idle_hits += 1
            if idle_hits >= 2:
                done = True
                break
        else:
            idle_hits = 0
        time.sleep(0.5)
    if not done:
        rec.step(name, timeout=True, hint="TIMEOUT: probably a modal dialog; run e07 watchdog, then dismiss by hand")
        rec.finish("ABORTED_TIMEOUT")
        raise SystemExit(f"ABORT: '{name}' did not finish within {timeout}s (modal dialog?).")
    res = st.get("last_results", [])
    rec.step(name, route=route, execute=ex.get("message"), results=res)
    return {"queued": True, "results": res, "ok": bool(res) and all(r.get("success") for r in res)}


def wait_fabric_done(rec: Recorder, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    fs = {}
    while time.time() < deadline:
        fs = get("/fabric-status", timeout=10)
        if fs.get("all_done"):
            break
        time.sleep(0.5)
    rec.step("fabric-status", **{k: fs.get(k) for k in ("pending", "completed", "failed", "all_done", "last_message")})
    return fs


def avatar_state(rec: Recorder, label: str) -> dict:
    s = get("/avatars/state", timeout=60)
    rec.step(f"avatars/state[{label}]", avatar_count=s.get("avatar_count"),
             names=[a.get("name") for a in s.get("avatars", [])], success=s.get("success"))
    return s


def pattern_count(rec: Recorder, label: str) -> int:
    c = get("/patterns/count", timeout=30)
    rec.step(f"patterns/count[{label}]", response=c)
    for k in ("count", "pattern_count"):
        if k in c:
            return int(c[k])
    return -1


def export_scene(rec: Recorder, name: str, path: str, fmt: str = "glb", timeout: float = 300.0) -> dict:
    path = os.path.abspath(path).replace("\\", "/")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = run_cmd(rec, name, "/export", {"path": path, "format": fmt}, timeout=timeout)
    size = os.path.getsize(path) if os.path.exists(path) else None
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16] if size else None
    rec.step(name + ".file", path=path, bytes=size, sha256_16=sha)
    return {"path": path, "bytes": size, "sha": sha, "ok": r.get("ok")}


def glb_summary(paths) -> list:
    gp, rows = glb_probe(), []
    for p in paths:
        try:
            g = gp.load(p)
            j = g["json"]
            v, t = gp.stats(g)
            rows.append({"path": p, "kind": g["kind"], "bytes": len(g["raw"]),
                         "bin_len": len(g["bin"]), "bin_sha": hashlib.sha256(g["bin"]).hexdigest()[:16],
                         "nodes": len(j.get("nodes", [])), "meshes": len(j.get("meshes", [])),
                         "verts": v, "tris": t, "materials": len(j.get("materials", [])),
                         "images": len(j.get("images", [])),
                         "baseColorFactors": [m.get("pbrMetallicRoughness", {}).get("baseColorFactor")
                                              for m in j.get("materials", [])][:20]})
        except Exception as e:  # noqa: BLE001
            rows.append({"path": p, "error": f"{type(e).__name__}: {e}"})
    return rows


def plan_only(args, lines) -> None:
    """Dry-run default: print the plan and exit 0 before touching the plugin."""
    if args.live:
        return
    print("DRY RUN (no --live): nothing contacted. Plan:")
    for i, line in enumerate(lines, 1):
        print(f"  {i}. {line}")
    print("Re-run with --live under supervision (backup first, one CLO instance, see README.md).")
    raise SystemExit(0)


def guarded(fn):
    """Run an experiment main; convert MissingPluginCommand into a clean fail-fast exit code 3."""
    try:
        fn()
    except MissingPluginCommand as e:
        print(str(e))
        raise SystemExit(3)
