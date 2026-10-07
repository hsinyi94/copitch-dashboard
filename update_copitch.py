# -*- coding: utf-8 -*-
"""Co-Pitch Review Dashboard 每週更新(加密版)。

流程:
  1. 執行來源資料夾的 build_review_dashboard.py 產出最新明文 HTML
  2. 比對明文 HTML 內容是否與上次相同(用存在 repo 外的雜湊檔,因為加密每次
     會有隨機 salt,密文一定不同,不能拿密文來比)
  3. 若有變化 -> 用 encrypt_dashboard.py 把明文加密成 index.html(AES-256-GCM)
  4. git add / commit / push 到 GitHub Pages

安全:
  * 進 repo 的只有「加密後」的 index.html。明文 HTML 與原始 Excel 永不進 repo。
  * 密碼讀自本機密碼檔(repo 外、不同步、不進 git),加密時複製一份暫存檔給
    encrypt_dashboard.py(它讀完即銷毀暫存),原始密碼檔保留供下週重用。

結束碼:
  0  = 有更新並 push 成功
  10 = 來源 HTML 沒有變化(無需 push)  -> 給 KiroCrew 當「無異動」判斷
  6  = 缺少密碼檔
  其它非 0 = 失敗
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SRC_DIR = Path(r"C:\Users\hsinyih\OneDrive - amazon.com\Co-Pitch")
BUILD = SRC_DIR / "build_review_dashboard.py"
SRC_HTML = SRC_DIR / "Co-Pitch_Review_Dashboard.html"
ENCRYPT = SRC_DIR / "encrypt_dashboard.py"

REPO = Path(__file__).resolve().parent
DST_HTML = REPO / "index.html"          # 加密後的鎖定頁(會進 git)
LOG_DIR = REPO / "logs"
# 明文雜湊存這裡,用來判斷「內容有沒有變」。放在 logs/ 底下,已被 .gitignore 擋掉,
# 不會進 repo。
HASH_FILE = LOG_DIR / ".last_plain_hash"
# 密碼檔:本機、不同步、不進 git。encrypt_dashboard.py 的 --password-file 讀完
# 即銷毀,所以每次「複製一份」暫存檔給它用,保留原檔供下週重用。
PW_FILE = Path(os.environ["USERPROFILE"]) / ".kiro" / "crew" / "secrets" / "copitch_pw.txt"
PY = sys.executable


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    LOG_DIR.mkdir(exist_ok=True)
    with (LOG_DIR / f"update_{datetime.now():%Y%m%d}.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def run(cmd, cwd, env=None):
    # 記錄時不印出完整環境(避免密碼外洩);只印指令本身。
    log("> " + " ".join(cmd))
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                         encoding="utf-8", env=env)
    if res.stdout.strip():
        log(res.stdout.strip())
    if res.returncode != 0:
        log("STDERR: " + res.stderr.strip())
    return res.returncode


def main():
    log("===== Co-Pitch 更新開始(加密版) =====")

    # 0. 先確認密碼檔存在
    if not PW_FILE.exists():
        log(f"缺少密碼檔:{PW_FILE} 不存在,無法加密。")
        return 6

    # 1. build
    log("[1/4] 執行 build_review_dashboard.py ...")
    if run([PY, "-X", "utf8", str(BUILD)], cwd=SRC_DIR) != 0:
        log("build 失敗")
        return 2
    if not SRC_HTML.exists():
        log(f"找不到產出的 HTML: {SRC_HTML}")
        return 3

    # 2. 比對明文是否有變化(用 repo 外的雜湊檔)
    LOG_DIR.mkdir(exist_ok=True)
    before = HASH_FILE.read_text(encoding="utf-8").strip() if HASH_FILE.exists() else ""
    after = sha(SRC_HTML)
    if before == after:
        log("[2/4] 明文內容與上次相同,無需更新")
        log("===== 結束(無異動) =====")
        return 10

    # 3. 加密成 index.html。encrypt_dashboard.py 的 --password-file 讀完會把檔案
    #    銷毀;我們不想毀掉長期保存的密碼檔,所以複製一份到暫存檔給它用。
    log("[3/4] 加密 HTML -> index.html (AES-256-GCM)")
    tmp_pw = None
    try:
        fd, tmp_pw = tempfile.mkstemp(prefix="copitch_pw_", suffix=".txt")
        os.close(fd)
        shutil.copyfile(PW_FILE, tmp_pw)
        rc = run([PY, "-X", "utf8", str(ENCRYPT),
                  "--src", str(SRC_HTML),
                  "--out", str(DST_HTML),
                  "--password-file", tmp_pw],
                 cwd=SRC_DIR)
    finally:
        # encrypt 成功時已自行刪除;萬一失敗殘留,這裡確保清掉。
        if tmp_pw and os.path.exists(tmp_pw):
            try:
                os.remove(tmp_pw)
            except OSError:
                pass
    if rc != 0:
        log("加密失敗")
        return 7

    # 4. git commit + push(只會含加密後的 index.html)
    log("[4/4] Git commit & push ...")
    stamp = f"{datetime.now():%Y-%m-%d}"
    run(["git", "add", "-A"], cwd=REPO)
    if run(["git", "commit", "-m", f"Weekly update {stamp}"], cwd=REPO) != 0:
        log("commit 失敗(可能沒有變更)")
        return 4
    if run(["git", "push"], cwd=REPO) != 0:
        log("push 失敗")
        return 5

    # push 成功後才更新雜湊記錄,確保失敗時下次會重試
    HASH_FILE.write_text(after, encoding="utf-8")

    log("===== 更新完成並 push 成功 =====")
    log("連結: https://hsinyi94.github.io/copitch-dashboard/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
