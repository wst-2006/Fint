"""抓取各分行公告栏目前若干页与末若干页，回收公示/公告条目（旧站迁移后检索索引不全）。"""
import re, os, sys, json, time, threading
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch as F
from parse import parse_html

ROOT = F.ROOT
HOSTS = ["beijing", "tianjin", "shijiazhuang", "taiyuan", "huhehaote", "shenyang", "dalian",
         "changchun", "haerbin", "shanghai", "nanjing", "hangzhou", "hefei", "fuzhou", "xiamen",
         "nanchang", "jinan", "qingdao", "zhengzhou", "wuhan", "changsha", "guangzhou",
         "shenzhen", "nanning", "haikou", "chongqing", "chengdu", "guiyang", "kunming",
         "xian", "lanzhou", "xining", "yinchuan", "wulumuqi", "lasa"]
GAP = 3.2
_locks, _last, _g = {}, {}, threading.Lock()


def fetch(u, name):
    h = re.match(r"https?://([^/]+)/", u).group(1)
    with _g:
        lk = _locks.setdefault(h, threading.Lock())
    with lk:
        w = GAP - (time.time() - _last.get(h, 0))
        if w > 0:
            time.sleep(w)
        p = os.path.join(ROOT, "raw", "columns", name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        code, size, err = F.fetch(u, p, gap=0)
        _last[h] = time.time()
        return code, p


def find_column(host):
    code, p = fetch(f"https://{host}.pbc.gov.cn/", f"{host}_home.html")
    if code != "200":
        return None
    r = parse_html(open(p, encoding="utf-8", errors="ignore").read())
    for a in r.iter("a"):
        if a.get_text(" ").strip() == "公告信息" and a.attrs.get("href"):
            href = a.attrs["href"]
            return f"https://{host}.pbc.gov.cn{href}" if href.startswith("/") else href
    return None


def parse_list(html, host):
    r = parse_html(html)
    out = []
    for a in r.iter("a"):
        href = a.attrs.get("href", "")
        if not re.search(r"/%s/\d+/\d{12,}/index\.html" % host, href):
            continue
        title = (a.attrs.get("title") or a.get_text(" ")).strip()
        if len(title) < 6:
            continue
        node, date = a, ""
        for _ in range(4):
            node = node.parent
            if node is None:
                break
            m = re.search(r"(20\d{2}-\d{2}-\d{2})", node.get_text(" "))
            if m:
                date = m.group(1)
                break
        if not date:
            continue
        out.append({"title": title, "date": date,
                    "url": href if href.startswith("http") else f"https://{host}.pbc.gov.cn{href}"})
    seen, ded = set(), []
    for x in out:
        if x["url"] in seen:
            continue
        seen.add(x["url"])
        ded.append(x)
    tp = re.search(r"分<b>(\d+)</b>页", html)
    total = int(tp.group(1)) if tp else 1
    mid = re.search(r"queryArticleByCondition\(this,'([^']*?)-(\d+)\.html'\)", html)
    base = mid.group(1) if mid else None
    return ded, total, base


def crawl(host):
    col = find_column(host)
    if not col:
        return {"host": host, "err": "no col"}
    code, p = fetch(col, f"{host}_col.html")
    if code != "200":
        return {"host": host, "err": code}
    items, total, base = parse_list(open(p, encoding="utf-8", errors="ignore").read(), host)
    pages = list(range(2, min(total, 14) + 1))
    if total > 16:
        pages += list(range(max(15, total - 13), total + 1))
    allit = list(items)
    for pno in pages:
        if not base:
            break
        u = f"https://{host}.pbc.gov.cn{base}-{pno}.html"
        code, p = fetch(u, f"{host}_p{pno}.html")
        if code != "200":
            continue
        its, _, _ = parse_list(open(p, encoding="utf-8", errors="ignore").read(), host)
        allit += its
    seen, ded = set(), []
    for x in allit:
        if x["url"] in seen:
            continue
        seen.add(x["url"])
        ded.append(x)
    keep = [x for x in ded if re.search(r"公示|监管工具|监管试点|创新应用|结束测试|提供服务", x["title"])]
    return {"host": host, "col": col, "total": total, "pages": len(pages) + 1,
            "items": ded, "keep": keep}


if __name__ == "__main__":
    out = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for r in ex.map(crawl, HOSTS):
            out.append(r)
            print(r.get("host"), r.get("total"), len(r.get("items") or []),
                  len(r.get("keep") or []), r.get("err", ""), flush=True)
    json.dump(out, open(os.path.join(ROOT, "work", "columns.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
