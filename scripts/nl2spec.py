# -*- coding: utf-8 -*-
"""
自然语言 -> 结构化规格(JSON)。模型只负责"把话说成参数", 不产出任何可执行代码。

对接任意 OpenAI 兼容接口, 用环境变量配置:
  CAD_LLM_BASE_URL  默认 https://api.openai.com/v1
  CAD_LLM_API_KEY   必填
  CAD_LLM_MODEL     默认 gpt-4o-mini

用法:
  python nl2spec.py --text "40x40板, R4圆角, 四角4个Ø4孔与圆角同心, 中心正六边形内切圆Ø20,
                             中心Ø20与Ø10两个圆, 画中心线" --out spec.json
模型输出会被 cad_ai.validate_spec 硬校验; 不合格则回喂错误重试一次。
"""
import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import cad_ai

SCHEMA_DOC = """{
  "part": {
    "outline":  {"type":"rounded_rect", "w":40, "h":40, "r":4, "center":[0,0]},
    "holes":    [{"diameter":4, "origin":"outline_fillet_centers"}],
    "polygons": [{"type":"regular","sides":6,"across_flats":20,"vertex_up":true,"center":[0,0]}],
    "circles":  [{"diameter":20,"center":[0,0]}, {"diameter":10,"center":[0,0]}],
    "centerlines": {"axis_extent": 26, "diagonals":true, "diagonal_extent":29}
  },
  "output": {"dwg": "C:/path/to/out.dwg"},
  "comment": "自由文本"
}"""

SYSTEM = """你是 CAD 参数解析器, 把用户的中文描述翻译成同构的 JSON 规格。
规则:
1. 只输出 JSON 本身, 不要解释、不要 Markdown 代码块、不要产生任何 LISP 或程序代码。
2. 严格只用下面出现的字段名, 不得新增字段(未知字段会被校验器拒绝):
%s
3. 尺寸一律用毫米, 直径写 diameter, 半径写 r; 坐标写 [x, y]。
4. 描述里没提到的可选字段直接省略, 不要猜造。
5. 孔位用 origin 表达: "与圆角同心" -> "outline_fillet_centers"; 给了坐标 -> "centers" + centers 数组。
6. 正多边形: 给对边距用 across_flats, 给外接圆半径用 circumradius, 二者只能有一个。
7. centerlines.axis_extent 与 diagonal_extent 都是"半长"(从中点到端点, 单位 mm), 不是总长;
   中心线应比轮廓略长(超出量几毫米量级), 不要给成远超板面尺寸的数。""" % SCHEMA_DOC


