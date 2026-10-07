# -*- coding: utf-8 -*-
"""Co-Pitch Review Dashboard 每週更新。

流程(對齊 ACC 2.0 的做法):
  1. 執行來源資料夾的 build_review_dashboard.py 產出最新 HTML
  2. 把產出的 Co-Pitch_Review_Dashboard.html 複製到本 repo 的 index.html
  3. git add / commit / push 到 GitHub Pages

安全: 只搬 HTML。原始 Excel (賣家名單) 永遠不進這個 repo。

結束碼:
  0 = 有更新並 push 成功
  10 = 來源 HTML 沒有變化(無需 push)  -> 給 KiroCrew 當「無異動」判斷
  其它非 0 = 失敗
"""
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SRC_DIR = Path(r"C:\Users\hsinyih\OneDrive - amazon.com\Co-Pitch")
BUILD = SRC_DIR / "build_review_dashboard.py"
SRC_HTML = SRC_DIR / "Co-Pitch_Review_Dashboard.html"

REPO = Path(__file__).resolve().parent
DST_HTML = REPO / "index.html"
LOG_DIR = REPO / "logs"
PY = sys.executable


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    LOG_DIR.mkdir(exist_ok=True)
    with (LOG_DIR / f"update_{datetime.now():%Y%m%d}.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def run(cmd, cwd):
    log("> " + " ".join(cmd))
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if res.stdout.strip():
        log(res.stdout.strip())
    if res.returncode != 0:
        log("STDERR: " + res.stderr.strip())
    return res.returncode


def main():
    log("===== Co-Pitch 更新開始 =====")

    # 1. build
    log("[1/4] 執行 build_review_dashboard.py ...")
    if run([PY, "-X", "utf8", str(BUILD)], cwd=SRC_DIR) != 0:
        log("build 失敗")
        return 2
    if not SRC_HTML.exists():
        log(f"找不到產出的 HTML: {SRC_HTML}")
        return 3

    # 2. 比對是否有變化
    before = sha(DST_HTML)
    after = sha(SRC_HTML)
    if before == after:
        log("[2/4] HTML 內容與上次相同,無需更新")
        log("===== 結束(無異動) =====")
        return 10

    # 3. 複製成 index.html
    log("[3/4] 複製 HTML -> index.html")
    shutil.copy2(SRC_HTML, DST_HTML)

    # 4. git commit + push
    log("[4/4] Git commit & push ...")
    stamp = f"{datetime.now():%Y-%m-%d}"
    run(["git", "add", "-A"], cwd=REPO)
    if run(["git", "commit", "-m", f"Weekly update {stamp}"], cwd=REPO) != 0:
        log("commit 失敗(可能沒有變更)")
        return 4
    if run(["git", "push"], cwd=REPO) != 0:
        log("push 失敗")
        return 5

    log("===== 更新完成並 push 成功 =====")
    log("連結: https://hsinyi94.github.io/copitch-dashboard/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
