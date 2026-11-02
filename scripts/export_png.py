# Export active AutoCAD drawing to PNG via COM plot (no screen capture).
# ASCII-only paths. Usage: python export_png.py [out_path]
import os
import sys
import time

import win32com.client

out = sys.argv[1] if len(sys.argv) > 1 else r'D:\CAD_tools\output\drawing.png'
app = win32com.client.GetActiveObject('AutoCAD.Application')
doc = app.ActiveDocument
print('doc =', doc.Name)

# COM boundary can reject calls for 1-2s after doc open/switch; bounded retry
layout = None
for _ in range(10):
    try:
        layout = doc.ActiveLayout
        break
    except Exception:
        time.sleep(1)
if layout is None:
    print('FAIL: cannot attach ActiveLayout')
    sys.exit(3)

layout.ConfigName = 'PublishToWeb PNG.pc3'
layout.PlotType = 1          # extents
layout.CenterPlot = True
layout.StandardScale = 0     # scale to fit
layout.PlotWithLineweights = True
doc.Plot.QuietErrorMode = True

if os.path.exists(out):
    os.remove(out)
ok = doc.Plot.PlotToFile(out)

# PlotToFile returns before the file is fully written - poll for it
for _ in range(15):
    if os.path.exists(out) and os.path.getsize(out) > 0:
        print('OK', out, os.path.getsize(out), 'bytes')
        sys.exit(0)
    time.sleep(2)
print('PLOT returned', ok, 'but file never appeared:', out)
sys.exit(4)