def chat(text, base_url, api_key, model, timeout=120):
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": text}],
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % api_key,
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def extract_json(text):
    """模型偶尔会包 Markdown 围栏或加解释, 这里剥出第一个完整 JSON 对象"""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    start = s.find("{")
    if start < 0:
        raise ValueError("模型输出里没有 JSON 对象")
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(s[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[start:i + 1])
    raise ValueError("JSON 花括号不配对")


ALLOWED_HOSTS = {"api.openai.com", "dashscope.aliyuncs.com", "api.deepseek.com"}


# 提示词注入防护: 用户描述是数据不是指令, 出现这些字样直接拒绝
INJECTION_PATTERNS = re.compile(
    r"(忽略(以上|上面|之前|前面).{0,8}(指令|规则|提示)|ignore\s+(all\s+)?(previous|above)\s+instructions?"
    r"|system\s*prompt|输出(你的)?(系统|初始)提示|你现在是|从现在开始你|"
    r"```|BEGIN\s+SYSTEM|role\s*[:=]\s*\"?(system|assistant)\"?)",
    re.IGNORECASE)


def guard_input(text, max_len=2000):
    """CAD 描述应该只有尺寸与几何词; 超长或含指令性语句一律拒, 防注入"""
    text = (text or "").strip()
    if not text:
        raise SystemExit("[FAIL] 没有输入描述")
    if len(text) > max_len:
        raise SystemExit("[FAIL] 描述过长(%d 字)，疑似非绘图需求" % len(text))
    if INJECTION_PATTERNS.search(text):
        raise SystemExit("[FAIL] 描述里含有指令性语句(忽略规则/系统提示/代码块等)，已拒绝。"
                         "本工具只接受尺寸与几何描述。")
    return text


def check_spec_sane(spec, max_mm=5000.0):
    """模型输出再校验一层: 数值必须有限且在合理范围, 杜绝注入后产出异常参数"""
    bad = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                walk(v)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            if not math.isfinite(o) or abs(o) > max_mm:
                bad.append(o)

    walk(spec)
    if bad:
        raise ValueError("规格含异常数值 %s（超出 ±%gmm 或非有限数）" % (bad[:5], max_mm))


def confirm_outbound(base_url):
    """发送前的数据外发确认：默认不发，必须本人显式同意"""
    if os.environ.get("CAD_LLM_CONFIRM") == "1":
        return
    if not sys.stdin.isatty():
        raise SystemExit(
            "[FAIL] 自然语言转规格会把你的描述发送到 %s。\n"
            "       非交互环境默认拒绝；确认可外发请设 CAD_LLM_CONFIRM=1 或回传 --allow-any-host。" % base_url)
    print("[!] 即将把你的绘图描述发送到: %s" % base_url)
    try:
        ok = input("    确认可外发？(y/N) ").strip().lower() in ("y", "yes")
    except EOFError:
        ok = False
    if not ok:
        raise SystemExit("[FAIL] 用户未确认，已取消，未发送任何数据")


def nl_to_spec(text, base_url=None, api_key=None, model=None, attempts=2, allow_any_host=False):
    base_url = base_url or os.environ.get("CAD_LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = api_key or os.environ.get("CAD_LLM_API_KEY", "")
    model = model or os.environ.get("CAD_LLM_MODEL", "gpt-4o-mini")
    if not api_key:
        raise SystemExit("[FAIL] 未配置 CAD_LLM_API_KEY (环境变量), 无法调用模型")
    text = guard_input(text)          # 输入隔离: 先过注入过滤再进 Prompt
    confirm_outbound(base_url)        # 数据外发确认: 未同意不发请求
    # 输入描述会被发到该接口, 只许发往白名单主机, 避免误配/被改配置把用户文字外发
    host = (urllib.parse.urlsplit(base_url).hostname or "").lower()
    if not allow_any_host and host not in ALLOWED_HOSTS:
        raise SystemExit(
            "[FAIL] CAD_LLM_BASE_URL 主机 %r 不在白名单 %s 内。\n"
            "       你的描述文本会随请求发送到该地址，确认可信后再加 --allow-any-host 放行。"
            % (host, sorted(ALLOWED_HOSTS)))

    prompt, last = text, None
    for attempt in range(1, attempts + 1):
        raw = chat(prompt, base_url, api_key, model)
        try:
            spec = extract_json(raw)
            check_spec_sane(spec)                    # 数值范围校验, 防注入后异常参数
            notes = cad_ai.validate_spec(spec)       # 硬校验 + 语义提示
            ents = cad_ai.compile_spec(spec)         # 能编译成图元才算真的可用
            return spec, notes, ents
        except Exception as e:
            last = e
            print("[WARN] 第 %d 次输出未通过校验: %s -> 回喂错误重试" % (attempt, e),
                  file=sys.stderr)
            prompt = ("你上一次的输出无法通过校验: %s\n"
                      "原始输入:\n%s\n请重新只输出修正后的 JSON。" % (e, text))
    raise SystemExit("[FAIL] 模型输出 %d 次都未通过校验: %s" % (attempts, last))


def main(argv=None):
    ap = argparse.ArgumentParser(description="自然语言 -> CAD 规格 JSON")
    ap.add_argument("--text", help="自然语言描述")
    ap.add_argument("--file", help="从文件读取描述")
    ap.add_argument("--out", default="spec.json", help="输出规格文件路径")
    ap.add_argument("--show", action="store_true", help="把 JSON 打到 stdout")
    ap.add_argument("--enable-llm", action="store_true",
                    help="启用自然语言转规格(会把描述发送到外部 LLM 接口，默认关闭)")
    ap.add_argument("--allow-any-host", action="store_true",
                    help="允许把描述发往白名单以外的 LLM 接口(自担数据外发风险)")
    args = ap.parse_args(argv)

    text = args.text
    if not text and args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    if not text:
        text = sys.stdin.read()
    if not text.strip():
        raise SystemExit("[FAIL] 没有输入描述")
    if not args.enable_llm:
        raise SystemExit(
            "[FAIL] 自然语言转规格默认关闭(涉及把描述发往第三方 LLM)。\n"
            "       直接给 spec.json 走 cad_ai 本地编译即可；确需自然语言请加 --enable-llm")

    spec, notes, ents = nl_to_spec(text, allow_any_host=args.allow_any_host)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    print("[OK] 生成规格 %s: 图元 %d 个" % (args.out, len(ents)))
    for n in notes:
        print("  [NOTE] %s" % n)
    if args.show:
        print(json.dumps(spec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())