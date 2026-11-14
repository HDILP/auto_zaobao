import os
import sys
import time
import glob
import json
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

# -----------------------------------------------
# 0. 运行参数
# -----------------------------------------------
# 状态文件：记录最近一次成功发布的日期与文章 id，用于「同一天不重复发」
STATE_FILE = "publish_state.json"
TZ = ZoneInfo("Asia/Shanghai")
# 一律按北京时间算日期，不受 runner 时区影响
TODAY = datetime.now(TZ).date()


def set_output(name, value):
    """写 GitHub Actions 的 step output（本地运行时会静默跳过）。"""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
    print(f"[OUTPUT] {name}={value}")


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(payload):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[STATE] 已写入 {STATE_FILE}: {payload}")


# -----------------------------------------------
# 1. 从环境变量导入 CONFIG
# -----------------------------------------------
try:
    config_raw = os.environ["CONFIG"]
    COMMON_PAYLOAD = json.loads(config_raw)

    if not isinstance(COMMON_PAYLOAD, dict):
        raise ValueError("CONFIG 必须是 JSON 对象/字典")

    print(f"[INIT] 成功加载 CONFIG，共 {len(COMMON_PAYLOAD)} 个配置项。")

except KeyError:
    print("🚨 致命错误：找不到环境变量 CONFIG！")
    print("请检查 GitHub Actions 是否设置了 secrets.CONFIG。")
    raise SystemExit(1)

except json.JSONDecodeError as e:
    print("🚨 致命错误：CONFIG 不是合法的 JSON！")
    print(f"JSON 错误：{e}")
    raise SystemExit(1)

except Exception as e:
    print(f"🚨 致命错误：加载 CONFIG 失败：{e}")
    raise SystemExit(1)


# -----------------------------------------------
# 2. 导入图片上传签名逻辑（依赖 send_coin.py）
# -----------------------------------------------
try:
    from send_coin import get_api_sig as get_image_sig
    print("[INIT] 成功导入 send_coin.py 中的图片签名函数。")

except ImportError:
    def get_image_sig(payload):
        print(
            "🚨 致命错误：找不到 send_coin.py 文件或 "
            "get_api_sig 函数！请检查仓库中文件是否提交。"
        )
        return ""


# -----------------------------------------------
# 3. 文章发布签名逻辑
# -----------------------------------------------
def get_note_sig(payload):
    """
    生成文章发布 API (UploadNote2) 签名。
    """

    skip_keys = ["api_key", "call_id", "openid"]

    result = ""

    for key, value in sorted(payload.items()):
        if key not in skip_keys:
            continue

        result += f"{key}{value}"

    result += "9bldwb2d5d02e81h"

    call_id = payload.get("call_id", "")

    if not call_id:
        return ""

    call_id_last_four = call_id[-4:]

    text = f"f0{call_id_last_four}com.yaerxing.fkst1.16.21F.K*$t"

    md5_obj = hashlib.md5()
    md5_obj.update(text.encode("utf-8"))

    text_hash = md5_obj.hexdigest()[5:21]

    result += text_hash

    api_sig = hashlib.md5()
    api_sig.update(result.encode("utf-8"))

    return api_sig.hexdigest().upper()


# ==================== 请求头 ====================

HEADERS = {
    "Connection": "Keep-Alive",
    "Charset": "UTF-8",
    "User-Agent": (
        "Dalvik/2.1.0 (Linux; U; Android 10; "
        "PJJ110 Build/SKQ1.221119.001)"
    ),
    "Host": "api.yaerxing.com",
    "Accept-Encoding": "gzip",
}


# ==================== 核心逻辑 ====================

def upload_image(file_path):
    """
    上传单张图片（带 2 次重试，覆盖上传请求超时）。
    使用 get_image_sig (从 send_coin.py 导入)
    """

    url = "https://api.yaerxing.com/OSSUploadImage4.php"

    for attempt in range(1, 4):
        payload = COMMON_PAYLOAD.copy()

        current_time_ms = str(int(time.time() * 1000))

        payload.update({
            "dir_name": "stupnote",
            "call_id": current_time_ms,
            "id": "0",
            "url_name": "",
            "group_id": "",
            "device_token": "",
        })

        payload["api_sig"] = get_image_sig(payload)

        if not payload["api_sig"]:
            print("❌ 签名失败，终止上传。")
            return ""

        print(
            f"正在上传图片: "
            f"{os.path.basename(file_path)} "
            f"(Call ID: {current_time_ms}, 第 {attempt} 次)"
        )

        try:
            with open(file_path, "rb") as file:
                files = {
                    "file": (
                        os.path.basename(file_path),
                        file,
                        "image/png",
                    )
                }

                response = requests.post(
                    url,
                    headers=HEADERS,
                    data=payload,
                    files=files,
                    timeout=60,
                )

            if response.status_code != 200:
                print(f" -> [HTTP ERROR] 状态码: {response.status_code}")
                time.sleep(3)
                continue

            res_json = response.json()

            if res_json.get("res") == 2:
                print(
                    f" -> [API ERROR] 错误码2: "
                    f"{res_json.get('error')} "
                    f"(极可能是 send_coin.py 中的签名逻辑有误)"
                )
                return ""

            img_url = res_json.get("url", "")

            if img_url:
                print(f" -> 上传成功: {img_url}")
                return img_url

            print(f" -> 响应里没有 url: {res_json}")
            time.sleep(3)

        except Exception as e:
            print(f" -> 上传异常: {e}")
            time.sleep(3)

    return ""


