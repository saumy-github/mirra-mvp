import sys, os, time, json, zipfile, struct, shutil
from pathlib import Path

REPO = Path(r"C:\D-drive-data\mirra-mvp")
sys.path.insert(0, str(REPO / "clo_avatar_generation"))
from avatar_runtime.client import CLORestClient
from avatar_runtime.avs_patch import _float_block_offset, FEATURE_MARKER

SCR = Path(__file__).resolve().parent.parent
WORK = SCR / "work"
WORK.mkdir(exist_ok=True)
ASSETS = REPO / ".agent" / "saumy" / "research_files" / "CLO" / "CLO Assets" / "Avatar"
FEM_RES = REPO / "clo_avatar_generation" / "input" / "female_research"

c = CLORestClient(timeout=180)

# slot meaning (same layout male and female)
NAMES = {0: "Total Height", 1: "Weight", 2: "Chest/Bust", 3: "Mid Neck", 4: "Neck Base", 5: "Under Bust", 6: "Waist", 7: "High Hip",
         8: "Low Hip", 9: "Thigh", 10: "Mid Thigh", 11: "Knee", 12: "Calf", 13: "Ankle", 14: "Armhole", 15: "Bicep", 16: "Elbow",
         17: "Wrist", 26: "Inseam", 36: "Across Shoulder"}
DRIVEN = [0, 2, 6, 8, 26, 36]


def feats_from_bytes(data):
    off = _float_block_offset(data)
    return [struct.unpack_from("<f", data, off + 4 * k)[0] for k in range(57)]


def feats_avs(p):
    return feats_from_bytes(Path(p).read_bytes())


def feats_avt(p):
    z = zipfile.ZipFile(p)
    for i in z.infolist():
        if i.filename.endswith(".dan"):
            return feats_from_bytes(z.read(i.filename))
    raise ValueError("no dan")


def patch_avs(template, changes, out):
    data = bytearray(Path(template).read_bytes())
    off = _float_block_offset(bytes(data))
    for idx, val in changes.items():
        struct.pack_into("<f", data, off + 4 * int(idx), float(val))
    Path(out).write_bytes(bytes(data))
    return out


def wq(extra=0.0):
    c.wait_for_queue(timeout=60)
    time.sleep(extra)


def fresh(base_avt):
    wq(4.0)
    r1 = c.new_project()
    wq(4.0)
    r2 = c.import_avatar_avt(str(base_avt))
    wq(3.0)
    return r1.get("success"), r2.get("success")


def apply_avs(p):
    r = c.import_avatar_avt(str(p), method="import_file")
    wq(3.0)
    return r


def readout(name):
    out = WORK / f"{name}.avt"
    if out.exists():
        out.unlink()
    r = c.export_avatar_avt(str(out))
    wq(1.5)
    for _ in range(20):
        if out.exists() and out.stat().st_size > 1000:
            break
        time.sleep(0.5)
    return feats_avt(out)


def diff(a, b, thr=0.05):
    return [(k, round(a[k], 2), round(b[k], 2), round(b[k] - a[k], 2)) for k in range(57) if abs(a[k] - b[k]) > thr]


def save(name, obj):
    (SCR / "results").mkdir(exist_ok=True)
    (SCR / "results" / f"{name}.json").write_text(json.dumps(obj, indent=1), encoding="utf-8")


import numpy as np


def mesh_vertices(name):
    """Export the current scene as GLB, return all vertices (N,3) in scene order, delete the file."""
    import trimesh
    out = WORK / f"{name}.glb"
    if out.exists():
        out.unlink()
    r = c.export_avatar_glb(str(out))
    wq(1.0)
    last = -1
    for _ in range(120):
        if out.exists():
            s = out.stat().st_size
            if s > 1000 and s == last:
                break
            last = s
        time.sleep(1.0)
    scene = trimesh.load(str(out), force="scene")
    parts = scene.dump(concatenate=False)
    V = np.vstack([np.asarray(p.vertices) for p in parts])
    try:
        out.unlink()
    except Exception:
        pass
    return V


def vdist(A, B):
    if A.shape != B.shape:
        return None
    d = np.linalg.norm(A - B, axis=1) * 100.0  # cm if GLB is in metres
    return {"mean_cm": round(float(d.mean()), 3), "p95_cm": round(float(np.percentile(d, 95)), 3), "max_cm": round(float(d.max()), 3)}


import glob, re

U_SLOTS = [4, 5, 7, 9, 15, 47]


def tmpl_id(p):
    m = re.search(rb"5\.1_(Female|Male)Template_\d+", Path(p).read_bytes())
    return m.group(0).decode() if m else "?"


