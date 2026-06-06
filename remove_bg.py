"""
图片白色背景转透明工具

将图片中的白色背景像素的 Alpha 通道设为 0，输出为支持透明的 PNG 格式。

三步处理:
  1. 边缘洪水填充 — 去掉与图片边缘相连的白色背景（安全，不误伤人物）
  2. --grow      透明度向内侵蚀 — 从已透明的边缘往白色区域侵蚀 N 层
  3. --hole-dist 智能空洞检测 — 去掉离透明背景"很近"的内部白色区域

用法:
    python remove_bg.py
    python remove_bg.py input.jpg output.png
    python remove_bg.py input.jpg output.png -t 50 --grow 3
    python remove_bg.py input.jpg output.png --hole-dist 3
"""

import argparse
import sys
from collections import deque
from PIL import Image


def is_whiteish(r, g, b, threshold):
    """判断一个像素是否"接近白色"."""
    return r > threshold and g > threshold and b > threshold


def edge_flood_fill(pixels, width, height, threshold):
    """从四条边出发 BFS，找出所有与边缘连通的白色像素。"""
    visited = set()
    queue = deque()
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    for x in range(width):
        for y in (0, height - 1):
            if (x, y) not in visited:
                r, g, b, a = pixels[x, y]
                if is_whiteish(r, g, b, threshold):
                    queue.append((x, y))
                    visited.add((x, y))
    for y in range(1, height - 1):
        for x in (0, width - 1):
            if (x, y) not in visited:
                r, g, b, a = pixels[x, y]
                if is_whiteish(r, g, b, threshold):
                    queue.append((x, y))
                    visited.add((x, y))

    while queue:
        cx, cy = queue.popleft()
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                r, g, b, a = pixels[nx, ny]
                if is_whiteish(r, g, b, threshold):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    return visited


def compute_distance_map(pixels, width, height):
    """
    从所有透明像素出发 BFS，穿过所有非透明像素（无论颜色），
    计算每个像素到最近透明像素的"跨越步数"。

    返回二维数组 dist[y][x]:
      - 0     = 自己就是透明像素
      - 1..N  = 距离最近透明像素的步数（即"围墙厚度"）
      - -1    = 不可达（理论上不会出现）
    """
    dist = [[-1] * width for _ in range(height)]
    queue = deque()
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    # 所有透明像素作为起点，距离 = 0
    for y in range(height):
        for x in range(width):
            if pixels[x, y][3] == 0:  # alpha == 0 → 透明
                dist[y][x] = 0
                queue.append((x, y))

    # BFS 向外扩散
    while queue:
        cx, cy = queue.popleft()
        nd = dist[cy][cx] + 1
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < width and 0 <= ny < height and dist[ny][nx] == -1:
                dist[ny][nx] = nd
                queue.append((nx, ny))

    return dist


def grow_transparency(pixels, width, height, threshold, iterations):
    """透明度向内侵蚀：把与透明像素相邻的白色像素也变为透明。"""
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    total_grown = 0

    for i in range(iterations):
        to_remove = []
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if a == 0 or not is_whiteish(r, g, b, threshold):
                    continue
                for dx, dy in directions:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and pixels[nx, ny][3] == 0:
                        to_remove.append((x, y))
                        break
        if not to_remove:
            break
        for x, y in to_remove:
            pixels[x, y] = (255, 255, 255, 0)
        total_grown += len(to_remove)

    return total_grown


