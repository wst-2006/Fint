"""统一的抓取工具：curl 子进程 + 原始落盘 + 请求日志。"""
import subprocess, time, os, json, datetime, sys

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
LOG = os.path.join(ROOT, "work", "fetch_log.jsonl")
_last = [0.0]
GAP = 3.0


def fetch(url, outpath, referer=None, gap=GAP):
    """返回 (code, size, err)。任何返回都落盘；失败也写日志。"""
    wait = GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    cmd = ["curl", "-sS", "-k", "--tlsv1.2", "--http1.1", "--compressed",
           "--max-time", "90", "-A", UA,
           "-H", "Accept-Language: zh-CN,zh;q=0.9",
           "-o", outpath, "-w", "%{http_code} %{size_download}"]
    if referer:
        cmd += ["-e", referer]
    cmd.append(url)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = (p.stdout or "").strip().split()
        code = out[0] if out else "000"
        size = int(out[1]) if len(out) > 1 and out[1].isdigit() else 0
        err = (p.stderr or "").strip()[:300]
    except Exception as e:
        code, size, err = "EXC", 0, str(e)[:300]
    _last[0] = time.time()
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
           "url": url, "code": code, "size": size, "sec": round(time.time() - t0, 2),
           "err": err, "file": os.path.relpath(outpath, ROOT)}
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return code, size, err


def get(url, name, subdir="pages", referer=None):
    d = os.path.join(RAW, subdir)
    os.makedirs(d, exist_ok=True)
    fn = name if name.endswith((".html", ".pdf", ".json")) else name + ".html"
    p = os.path.join(d, fn)
    code, size, err = fetch(url, p, referer=referer)
    return code, p
