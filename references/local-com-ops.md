# 本机 COM 实战笔记：AutoCAD 2027 @ 中文 Win11 + PS5.1 + Python 3.14/pywin32（原独立技能 autocad-com-ops，2026-10 并入 autocad-drawing）

# AutoCAD COM 实战经验（本机）

本机环境：AutoCAD 2027（`D:\autocad\AutoCAD 2027\acad.exe`）、中文 Win11、PowerShell 5.1、Python 3.14（`python3.14`，`python`/`python3` 不存在）+ pywin32。

## 已安装的 CAD 技能（2026-10-03 装入）

| 技能 | 来源 | 角色 |
|---|---|---|
| `autocad-drawing` | MiaTxxx/autocad-skill-marketplace（zipball 装入） | 核心：规格 JSON → cad_ai.py 落图 → 回读校验 |
| `cad-automation` | delancy827/cad-skills (74★) | COM/LISP/批量/国产CAD 知识库 |
| `cad-designer` | delancy827/cad-skills | 制图设计流程 |

安全扫描：18 分 LOW / 37 分 MEDIUM；仅有的 2 个 HIGH 核实均为误报（技能读自己的 `CAD_LLM_MODEL` 环境变量；SKILL.md frontmatter 被当 Hidden Instructions）。skill 副本与脚本在 `D:\CAD_tools\`（ASCII 路径），成品 `D:\CAD_tools\output\`。

## 已验证的端到端流水线

```powershell
# 0. 输出目录必须先建（AutoCAD SaveAs 不自建目录，否则画完才崩）
New-Item -ItemType Directory -Force -Path 'D:\CAD_tools\output'
# 1. 写规格 JSON（part.outline/holes/polygons/circles/centerlines + output.dwg）
# 2. 预检：不碰 CAD，两条算路互证周长/面积
python3.14 D:\CAD_tools\cad_ai.py --spec spec.json --dry-run
# 3. --clear 清的是当前活动文档！先关掉用户开着的图纸：
python3.14 -c "import win32com.client; win32com.client.GetActiveObject('AutoCAD.Application').ActiveDocument.Close(False)"
# 4. 落图 + 回读（输出目录必须已存在）
python3.14 D:\CAD_tools\cad_ai.py --spec spec.json --clear --force
# 5. 交付配图：COM 出图 PNG（不要截屏！）
python3.14 D:\CAD_tools\export_png.py D:\CAD_tools\output\plate.png
```

回读校验输出逐图元列出「期望 vs CAD 实测」，12/12 匹配才算完成；只报"画完了"不给回读表 = 未完成（安装技能的铁律）。

## 本机额外坑（安装技能 SKILL.md 之外）

1. **SaveAs 前确认输出目录存在**——否则落图成功、保存才报 com_error「保存文档时出错」。
2. **`diagonal_extent`/`axis_extent` 是半长且须伸出轮廓外**：连接板案例里斜中心线半长 60 被拒（要求 ≥101.2），直接给伸出量（如 115）。
3. **交付配图禁用截屏**：SetForegroundWindow 提前台后会被顶掉，连截两次都是空白桌面。用 `scripts/export_png.py`（PublishToWeb PNG.pc3，extents+CenterPlot+ScaleToFit）；**PlotToFile 异步落盘**，返回 True ≠ 文件已存在，必须轮询到 size>0（脚本已内置）。
4. **PS5.1 手写 COM 落图脚本三坑**（详见面板参考文件）：方法必须逗号传参；坐标一律内联 `[double[]]@(x,y,0)`（封装函数返回会丢类型报 "Value does not fall within the expected range"）；脚本含中文必须 UTF-8 BOM，否则 SaveAs 落乱码目录且 `Test-Path` 同字符串验证是假阳性。
5. **PowerShell 侧 COM 只适合轻量探针/开关**（附着、关闭文档、WindowState），画图一律走 cad_ai.py 的 Python VARIANT 路线。

## 实测锚点（回归对照）

170×110 圆角矩形 R18 + 四角 Ø12 孔（与圆角同心）+ 六边形对边距 32 + Ø50/Ø28 同心圆：
- dry-run：周长 529.0973（=2(w−2r)+2(h−2r)+2πr）、面积 18421.8760
- 回读：4 孔圆心 (±67,±37)、六边形 L=110.8513/A=886.81、对角线 L=325.2691、12/12 PASS
