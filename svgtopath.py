import re
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = "{http://www.w3.org/2000/svg}"
_NUM = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'


# ---------- 仿射矩阵 (a b c d e f) ----------
def _identity():
    return (1, 0, 0, 1, 0, 0)


def _mat_mul(m, n):
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
        e1 * a2 + f1 * c2 + e2,
        e1 * b2 + f1 * d2 + f2,
    )


def parse_transform(s):
    import math
    m = _identity()
    if not s:
        return m
    for name, vals in re.findall(r'(\w+)\s*\(([^)]*)\)', s):
        nums = [float(x) for x in re.split(r'[,\s]+', vals.strip())]
        if name == "translate":
            tx = nums[0]; ty = nums[1] if len(nums) > 1 else 0
            m = _mat_mul(m, (1, 0, 0, 1, tx, ty))
        elif name == "scale":
            sx = nums[0]; sy = nums[1] if len(nums) > 1 else sx
            m = _mat_mul(m, (sx, 0, 0, sy, 0, 0))
        elif name == "rotate":
            ang = nums[0] * math.pi / 180
            ca, sa = math.cos(ang), math.sin(ang)
            if len(nums) == 3:
                cx, cy = nums[1], nums[2]
                m = _mat_mul(m, (1, 0, 0, 1, cx, cy))
                m = _mat_mul(m, (ca, sa, -sa, ca, 0, 0))
                m = _mat_mul(m, (1, 0, 0, 1, -cx, -cy))
            else:
                m = _mat_mul(m, (ca, sa, -sa, ca, 0, 0))
        elif name == "matrix":
            m = _mat_mul(m, tuple(nums))
        elif name == "skewX":
            v = math.tan(nums[0] * math.pi / 180)
            m = _mat_mul(m, (1, 0, v, 1, 0, 0))
        elif name == "skewY":
            v = math.tan(nums[0] * math.pi / 180)
            m = _mat_mul(m, (1, v, 0, 1, 0, 0))
    return m


