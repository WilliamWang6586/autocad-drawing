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

把本目录整个复制到你的 agent 技能目录（如 `~/.agent/skills/` 或所用工具的 skills 目录）：

```bash
git clone https://github.com/WilliamWang6586/autocad-drawing.git
cp -r autocad-drawing "<你的技能目录>/"
```

放进去后，agent 读到 `SKILL.md` 即可按其中的触发条件调用。

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

