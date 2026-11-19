"""统计与图表数据。"""
import csv, os, sys, json
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    with open(os.path.join(ROOT, "work", "projects.csv"), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def stat(rows):
    out = {}
    out["total"] = len(rows)
    out["by_year"] = Counter((r.get("年份") or "未知") for r in rows)
    out["by_region"] = Counter(r["地区"] for r in rows)
    out["by_type"] = Counter(r["创新应用类型"] or "未列明" for r in rows)
    out["by_status"] = Counter(r["状态"] for r in rows)
    tech = Counter()
    for r in rows:
        for t in (r["技术类型_推断"] or "未识别").split("；"):
            tech[t] += 1
    out["by_tech"] = tech
    serv = Counter()
    for r in rows:
        for t in (r["服务类型_推断"] or "未识别").split("；"):
            serv[t] += 1
    out["by_serv"] = serv
    users = Counter()
    for r in rows:
        for t in (r["面向用户_推断"] or "未列明").split("；"):
            users[t] += 1
    out["by_user"] = users
    return out


if __name__ == "__main__":
    rows = load()
    s = stat(rows)
    for k, v in s.items():
        if isinstance(v, Counter):
            print("##", k)
            for a, b in v.most_common():
                print(f"   {a}\t{b}")
        else:
            print("##", k, v)