def publish_article(image_urls):
    """
    发布文章，返回 (是否成功, 文章 id)。
    平台成功响应形如：{"res":0,"id":"5222138"}
    """

    if not image_urls:
        print("没有图片URL，跳过发布。")
        return False, ""

    url = "https://api.yaerxing.com/UploadNote2"

    urls_str = "[" + ",".join(f'"{u}"' for u in image_urls) + "]"

    payload = COMMON_PAYLOAD.copy()

    current_time_ms = str(int(time.time() * 1000))

    payload.update({
        "title": f"每日早报 {TODAY}",
        "content": (
            "今天是新的一天，来看看发生了什么大事吧！"
            "#早报 #新闻"
        ),
        "urls": urls_str,
        "urls2": "",
        "attachment_urls": "",
        "call_id": current_time_ms,
        "id": "0",
        "group_id": "",
        "device_token": "",
    })

    payload["api_sig"] = get_note_sig(payload)

    print("正在发布文章...")
    print(f"标题: {payload['title']}，图片 {len(image_urls)} 张")

    try:
        response = requests.post(
            url,
            data=payload,
            headers=HEADERS,
            timeout=60,
        )

        print("发布响应:", response.text)

        if response.status_code != 200:
            print(f"❌ 发布失败：HTTP {response.status_code}")
            return False, ""

        try:
            res_json = response.json()
        except Exception:
            print(f"❌ 发布失败：响应不是 JSON -> {response.text[:200]}")
            return False, ""

        article_id = str(res_json.get("id", ""))

        # 平台以 res == 0 表示成功；旧代码找 '"success":true' 是错的，
        # 会把成功误判成失败（2026-11-07 那次就是这样报了假警）。
        if res_json.get("res") == 0 and article_id:
            print(f"✅ 文章发布成功！文章 id = {article_id}")
            return True, article_id

        print(f"❌ 文章发布失败，平台返回: {res_json}")
        return False, ""

    except Exception as e:
        print(f"❌ 发布异常: {e}")
        return False, ""


def safe_sort_key(path):
    """zaobao_page_3.png -> 3；fallback_page.png 之流排到最后。"""
    name = os.path.basename(path)
    try:
        return int(name.split("_")[-1].split(".")[0])
    except ValueError:
        return 10 ** 6


def main():
    allow_republish = os.environ.get("ALLOW_REPUBLISH", "true").lower() != "false"

    state = load_state()
    if not allow_republish and state.get("date") == str(TODAY):
        print(
            f"⏭️ 今天（{TODAY}）已经成功发布过"
            f"（文章 id {state.get('article_id')}），本次是补发流程，跳过。"
        )
        set_output("published", "false")
        return 0

    files = glob.glob("screenshots/*.png")

    if not files:
        print("❌ 未找到截图文件，请检查 capture_zaobao.py 是否执行成功。")
        set_output("published", "false")
        return 1

    files.sort(key=safe_sort_key)

    print(f"找到 {len(files)} 张截图，准备上传...")

    uploaded_urls = []

    for file_path in files:
        url = upload_image(file_path)

        if url:
            uploaded_urls.append(url)
            time.sleep(1)

    if not uploaded_urls:
        print("❌ 所有图片上传失败，终止发布。")
        set_output("published", "false")
        return 1

    if len(uploaded_urls) < len(files):
        print(
            f"⚠️ 只有 {len(uploaded_urls)}/{len(files)} 张上传成功，"
            "继续用成功的那些发布。"
        )

    ok, article_id = publish_article(uploaded_urls)

    if not ok:
        set_output("published", "false")
        return 1

    save_state({
        "date": str(TODAY),
        "article_id": article_id,
        "images": len(uploaded_urls),
        "published_at": __import__("datetime").datetime.now(TZ).isoformat(
            timespec="seconds"
        ),
    })
    set_output("published", "true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
