# bg_remover

图片背景移除工具箱，提供两种方案：

| 方案 | 文件 | 原理 | 适用场景 |
|------|------|------|----------|
| 🧠 AI 语义抠图 | `ai_remove_bg.py` | 深度学习（rembg） | 二次元/人物/复杂背景 |
| 🎯 白色背景清除 | `remove_bg.py` | 传统图像处理 | 纯白背景产品图/证件照 |

---

## 安装

```bash
pip install -r requirements.txt
```

> 首次运行 AI 抠图时会自动下载模型权重（约 170MB）。

---

## 使用

### AI 语义抠图

```bash
# 默认模型 isnet-anime（二次元专精）
python ai_remove_bg.py input.jpg

# 指定模型与输出路径
python ai_remove_bg.py photo.jpg output.png -m u2net
```

可选模型：

| 模型 | 说明 |
|------|------|
| `isnet-anime` | 二次元/动漫插画专精（默认） |
| `u2net` | 通用真实照片 |
| `isnet-general-use` | 新一代通用模型 |

### 白色背景转透明

```bash
# 默认参数
python remove_bg.py product.jpg

# 调整容差 + 边缘侵蚀
python remove_bg.py input.jpg output.png -t 50 --grow 3

# 开启智能空洞检测
python remove_bg.py input.jpg output.png --hole-dist 3
```

参数说明：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-t, --tolerance` | 白色容差值（0-255，越小越严格） | 30 |
| `--grow` | 透明度向内侵蚀次数（0=关闭） | 2 |
| `--hole-dist` | 智能空洞：移除距透明背景 ≤N px 的内部白色区域（0=关闭） | 0 |

### 处理流程

```
① 边缘洪水填充  →  ② 透明度侵蚀  →  ③ 智能空洞移除
   去掉与边缘相连         向内削一层             处理封闭内部白块
   的白色背景             减少白边残留            （如手臂间隙）
```

---

## License

MIT