def ridge_fit(X, Y, alpha=1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z1 = np.c_[np.ones(len(X)), (X - mu) / sd]
    I = np.eye(Z1.shape[1]); I[0, 0] = 0
    W = np.linalg.solve(Z1.T @ Z1 + alpha * I, Z1.T @ Y)
    return mu, sd, W


def ridge_pred(m, x):
    mu, sd, W = m
    return np.r_[1.0, (np.asarray(x) - mu) / sd] @ W


def predict_slots(train_feats, six_vals, slots, alpha=1.0):
    A = np.array(train_feats)
    m = ridge_fit(A[:, DRIVEN], A[:, slots], alpha)
    return ridge_pred(m, six_vals)


def truth_metrics(got, S):
    d = np.abs(np.array(got) - np.array(S))
    return {"mean_abs_slot_err_cm": round(float(d.mean()), 3), "max_slot_err_cm": round(float(d.max()), 2),
            "U_slots_err": {k: round(float(got[k] - S[k]), 2) for k in U_SLOTS}}


# ---- faster settle times with automatic fallback (added 2026-10-20) ----
SPEED = {"f": 0.5}  # multiplier on the pipeline's settle times (4 s / 4 s / 3 s); 1.0 = pipeline speed


def fresh(base_avt):  # noqa: F811
    f = SPEED["f"]
    wq(4.0 * f)
    r1 = c.new_project()
    wq(4.0 * f)
    r2 = c.import_avatar_avt(str(base_avt))
    wq(3.0 * f)
    return r1.get("success"), r2.get("success")


def apply_avs(p):  # noqa: F811
    r = c.import_avatar_avt(str(p), method="import_file")
    wq(2.0 * SPEED["f"])
    return r


def readout(name, keep=False):  # noqa: F811
    out = WORK / f"{name}.avt"
    if out.exists():
        out.unlink()
    c.export_avatar_avt(str(out))
    wq(0.5)
    for _ in range(40):
        if out.exists() and out.stat().st_size > 1000:
            time.sleep(0.3)
            break
        time.sleep(0.25)
    f = feats_avt(out)
    if not keep:
        try:
            out.unlink()
        except Exception:
            pass
    return f


def run_variant(base_avt, avs, name, want_mesh=True, keep_avt=False):
    """fresh + apply + readout (+ mesh). Verifies the readout looks applied; retries once at pipeline speed."""
    sent = feats_avs(avs)
    for attempt in (0, 1):
        try:
            fresh(base_avt)
            apply_avs(avs)
            got = readout(name, keep=keep_avt)
            ok = abs(got[0] - sent[0]) < 0.6 and abs(got[2] - sent[2]) < 0.6 and abs(got[6] - sent[6]) < 0.6
            if ok:
                V = mesh_vertices("m_" + name) if want_mesh else None
                return got, V
        except Exception as e:  # noqa: BLE001
            print("  retry after error:", repr(e)[:120], flush=True)
        SPEED["f"] = 1.0
        print("  -> falling back to pipeline speed", flush=True)
    raise RuntimeError("variant failed twice: " + name)


def float_block_offset_robust(d):
    """Offset of the 57 floats: they end a few bytes before 'listMeasureLinkList'; find the gap that gives plausible values."""
    e = d.find(b"listMeasureLinkList")
    if e < 0:
        raise ValueError("listMeasureLinkList marker not found")
    best = None
    for gap in range(0, 241, 4):
        off = e - 57 * 4 - gap
        if off < 0:
            break
        f = [struct.unpack_from("<f", d, off + 4 * i)[0] for i in range(57)]
        if not all(-1.0 < x < 400.0 for x in f):
            continue
        if 60.0 < f[0] < 250.0 and f[0] >= max(f) - 1e-3 and 5.0 < f[1] < 220.0 and 20.0 < f[2] < 200.0 and 15.0 < f[6] < 200.0 and 20.0 < f[8] < 200.0 and 15.0 < f[26] < 150.0:
            return off, gap
    raise ValueError("no plausible float block")


def feats_from_bytes(data):  # noqa: F811
    off, _ = float_block_offset_robust(data)
    return [struct.unpack_from("<f", data, off + 4 * k)[0] for k in range(57)]


def patch_avs(template, changes, out):  # noqa: F811
    data = bytearray(Path(template).read_bytes())
    off, _ = float_block_offset_robust(bytes(data))
    for idx, val in changes.items():
        struct.pack_into("<f", data, off + 4 * int(idx), float(val))
    Path(out).write_bytes(bytes(data))
    return out
