"""把公示/登记/结束测试三路记录合并成项目级清单。"""
import json, os, re, csv, sys
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import tag, TECH, SERV, USERS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def clean_name(n):
    n = re.sub(r"[（(]\s*自声明链接.*$", "", n or "")
    n = re.sub(r"\s+", "", n)
    return n.strip()


def clean_code(c):
    c = (c or "").replace("—", "-").replace("－", "-")
    c = re.sub(r"\s+", "", c)
    m = re.match(r"^([0-9A-Z]{15,22})-(\d{4})-(\d{4})$", c)
    if not m or int(m.group(2)) < 2019:
        return ""
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def norm(s):
    s = re.sub(r"\s+", "", s or "")
    return s.replace("（", "(").replace("）", ")").replace("“", "").replace("”", "")


def tech_label(name):
    t = tag(name, TECH)
    return "；".join(t) if t else "未识别"


def serv_label(name):
    s = tag(name, SERV)
    return "；".join(s) if s else "未识别"


def user_label(name):
    u = tag(name, USERS)
    return "；".join(u) if u else "未列明"


def main():
    res = json.load(open(os.path.join(ROOT, "work", "extracted.json"), encoding="utf-8"))
    proj, order = {}, []
    end_list = []
    for r in res:
        for e in r.get("ended", []):
            if len(norm(e["name"])) < 6 or "金融科技创新监管工具" in e["name"]:
                continue
            end_list.append({"name": norm(e["name"]), "date": r["date"], "code": e.get("code", ""),
                             "inst": e.get("inst", ""), "type": e.get("type", ""),
                             "src": r["src"], "region": r["region"]})
    end_by_name = defaultdict(list)
    for e in end_list:
        end_by_name[e["name"]].append(e)

    for r in sorted(res, key=lambda x: x["date"] or ""):
        if r["kind"] not in ("PUB", "SERV", "OTHER"):
            continue
        for p in r.get("projects", []):
            nm = norm(clean_name(p["name"]))
            if not nm or len(nm) < 5 or "金融科技创新监管工具" in nm:
                continue
            if nm not in proj:
                proj[nm] = {"name": p["name"], "inst": p["inst"], "app_type": p["app_type"],
                            "code": clean_code(p.get("code", "")), "pub_date": "", "pub_src": "",
                            "pub_region": "", "serv_date": "", "serv_src": "",
                            "end_date": "", "end_src": "", "regions": [], "note": ""}
                order.append(nm)
            q = proj[nm]
            if not q["inst"] and p["inst"]:
                q["inst"] = p["inst"]
            if not q["app_type"] and p["app_type"]:
                q["app_type"] = p["app_type"]
            pc = clean_code(p.get("code"))
            if pc and not q["code"]:
                q["code"] = pc
            if r["kind"] == "PUB" and not q["pub_date"]:
                q["pub_date"], q["pub_src"], q["pub_region"] = r["date"], r["src"], r["region"]
            elif r["kind"] == "SERV" and not q["serv_date"]:
                q["serv_date"], q["serv_src"] = r["date"], r["src"]
            if r["region"] and r["region"] not in q["regions"]:
                q["regions"].append(r["region"])

    names = list(proj.keys())

    def fuzzy(nm):
        if nm in proj:
            return nm
        cands = [k for k in names if (nm in k or k in nm)
                 and min(len(nm), len(k)) / max(len(nm), len(k)) > 0.8]
        return cands[0] if len(cands) == 1 else None

    matched = set()
    for e in sorted(end_list, key=lambda x: x["date"]):
        k = fuzzy(e["name"])
        if k and not proj[k]["end_date"]:
            q = proj[k]
            q["end_date"], q["end_src"] = e["date"], e["src"]
            if not q["code"] and clean_code(e["code"]):
                q["code"] = clean_code(e["code"])
            if not q["inst"] and e["inst"]:
                q["inst"] = e["inst"]
            matched.add(e["name"])
        elif not k:
            key = "__end__" + e["name"]
            if key in proj:
                continue
            proj[key] = {"name": e["name"], "inst": e["inst"], "app_type": e["type"],
                         "code": clean_code(e["code"]), "pub_date": "", "pub_src": "", "pub_region": "",
                         "serv_date": "", "serv_src": "", "end_date": e["date"],
                         "end_src": e["src"], "regions": [e["region"]] if e["region"] else [],
                         "note": "仅见结束测试公告，未见公示公告"}
            order.append(key)

    rows = []
    for k in order:
        q = proj[k]
        status = ("已出箱（成功完成测试）" if q["end_date"] else
                  ("测试运行中（已登记/提供服务）" if q["serv_date"] else
                   ("仅公示，未见后续登记公告" if q["pub_date"] else "状态未见公告")))
        rows.append({
            "公示日期": q["pub_date"], "地区": q["pub_region"] or "、".join(q["regions"]),
            "项目名称": q["name"], "申请机构": q["inst"], "创新应用类型": q["app_type"],
            "创新应用编号": q["code"], "技术类型_推断": tech_label(q["name"]),
            "服务类型_推断": serv_label(q["name"]), "面向用户_推断": user_label(q["name"]),
            "状态": status, "出箱日期": q["end_date"],
            "登记/测试开始公告日期": q["serv_date"],
            "年份": (q["pub_date"] or "")[:4] or (re.search(r"-(20\d{2})-", q["code"]).group(1) if re.search(r"-(20\d{2})-", q["code"]) else ""),
            "公示公告链接": q["pub_src"],
            "登记公告链接": q["serv_src"], "出箱公告链接": q["end_src"], "备注": q["note"],
        })
    rows.sort(key=lambda r: (r["公示日期"] or "9999", r["地区"]))
    for i, r in enumerate(rows, 1):
        r["序号"] = i
    fields = ["序号", "公示日期", "年份", "地区", "项目名称", "申请机构", "创新应用类型", "创新应用编号",
              "技术类型_推断", "服务类型_推断", "面向用户_推断", "状态", "出箱日期",
              "登记/测试开始公告日期", "公示公告链接", "登记公告链接", "出箱公告链接", "备注"]
    out = os.path.join(ROOT, "work", "projects.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("projects", len(rows))
    print(Counter(r["状态"] for r in rows))
    print("end records", len(end_list), "matched", len(matched),
          "only-end rows", sum(1 for r in rows if r["备注"]))
    return rows


if __name__ == "__main__":
    main()
