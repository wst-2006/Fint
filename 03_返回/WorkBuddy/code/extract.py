"""从公告详情页抽取结构化字段。"""
import re, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse import parse_html, tables_with, main_text

PROV = ["北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江", "上海", "江苏",
        "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "广西",
        "海南", "重庆", "四川", "贵州", "云南", "西藏", "陕西", "甘肃", "青海", "宁夏",
        "新疆", "深圳", "宁波", "厦门", "青岛", "大连", "雄安"]


def norm_region(s):
    if not s:
        return ""
    s = s.strip()
    for p in PROV:
        if p in s:
            return p
    if "上海总部" in s:
        return "上海"
    return s


def get_region(lines, url):
    for ln in lines[:40]:
        m = re.search(r"我的位置[:：]\s*(.+)$", ln)
        if m:
            return norm_region(m.group(1).split(">")[0])
    m = re.match(r"https?://([a-z]+)\.pbc\.gov\.cn", url or "")
    if m:
        mp = {"beijing": "北京", "tianjin": "天津", "shijiazhuang": "河北", "taiyuan": "山西",
              "huhehaote": "内蒙古", "shenyang": "辽宁", "dalian": "大连", "changchun": "吉林",
              "haerbin": "黑龙江", "shanghai": "上海", "nanjing": "江苏", "hangzhou": "浙江",
              "hefei": "安徽", "fuzhou": "福建", "xiamen": "厦门", "nanchang": "江西",
              "jinan": "山东", "qingdao": "青岛", "zhengzhou": "河南", "wuhan": "湖北",
              "changsha": "湖南", "guangzhou": "广东", "shenzhen": "深圳", "nanning": "广西",
              "haikou": "海南", "chongqing": "重庆", "chengdu": "四川", "guiyang": "贵州",
              "kunming": "云南", "lasa": "西藏", "xian": "陕西", "lanzhou": "甘肃",
              "xining": "青海", "yinchuan": "宁夏", "wulumuqi": "新疆", "ningbo": "宁波"}
        return mp.get(m.group(1), m.group(1))
    return ""


def get_date(lines, html):
    for ln in lines[:60]:
        m = re.search(r"(20\d{2})-(\d{2})-(\d{2})[ T]\d{2}:\d{2}", ln)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r'createDate"\s+content="(20\d{2})-(\d{2})-(\d{2})', html)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def get_title(lines, html):
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def classify(title, text):
    t = title + " " + " ".join(text[:60])
    if "结束测试" in t or "出箱" in t:
        return "END"
    if "测试运行" in t or "提供服务" in t or "登记" in t:
        return "SERV"
    if "公示" in t:
        return "PUB"
    if "征集" in t:
        return "CALL"
    return "OTHER"


HEADER_MAP = [("name", ["创新应用名称", "应用名称", "项目名称"]),
              ("type", ["创新应用类型", "应用类型"]),
              ("inst", ["申请机构", "参与机构", "申报机构", "申请单位"]),
              ("code", ["创新应用编号", "应用编号"]),
              ("time", ["测试开始时间", "拟测试时间", "开始时间"]),
              ("attach", ["声明书", "附件"])]


def parse_table_projects(rows):
    """在表格中找表头行，按列名映射，返回项目行列表。"""
    out = []
    for t in rows:
        hdr_i, cmap = None, {}
        for i, r in enumerate(t[:3]):
            joined = " ".join(r)
            if ("名称" in joined and "机构" in joined):
                hdr_i = i
                for j, cell in enumerate(r):
                    for key, keys in HEADER_MAP:
                        if key in cmap:
                            continue
                        if any(k in cell for k in keys):
                            cmap[key] = j
                            break
                break
        if hdr_i is None:
            continue
        for r in t[hdr_i + 1:]:
            if len(r) < 2:
                continue
            def g(k):
                j = cmap.get(k)
                return r[j].strip() if j is not None and j < len(r) else ""
            name = g("name")
            if not name or name in ("序号",) or len(name) < 4:
                continue
            if not re.search(r"[\u4e00-\u9fa5]", name):
                continue
            out.append({"name": clean_name(name), "app_type": g("type"),
                        "inst": g("inst"), "code": g("code"), "time": g("time"),
                        "attach": g("attach")})
    return out


def clean_name(s):
    s = re.sub(r"\s+", "", s)
    s = s.strip("　 ")
    return s


def parse_end_text(text):
    """解析结束测试公告：返回 [{'inst','name','code','type'}]"""
    out = []
    joined = " ".join(text)
    joined = re.sub(r"^.*?以下\s*\d+\s*个[^：:]{0,20}(?:结束测试|完成测试)[：:]", "", joined)
    joined = re.sub(r"^.*?(?:结束测试|完成测试)[：:]\s*(?=[一二三四五六七八九十0-9])", "", joined)
    # 按序号切分
    parts = re.split(r"(?:^|\s)[一二三四五六七八九十]+、|(?:^|\s)\d{1,2}[.、]", joined)
    for p in parts:
        if "成功完成测试" not in p and "结束测试" not in p:
            continue
        m = re.search(r"^(.*?)申报的[“\"](.+?)[”\"]", p)
        if not m:
            m = re.search(r"^(.*?)申请的[“\"](.+?)[”\"]", p)
        if not m:
            m = re.search(r"[“\"](.+?)[”\"].*?(?:申报|申请)", p)
            if m:
                out.append({"inst": "", "name": clean_name(m.group(1)), "code": "", "type": ""})
            continue
        inst, name = m.group(1), m.group(2)
        inst = re.sub(r"^.*?的", "", inst) if "的" in inst and len(inst) > 60 else inst
        code = re.search(r"创新应用编号[:：]\s*([0-9A-Za-z\-]+)", p)
        typ = re.search(r"创新应用类型[:：]\s*([\u4e00-\u9fa5]+)", p)
        out.append({"inst": inst.strip("，,。 "), "name": clean_name(name),
                    "code": code.group(1) if code else "",
                    "type": typ.group(1) if typ else ""})
    return out


def extract(path, url=""):
    html = open(path, encoding="utf-8", errors="ignore").read()
    root = parse_html(html)
    lines = main_text(root)
    title = get_title(lines, html)
    date = get_date(lines, html)
    region = get_region(lines, url)
    kind = classify(title, lines)
    rows = [t for t in tables_with(root) if max(len(x) for x in t) >= 3]
    res = {"title": title, "date": date, "region": region, "kind": kind,
           "projects": [], "ended": [], "text_head": " ".join(lines[:80])[:1200]}
    if kind in ("PUB", "SERV"):
        res["projects"] = parse_table_projects(rows)
    if kind == "END":
        res["ended"] = parse_end_text(lines)
        # 有些结束测试也用表格
        if not res["ended"]:
            res["projects"] = parse_table_projects(rows)
    if kind == "OTHER":
        res["projects"] = parse_table_projects(rows)
        res["ended"] = parse_end_text(lines)
    return res


if __name__ == "__main__":
    import glob
    for p in sys.argv[1:]:
        r = extract(p)
        print(json.dumps({k: v for k, v in r.items() if k != "text_head"},
                         ensure_ascii=False)[:800])
        print("  title:", r["title"][:60], "| date", r["date"], "| region", r["region"], "|", r["kind"])
