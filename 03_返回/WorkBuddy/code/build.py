"""汇总为项目级清单，并做技术/服务类型标注。"""
import json, os, re, csv, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import extract

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TECH = [
    ("大模型", ["大模型", "LLM", "生成式", "AIGC", "智能体"]),
    ("人工智能（不含大模型）", ["人工智能", "AI", "机器学习", "深度学习", "神经网络", "智能算法",
                        "知识图谱", "自然语言", "NLP", "OCR", "计算机视觉", "图像识别",
                        "语音识别", "生物识别", "人脸识别", "智能风控", "智能", "算法"]),
    ("区块链", ["区块链", "分布式账本", "智能合约", "链上"]),
    ("隐私计算", ["隐私计算", "多方安全计算", "联邦学习", "可信执行环境", "TEE", "同态加密",
              "安全多方", "差分隐私", "数据可用不可见"]),
    ("大数据", ["大数据", "数据仓库", "数据中台", "数据挖掘", "数据治理", "数据要素", "数据资产"]),
    ("云计算/分布式架构", ["云计算", "云原生", "分布式", "微服务", "容器"]),
    ("应用程序接口API", ["API", "接口", "开放银行"]),
    ("卫星遥感/地理信息", ["遥感", "卫星", "地理信息", "GIS", "北斗"]),
    ("物联网/5G", ["物联网", "IoT", "5G", "传感器", "车联网"]),
    ("机器人/数字人", ["机器人", "数字人", "虚拟人", "RPA", "流程自动化"]),
    ("数字孪生/三维建模", ["数字孪生", "3D", "三维"]),
    ("密码/电子认证", ["密码", "加密", "电子签名", "数字证书", "CA", "电子认证", "可信身份"]),
    ("图计算/图数据库", ["图计算", "图数据库", "关系网络"]),
    ("流计算/实时计算", ["流计算", "实时计算", "实时风控"]),
]

SERV = [
    ("信贷/融资", ["信贷", "贷款", "授信", "融资", "贷前", "贷中", "贷后", "风控", "信用评分", "额度"]),
    ("支付结算", ["支付", "收单", "结算", "清算", "账户", "钱包", "条码", "二维码"]),
    ("财富管理/理财", ["理财", "投顾", "基金", "财富", "资产配置", "存款", "养老"]),
    ("保险", ["保险", "理赔", "投保", "承保"]),
    ("供应链金融", ["供应链", "应收", "保理", "票据", "信用证"]),
    ("普惠/小微", ["普惠", "小微", "个体工商户", "三农", "助农", "乡村", "农户"]),
    ("绿色金融", ["绿色", "碳", "ESG", "气候"]),
    ("跨境/贸易金融", ["跨境", "贸易", "外汇", "出海", "自贸"]),
    ("营销/客户运营", ["营销", "获客", "客户运营", "客户服务", "客服", "智能助手"]),
    ("合规/反洗钱/监管科技", ["反洗钱", "合规", "监管", "报送", "风险监测", "反欺诈", "欺诈"]),
    ("征信/信用服务", ["征信", "信用", "评级"]),
    ("内部运营/科技管理", ["运营", "运维", "研发", "办公", "人力", "财务", "数据管理", "驾驶舱"]),
]

USERS = [
    ("个人消费者", ["个人", "消费", "零售", "手机银行", "客户体验", "百姓", "居民"]),
    ("小微企业", ["小微", "个体工商户", "商户", "普惠"]),
    ("企业/对公客户", ["企业", "对公", "公司", "供应链", "产业", "制造业"]),
    ("农户/农村经营主体", ["农户", "农村", "农业", "助农", "乡村"]),
    ("金融机构", ["同业", "银行间", "金融机构", "托管", "清算机构"]),
    ("政府/公共部门", ["政务", "政府", "医保", "社保", "公积金", "税务", "海关"]),
]


def tag(name, rules):
    hits = []
    for label, kws in rules:
        if any(k.lower() in name.lower() for k in kws):
            hits.append(label)
    return hits


def main():
    anns = json.load(open(os.path.join(ROOT, "work", "announcements.json"), encoding="utf-8"))
    results = []
    for i, a in enumerate(anns):
        import hashlib
        h = hashlib.md5(a["urls"][0].encode()).hexdigest()[:12]
        if not a.get("page"):
            a["page"] = f"raw/pages/{a['date']}_{h}.html"
        p = os.path.join(ROOT, a["page"])
        if not p or not os.path.exists(p):
            continue
        try:
            r = extract(p, a["urls"][0])
        except Exception as e:
            r = {"title": a["title"], "date": a["date"], "region": "", "kind": "ERR",
                 "projects": [], "ended": [], "err": str(e)}
        r["src"] = a["urls"][0]
        r["src_all"] = a["urls"]
        r["list_title"] = a["title"]
        r["list_date"] = a["date"]
        results.append(r)
        if i % 100 == 0:
            print(i, len(anns), flush=True)
    json.dump(results, open(os.path.join(ROOT, "work", "extracted.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(r["kind"] for r in results))
    print("projects:", sum(len(r["projects"]) for r in results),
          "ended:", sum(len(r["ended"]) for r in results))


if __name__ == "__main__":
    main()
