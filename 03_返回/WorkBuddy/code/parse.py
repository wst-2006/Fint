"""轻量 HTML 解析：把页面解析成树，抽表格与正文文本。"""
from html.parser import HTMLParser
import re

VOID = {"br", "img", "input", "meta", "link", "hr", "area", "base", "col", "embed",
        "param", "source", "track", "wbr"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []
        self.parent = parent

    def add_text(self, t):
        self.children.append(t)

    def iter(self, tag=None):
        for c in self.children:
            if isinstance(c, Node):
                if tag is None or c.tag == tag:
                    yield c
                yield from c.iter(tag)

    def get_text(self, sep=""):
        out = []
        for c in self.children:
            if isinstance(c, str):
                out.append(c)
            else:
                if c.tag in ("script", "style"):
                    continue
                if c.tag in ("br", "p", "div", "tr", "td", "li"):
                    out.append(sep)
                out.append(c.get_text(sep))
        return "".join(out)


class Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root:
            if n.tag == tag:
                self.cur = n.parent
                return
            n = n.parent

    def handle_data(self, data):
        if data.strip():
            self.cur.add_text(data)


def parse_html(html):
    b = Builder()
    b.feed(html)
    return b.root


def clean(s):
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    s = re.sub(r"[ \t\r\n]+", " ", s)
    return s.strip()


def tables_with(root, must=()):
    """返回所有表格 (rows)，rows 为 [[cell_text,...],...]；只取直接 tr（含嵌套表时取外层）。"""
    out = []
    for t in root.iter("table"):
        rows = []
        for tr in t.iter("tr"):
            # 跳过属于嵌套表格的 tr
            p = tr.parent
            nested = False
            while p is not None and p is not t:
                if p.tag == "table":
                    nested = True
                    break
                p = p.parent
            if nested:
                continue
            cells = [clean(td.get_text(" ")) for td in tr.children
                     if isinstance(td, Node) and td.tag in ("td", "th")]
            if cells:
                rows.append(cells)
        if not rows:
            continue
        flat = " ".join(" ".join(r) for r in rows)
        if all(m in flat for m in must):
            out.append(rows)
    return out


def main_text(root):
    body = next(root.iter("body"), root)
    txt = body.get_text("\n")
    lines = [clean(x) for x in txt.split("\n")]
    return [x for x in lines if x]
