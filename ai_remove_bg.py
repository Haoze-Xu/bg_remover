"""
AI 语义抠图工具 (rembg)

支持多种模型:
  - isnet-anime  二次元/动漫插画专精（默认）
  - u2net        通用真实照片
  - isnet-general-use  新一代通用模型

用法:
    python ai_remove_bg.py
    python ai_remove_bg.py input.jpg output.png
    python ai_remove_bg.py input.jpg output.png -m u2net
"""

import argparse
import os
import sys
from PIL import Image
from rembg import remove, new_session


# 可用模型列表
MODELS = {
    "isnet-anime": "二次元/动漫插画专精 (ISNet-Anime)",
    "u2net": "通用真实照片 (U²-Net)",
    "isnet-general-use": "新一代通用模型 (ISNet-General-Use)",
}


def semantic_remove_bg(input_path, output_path, model="isnet-anime"):
    """
    使用 rembg 进行语义级背景移除。
    model: 模型名称，默认 isnet-anime（二次元专精）
    """
    if not os.path.exists(input_path):
        print(f"[ERROR] File not found: {input_path}")
        return False

    model_desc = MODELS.get(model, model)
    print(f"Model: {model_desc}")
    print(f"Loading and processing: {input_path}")
    print("  (first run downloads model weights ~170MB, please wait...)")

    try:
        session = new_session(model)
        input_image = Image.open(input_path)
        # post_process=False: 二次元边缘更干净，不会过度侵蚀发丝
        output_image = remove(input_image, session=session, post_process=False)
        output_image.save(output_path, "PNG")
        print(f"[OK] Saved to: {output_path}")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="AI 语义抠图 — 使用深度学习区分人物与背景"
    )
    parser.add_argument("input", nargs="?", default="stardust.jpg",
                        help="输入图片路径")
    parser.add_argument("output", nargs="?", default="",
                        help="输出图片路径（默认: xxx_ai_transparent.png）")
    parser.add_argument("-m", "--model", choices=list(MODELS.keys()),
                        default="isnet-anime",
                        help="AI 模型选择（默认: isnet-anime）")
    args = parser.parse_args()

    output = args.output
    if not output:
        base = args.input.rsplit(".", 1)[0]
        output = f"{base}_ai_transparent.png"
    if not output.lower().endswith(".png"):
        print("[WARN] Output is not .png, auto-fixing to .png")
        output = output.rsplit(".", 1)[0] + ".png"

    semantic_remove_bg(args.input, output, args.model)


if __name__ == "__main__":
    main()
