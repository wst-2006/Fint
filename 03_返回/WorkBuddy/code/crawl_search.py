"""抓取央行站内检索结果（标题检索），翻页收集公告列表。"""
import re, os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import get, ROOT

BASE = ("https://wzdig.pbc.gov.cn/search/pcRender?pageId=c177a85bd02b4114bebebd210809f691"
        "&q={q}&searchArea=title&pNo={p}")


def unesc(s):
    s = re.sub(r"<font[^>]*>|</font>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    return (s.replace("&nbsp;", " ").replace("&amp;", "&")
             .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').strip())


def parse(h):
    items = []
    for blk in re.split(r'<div class="searchMod">', h)[1:]:
        m = re.search(r'<h3>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not m:
            continue
        url, title = m.group(1), unesc(m.group(2))
        d = re.search(r'<span>(\d{4})年(\d{1,2})月(\d{1,2})日</span>', blk)
        snip = re.search(r'<p class="txtCon[^"]*">(.*?)</p>', blk, re.S)
        items.append({"url": url, "title": title,
                      "date": f"{d.group(1)}-{int(d.group(2)):02d}-{int(d.group(3)):02d}" if d else "",
                      "snippet": unesc(snip.group(1))[:300] if snip else ""})
    tp = re.search(r'default-result-total-pages" value="(\d+)"', h)
    tr = re.search(r'default-result-total-records" value="(\d+)"', h)
    return items, (int(tp.group(1)) if tp else 0), (int(tr.group(1)) if tr else 0)


def crawl(q, tag, maxpages=80):
    from urllib.parse import quote
    qq = quote(q)
    allitems = []
    p = 1
    total_pages = 1
    while p <= min(total_pages, maxpages):
        url = BASE.format(q=qq, p=p)
        cache = os.path.join(ROOT, "raw", "search", f"search_{tag}_{p:03d}.html")
        if os.path.exists(cache) and os.path.getsize(cache) > 3000:
            code, path = "200", cache
        else:
            code, path = get(url, f"search_{tag}_{p:03d}", subdir="search")
        if code != "200":
            print("FAIL", p, code); break
        h = open(path, encoding="utf-8", errors="ignore").read()
        items, total_pages, total_records = parse(h)
        if p == 1:
            print(f"[{tag}] {q}: records={total_records} pages={total_pages}", flush=True)
        if not items:
            break
        for it in items:
            it["query_tag"] = tag
        allitems += items
        print(f"  page {p}/{total_pages}: {len(items)}", flush=True)
        p += 1
    out = os.path.join(ROOT, "work", f"search_{tag}.json")
    json.dump(allitems, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{tag}] saved {len(allitems)} -> {out}")
    return allitems


if __name__ == "__main__":
    tag = sys.argv[1]
    q = sys.argv[2]
    crawl(q, tag)
