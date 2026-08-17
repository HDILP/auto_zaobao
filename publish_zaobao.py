import os
import time
import requests
import hashlib
import glob
import json
from datetime import date

# -----------------------------------------------
# 1. 从环境变量导入 COMMON_PAYLOAD
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
    print(f"🚨 致命错误：CONFIG 不是合法的 JSON！")
    print(f"JSON 错误：{e}")
    raise SystemExit(1)

except Exception as e:
    print(f"🚨 致命错误：加载 CONFIG 失败：{e}")
    raise SystemExit(1)


# -----------------------------------------------
# 2. 导入图片上传签名逻辑
#    (依赖外部文件 send_coin.py)
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
    上传单张图片。
    使用 get_image_sig (从 send_coin.py 导入)
    """

    url = "https://api.yaerxing.com/OSSUploadImage4.php"

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

    # 生成签名
    payload["api_sig"] = get_image_sig(payload)

    if not payload["api_sig"]:
        print("❌ 签名失败，终止上传。")
        return ""

    print(
        f"正在上传图片: "
        f"{os.path.basename(file_path)} "
        f"(Call ID: {current_time_ms})"
    )

    try:
        with open(file_path, "rb") as file:
            files = {
                "file": (
                    os.path.basename(file_path),
                    file,
                    "image/jpeg",
                )
            }

            response = requests.post(
                url,
                headers=HEADERS,
                data=payload,
                files=files,
            )

            if response.status_code != 200:
                print(
                    f" -> [HTTP ERROR] "
                    f"状态码: {response.status_code}"
                )
                return ""

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

            return ""

    except Exception as e:
        print(f" -> 上传异常: {e}")
        return ""


def publish_article(image_urls):
    """
    发布文章。
    使用 get_note_sig (内部定义)
    """

    if not image_urls:
        print("没有图片URL，跳过发布。")
        return

    url = "https://api.yaerxing.com/UploadNote2"

    urls_str = "["

    urls_str += ",".join(
        [f'"{u}"' for u in image_urls]
    )

    urls_str += "]"

    payload = COMMON_PAYLOAD.copy()

    current_time_ms = str(int(time.time() * 1000))

    payload.update({
        "title": f"每日早报 {date.today()}",
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

    # 生成签名
    payload["api_sig"] = get_note_sig(payload)

    print("正在发布文章...")

    try:
        response = requests.post(
            url,
            data=payload,
            headers=HEADERS,
        )

        print("发布响应:", response.text)

        if (
            response.status_code == 200
            and '"success":true' in response.text
        ):
            print("✅ 文章发布成功！")
        else:
            print("❌ 文章发布可能失败，请检查日志。")

    except Exception as e:
        print(f"发布异常: {e}")


def main():
    files = glob.glob("screenshots/*.png")

    if not files:
        print(
            "❌ 未找到截图文件，"
            "请检查 capture_zaobao.py 是否执行成功。"
        )
        return

    files.sort(
        key=lambda x: int(
            x.split("_")[-1].split(".")[0]
        )
    )

    print(
        f"找到 {len(files)} 张截图，"
        "准备上传..."
    )

    uploaded_urls = []

    for file_path in files:
        url = upload_image(file_path)

        if url:
            uploaded_urls.append(url)
            time.sleep(1)

    if uploaded_urls:
        publish_article(uploaded_urls)
    else:
        print("❌ 所有图片上传失败，终止发布。")


if __name__ == "__main__":
    main()
