# 本机实测细节：AutoCAD 2027 @ 中文 Win11（PS5.1 / Python 3.14）

2026-10-03 首次全流程实测（传动连接板，12 图元回读 12/12）。

## 实测锚点（回归对照）

规格：170×110 圆角矩形 R18 + 四角 Ø12 孔（与圆角同心，即 inset 默认 [r,r]）+ 正六边形对边距 32 + Ø50/Ø28 同心圆 + 轴线半长 100 + 对角中心线半长 115。

- dry-run 双算路：周长 529.0973 = 2(w−2r)+2(h−2r)+2πr ✓；面积 18421.8760 ✓
- 落图回读 12/12 全匹配：4 孔圆心 (±67, ±37)、六边形 L=110.8513 / A=886.81、对角线 L=325.2691
- 校验器规则实测：`diagonal_extent`（斜中心线半长）必须伸出轮廓外（本例 ≥101.2，上界 = max(w,h)），60 被拒、115 通过——写规格直接给伸出量，别按图形内长度给
- 当次成品：`D:\CAD_tools\output\mounting_plate.dwg`；规格副本 `D:\CAD_tools\spec_plate.json`；cad_ai.py 副本 `D:\CAD_tools\`（ASCII 路径）

## PS5.1 → COM 互操作三坑（手写 PS 落图脚本时）

1. .NET/COM 方法必须逗号传参：`$ms.AddCircle($pt, 50)`；写成命令式 `AddCircle (C 0 0) 50` 直接语法错误（Unexpected token '('）。
2. PS 函数返回 `[double[]]` 会被展开成 object[] → COM 报 "Value does not fall within the expected range"。**坐标一律内联 `[double[]]@(x,y,0)`**，不要封装坐标辅助函数。
3. 脚本含中文（含路径字符串）必须 UTF-8 BOM 或干脆纯 ASCII：无 BOM UTF-8 被 PS5.1 按 GBK 解码，SaveAs 落进乱码目录（文档名显示为一串乱码），且用同一乱码字符串做 `Test-Path` 验证是假阳性（saved=True 实为存错地方）。GDI+ 存 CJK 路径同样报 "A generic error occurred in GDI+"。

## 流程级坑（cad_ai.py 使用时）

1. **输出目录先建**：SaveAs 不自建目录，画完才崩（com_error「保存文档时出错」），白画一轮。
2. **`--clear` 清当前活动文档**：先 `doc.Close(False)` 关掉用户开着的图纸再落图。
3. **PlotToFile 异步**：返回 True ≠ 文件已存在，轮询 size>0 再交付。
4. **交付配图禁截屏**：SetForegroundWindow 会被顶掉（实测连截两次空白桌面），走 COM 出图（见 scripts/export_png.py）。
