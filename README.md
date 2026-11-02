# AutoCAD 参数化绘图

> 用 COM / ActiveX 驱动本机正在运行的 AutoCAD，按参数化规格画图、改图和读图：给定尺寸就能画出零件图与平面图，画完回读几何做校验，导出 dwg 与 PNG。适合要按确定尺寸出图、或者要反复改同一张图参数的情况。工具脚本附带 dry-run 预演，先看画什么再落笔。

**版本** 1.0.0 ｜ **技能名** `autocad-drawing`

模型只把需求翻译成规格 JSON；几何与算式由 Python 算；落图由 COM 执行；画得对不对由回读数据判定。任何"应该画上了"的结论都不算完成。

## 用法

```
/marketplace add <本地路径 或 github owner/repo>
/marketplace install autocad-drawing@autocad-skill-marketplace
```

## 安装

```bash
# 方式一：直接链接安装（Hermes Agent）
hermes skills install https://github.com/WilliamWang6586/hermes-skills/tree/main/autocad-drawing

# 方式二：手动拷贝
git clone https://github.com/WilliamWang6586/hermes-skills.git && cp -r hermes-skills/autocad-drawing ~/AppData/Local/hermes-home/skills/
```

## 文件

- `SKILL.md`
- `references/autocad-com-notes.md`
- `references/local-com-ops.md`
- `references/win11-autocad2027-notes.md`
- `scripts/cad_ai.py`
- `scripts/export_png.py`
- `scripts/nl2spec.py`
- `scripts/selftest_security.py`

## 说明

本技能收录于 [hermes-skills](https://github.com/WilliamWang6586/hermes-skills)，每个技能独立成目录、独立维护。内容若参考第三方项目，见本目录 `ATTRIBUTION.md`。