def _apply_pt(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


# ---------- 图元 → path d ----------
def _rect_d(e):
    x = float(e.get("x", 0)); y = float(e.get("y", 0))
    w = float(e.get("width")); h = float(e.get("height")); rx = e.get("rx")
    if rx:
        r = float(rx)
        return (f"M{x+r},{y} H{x+w-r} A{r},{r} 0 0 1 {x+w},{y+r} "
                f"V{y+h-r} A{r},{r} 0 0 1 {x+w-r},{y+h} H{x+r} "
                f"A{r},{r} 0 0 1 {x},{y+h-r} V{y+r} A{r},{r} 0 0 1 {x+r},{y} Z")
    return f"M{x},{y} H{x+w} V{y+h} H{x} Z"


def _circle_d(e):
    cx = float(e.get("cx")); cy = float(e.get("cy")); r = float(e.get("r"))
    return (f"M{cx-r},{cy} A{r},{r} 0 1 0 {cx+r},{cy} "
            f"A{r},{r} 0 1 0 {cx-r},{cy} Z")


def _ellipse_d(e):
    cx = float(e.get("cx")); cy = float(e.get("cy"))
    rx = float(e.get("rx")); ry = float(e.get("ry"))
    return (f"M{cx-rx},{cy} A{rx},{ry} 0 1 0 {cx+rx},{cy} "
            f"A{rx},{ry} 0 1 0 {cx-rx},{cy} Z")


def _poly_d(e, closed=True):
    pts = [float(p) for p in re.split(r'[\s,]+', e.get("points").strip())]
    d = f"M{pts[0]},{pts[1]}"
    for i in range(2, len(pts), 2):
        d += f" L{pts[i]},{pts[i+1]}"
    return d + (" Z" if closed else "")


def _prim_d(node):
    tag = node.tag.replace(SVG, "")
    if tag == "rect":
        return _rect_d(node)
    if tag == "circle":
        return _circle_d(node)
    if tag == "ellipse":
        return _ellipse_d(node)
    if tag in ("polygon", "polyline"):
        return _poly_d(node, tag == "polygon")
    if tag == "path":
        return node.get("d", "")
    return None


# ---------- d 字符串按命令烘焙矩阵 ----------
def _transform_d(d, m):
    import math
    tokens = re.findall(r'[a-zA-Z]|' + _NUM, d)
    out = []
    k = 0
    cur = [0.0, 0.0]     # 用户坐标系（未变换）下的当前点
    start = [0.0, 0.0]   # 当前子路径起点
    cmd = None
    mfirst = False       # 当前 m 命令是否为第一组参数（隐式重复按 lineto 处理）
    axis = (m[1] == 0 and m[2] == 0)          # 无旋转/斜切时 H/V 可保留
    det = m[0] * m[3] - m[1] * m[2]           # 负值表示镜像
    sx = math.hypot(m[0], m[1]) or 1.0
    sy = math.hypot(m[2], m[3]) or 1.0
    ang = math.degrees(math.atan2(m[1], m[0]))

    def read_pt():
        nonlocal k
        x = float(tokens[k]); y = float(tokens[k + 1]); k += 2
        return x, y

    def put(letter, *vals):
        out.append(letter)
        out.extend(v if isinstance(v, str) else f"{v:.3f}" for v in vals)

    while k < len(tokens):
        t = tokens[k]
        if t.isalpha():
            cmd = t
            if t.lower() == 'z':
                cur[:] = start[:]   # 闭合后当前点回到子路径起点
            mfirst = (t.lower() == 'm')
            k += 1
            continue

        if cmd is None:   # 数字出现在任何命令之前（非法数据），跳过
            k += 1
            continue

        c = cmd.lower()
        rel = cmd.islower()

        if c in ('m', 'l', 't'):
            x, y = read_pt()
            ax, ay = (cur[0] + x, cur[1] + y) if rel else (x, y)
            if c == 'm' and mfirst:
                put('M', *_apply_pt(m, ax, ay))
                start[:] = [ax, ay]
            else:
                put('L' if c != 't' else 'T', *_apply_pt(m, ax, ay))
            cur[:] = [ax, ay]
            mfirst = False

        elif c in ('h', 'v'):
            v = float(tokens[k]); k += 1
            if c == 'h':
                ax = cur[0] + v if rel else v
                ay = cur[1]
            else:
                ax = cur[0]
                ay = cur[1] + v if rel else v
            nx, ny = _apply_pt(m, ax, ay)
            if axis:
                put('H' if c == 'h' else 'V', nx if c == 'h' else ny)
            else:
                put('L', nx, ny)
            cur[:] = [ax, ay]

        elif c == 'c':
            x1, y1 = read_pt(); x2, y2 = read_pt(); x, y = read_pt()
            if rel:
                x1 += cur[0]; y1 += cur[1]
                x2 += cur[0]; y2 += cur[1]
                x += cur[0]; y += cur[1]
            put('C', *_apply_pt(m, x1, y1), *_apply_pt(m, x2, y2), *_apply_pt(m, x, y))
            cur[:] = [x, y]

        elif c == 's':
            x2, y2 = read_pt(); x, y = read_pt()
            if rel:
                x2 += cur[0]; y2 += cur[1]
                x += cur[0]; y += cur[1]
            put('S', *_apply_pt(m, x2, y2), *_apply_pt(m, x, y))
            cur[:] = [x, y]

        elif c == 'q':
            x1, y1 = read_pt(); x, y = read_pt()
            if rel:
                x1 += cur[0]; y1 += cur[1]
                x += cur[0]; y += cur[1]
            put('Q', *_apply_pt(m, x1, y1), *_apply_pt(m, x, y))
            cur[:] = [x, y]

        elif c == 'a':
            rx = float(tokens[k]); ry = float(tokens[k + 1])
            rot = float(tokens[k + 2])
            large = tokens[k + 3]; sweep = tokens[k + 4]
            x = float(tokens[k + 5]); y = float(tokens[k + 6])
            k += 7
            ax, ay = (cur[0] + x, cur[1] + y) if rel else (x, y)
            if det < 0:  # 镜像时扫掠方向翻转
                sweep = '1' if sweep == '0' else '0'
            # 半径按缩放近似处理，旋转角叠加矩阵旋转角（非均匀缩放时为近似）
            put('A', rx * sx, ry * sy, rot + ang, large, sweep,
                *_apply_pt(m, ax, ay))
            cur[:] = [ax, ay]

        else:
            k += 1  # 跳过未知/无参数命令后残留的 token，避免死循环

    return " ".join(out)


# ---------- 递归遍历 ----------
def _walk(node, mat, out):
    tag = node.tag.replace(SVG, "")
    if tag == "g":
        m = _mat_mul(mat, parse_transform(node.get("transform")))
        for c in node:
            _walk(c, m, out)
        return
    d = _prim_d(node)
    if d:
        out.append(_transform_d(d, mat))
    # svg / defs 等容器也继续往下走
    for c in node:
        _walk(c, mat, out)


# ---------- 对外接口 ----------
def svg_to_path_data(svg_text, merge=False):
    """返回 list[str]；merge=True 时合并为单个 Data 字符串"""
    root = ET.fromstring(svg_text)
    out = []
    _walk(root, _identity(), out)
    if merge:
        return " ".join(out)
    return out


def write_geometry_dict(datas, path, prefix="Icon"):
    lines = ['<ResourceDictionary '
             'xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
             'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">']
    for i, d in enumerate(datas):
        lines.append(f'  <Geometry x:Key="{prefix}_{i}">{d}</Geometry>')
    lines.append('</ResourceDictionary>')
    Path(path).write_text("\n".join(lines), encoding="utf-8")


# ---------- 自测 ----------
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        svg_text = Path(sys.argv[1]).read_text(encoding="utf-8")
        datas = svg_to_path_data(svg_text)
        print(f"// {len(datas)} paths")
        for i, d in enumerate(datas):
            print(f"// [{i}] {d[:80]}...")
        print(svg_to_path_data(svg_text, merge=True))