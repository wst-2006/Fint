"""多线程按站点限速抓取详情页（每个站点请求间隔 >= 3 秒）。"""
import json, os, re, sys, hashlib, time, threading
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch as F

ROOT = F.ROOT
GAP = 3.2
_locks = {}
_guard = threading.Lock()
_last = {}


def host(u):
    m = re.match(r"https?://([^/]+)/", u)
    return m.group(1) if m else "?"


def fetch_one(u, path):
    h = host(u)
    with _guard:
        lk = _locks.setdefault(h, threading.Lock())
    with lk:
        wait = GAP - (time.time() - _last.get(h, 0))
        if wait > 0:
            time.sleep(wait)
        out = os.path.join(ROOT, path)
        code, size, err = F.fetch(u, out, gap=0)
        _last[h] = time.time()
        return code


def main():
    anns = json.load(open(os.path.join(ROOT, "work", "announcements.json"), encoding="utf-8"))
    def keep(t):
        return any(k in t for k in ["监管工具", "监管试点", "创新应用", "沙盒", "入盒", "出箱"])
    anns = [a for a in anns if keep(a["title"])]
    todo = []
    for a in anns:
        h = hashlib.md5(a["urls"][0].encode()).hexdigest()[:12]
        a["page"] = f"raw/pages/{a['date']}_{h}.html"
        p = os.path.join(ROOT, a["page"])
        if os.path.exists(p) and os.path.getsize(p) > 2000:
            continue
        todo.append(a)
    print("todo", len(todo), flush=True)
    done = [0]
    def work(a):
        code = fetch_one(a["urls"][0], a["page"])
        done[0] += 1
        if done[0] % 25 == 0:
            print(f"  {done[0]}/{len(todo)} {code} {a['date']}", flush=True)
    with ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(work, todo))
    print("done", done[0], flush=True)


if __name__ == "__main__":
    main()
