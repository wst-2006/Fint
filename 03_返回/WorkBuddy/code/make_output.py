"""生成交付文件：项目清单、公告台账、原始文件清单、统计。"""
import csv, os, json, hashlib, datetime, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import load, stat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "repo", "03_返回", "WorkBuddy")
TS = datetime.datetime.now().strftime("%Y%m%dT%H%M")


def w(name, rows, fields=None):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    if not rows:
        open(p, "w", encoding="utf-8-sig").write("")
        return p
    fields = fields or list(rows[0].keys())
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    return p


def main():
    rows = load()
    p1 = w(f"P1-R1-WB_沙盒项目清单_{TS}.csv", rows)

    # 公告台账
    ext = json.load(open(os.path.join(ROOT, "work", "extracted.json"), encoding="utf-8"))
    anns = []
    for r in sorted(ext, key=lambda x: x["date"], reverse=True):
        n_p = len(r.get("projects", []))
        n_e = len(r.get("ended", []))
        anns.append({"公告日期": r["date"], "地区": r["region"], "公告类型": r["kind"],
                     "标题": r["title"], "项目条数": n_p, "出箱条数": n_e, "链接": r["src"]})
    p2 = w(f"P1-R1-WB_公告台账_{TS}.csv", anns)

    # 原始文件清单
    man = []
    for sub in ["pages", "search", "columns"]:
        d = os.path.join(ROOT, "raw", sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            fp = os.path.join(d, fn)
            if not os.path.isfile(fp):
                continue
            h = hashlib.sha256(open(fp, "rb").read()).hexdigest()[:16]
            man.append({"目录": f"raw/{sub}", "文件名": fn, "字节": os.path.getsize(fp),
                        "sha256_16": h})
    p3 = w(f"P1-R1-WB_原始文件清单_{TS}.csv", man)

    # 统计
    s = stat(rows)
    lines = [f"# 沙盒项目统计（{TS}）", "", f"总项目数：{s['total']}", ""]
    for key, title in [("by_year", "按公示年份"), ("by_region", "按地区"), ("by_type", "按创新应用类型"),
                       ("by_status", "按状态"), ("by_tech", "按技术类型（多标签）"),
                       ("by_serv", "按服务类型（多标签）"), ("by_user", "按面向用户（推断）")]:
        lines += [f"## {title}", "", "| 项 | 数量 |", "|---|---|"]
        for k, v in s[key].most_common():
            lines.append(f"| {k} | {v} |")
        lines.append("")
    p4 = os.path.join(OUT, f"P1-R1-WB_统计_{TS}.md")
    open(p4, "w", encoding="utf-8").write("\n".join(lines))
    print(p1); print(p2); print(p3); print(p4)
    print("rows", len(rows), "anns", len(anns), "files", len(man))


if __name__ == "__main__":
    main()