def remove_near_edge_holes(pixels, width, height, threshold, max_dist):
    """
    智能空洞检测：找到所有内部白色连通区域，
    只去掉那些"离透明背景很近"的区域（围墙厚度 <= max_dist）。

    原理: 背景洞（比如手臂和身体之间）通常只隔了一条细细的人物轮廓线，
     距离透明背景只有 2~4 像素；而白色衣服深藏在人物内部，距离 10+ 像素。
    """
    distance = compute_distance_map(pixels, width, height)
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    # 收集所有剩余的白色像素
    remaining = set()
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 0 and is_whiteish(r, g, b, threshold):
                remaining.add((x, y))

    if not remaining:
        return 0, 0, 0

    # 连通分量分析
    components = []
    while remaining:
        start = remaining.pop()
        comp = {start}
        queue = deque([start])
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in remaining:
                    remaining.remove((nx, ny))
                    comp.add((nx, ny))
                    queue.append((nx, ny))
        components.append(comp)

    # 计算每个分量到透明背景的最短距离
    removed = kept = removed_px = 0
    for comp in components:
        min_dist = min(distance[y][x] for x, y in comp)
        if min_dist <= max_dist:
            for x, y in comp:
                pixels[x, y] = (255, 255, 255, 0)
            removed_px += len(comp)
            removed += 1
        else:
            kept += 1

    return removed, kept, removed_px


def remove_white_background(
    input_path, output_path, tolerance=30, grow=0, hole_dist=None
):
    """
    主处理函数:
      1. 边缘洪水填充
      2. 透明度侵蚀 (--grow)
      3. 智能空洞移除 (--hole-dist)
    """
    img = Image.open(input_path).convert("RGBA")
    pixels = img.load()
    width, height = img.size
    total_pixels = width * height
    threshold = 255 - tolerance

    # === 第一步：边缘洪水填充 ===
    edge_removed = edge_flood_fill(pixels, width, height, threshold)
    for x, y in edge_removed:
        pixels[x, y] = (255, 255, 255, 0)
    print(f"[1/3] Edge flood fill: removed {len(edge_removed)} px "
          f"({100*len(edge_removed)/total_pixels:.1f}%)")

    # === 第二步：透明度侵蚀 ===
    grown = 0
    if grow > 0:
        grown = grow_transparency(pixels, width, height, threshold, grow)
        print(f"[2/3] Grow transparency ({grow} iter): removed {grown} px")
    else:
        print(f"[2/3] Grow transparency: skipped")

    # === 第三步：智能空洞 ===
    hole_removed = hole_kept = hole_px = 0
    if hole_dist is not None and hole_dist > 0:
        hole_removed, hole_kept, hole_px = remove_near_edge_holes(
            pixels, width, height, threshold, hole_dist
        )
        print(f"[3/3] Hole removal (max wall={hole_dist}px): "
              f"removed {hole_removed}, kept {hole_kept}, total {hole_px} px")
    else:
        print(f"[3/3] Hole removal: skipped (use --hole-dist N to enable)")

    img.save(output_path, "PNG")
    total_removed = len(edge_removed) + grown + hole_px
    print(f"---")
    print(f"[OK] Saved to: {output_path}")
    print(f"      total removed {total_removed} px ({100*total_removed/total_pixels:.1f}%), "
          f"tolerance={tolerance}")


def main():
    parser = argparse.ArgumentParser(
        description="去除图片白色背景，生成透明 PNG"
    )
    parser.add_argument("input", nargs="?", default="stardust.jpg",
                        help="输入图片路径")
    parser.add_argument("output", nargs="?", default="",
                        help="输出图片路径（默认: xxx_transparent.png）")
    parser.add_argument("-t", "--tolerance", type=int, default=30,
                        help="白色容差值 0-255（默认: 30）")
    parser.add_argument("--grow", type=int, default=2,
                        help="透明度向内侵蚀次数（默认: 2，设为 0 关闭）")
    parser.add_argument("--hole-dist", type=int, default=0,
                        help="[实验性] 智能空洞: 离透明背景 <=N 像素的封闭白色区域才移除。"
                             "默认 0=关闭。有误伤风险，慎用")

    args = parser.parse_args()

    output = args.output
    if not output:
        base = args.input.rsplit(".", 1)[0]
        output = f"{base}_transparent.png"
    if not output.lower().endswith(".png"):
        print("[WARN] Output is not .png, auto-fixing to .png")
        output = output.rsplit(".", 1)[0] + ".png"

    hd = args.hole_dist if args.hole_dist > 0 else None
    remove_white_background(args.input, output, args.tolerance, args.grow, hd)


if __name__ == "__main__":
    main()
