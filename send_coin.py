import hashlib
import time
import requests
import re
from get_qiandao_list import get_issues


def get_api_sig(payload):
    """
    生成API签名。

    该函数通过给定的负载（payload）生成一个API签名。它首先对负载中的键进行排序（跳过'api_sig'键），
    然后拼接键和值以生成一个字符串。之后，它添加一个密钥，并基于这个字符串生成一个MD5哈希值作为签名。

    参数:
    payload (dict): 包含API请求参数的字典。

    返回:
    str: 生成的API签名的MD5哈希值。
    """
    # 定义要跳过的键
    skip_keys = ["api_sig"]

    # 按键排序并拼接键和值，跳过指定的键
    result = ""
    for key, value in sorted(payload.items()):
        if key in skip_keys:
            continue
        result += f"{key}{value}"

    # 添加密钥到结果字符串
    result += "9bldwb2d5d02e81h"

    print(result)

    # 获取call_id的后四位
    call_id = payload["call_id"][-4:]

    # 构造需要进行MD5哈希的文本字符串
    text = f"f0{call_id}com.yaerxing.fkst1.16.21F.K*$t"
    print(f"加密前：{text}")
    # 计算给定字符串的MD5哈希值。
    md5 = hashlib.md5()
    md5.update(text.encode("utf-8"))
    md5 = md5.hexdigest()

    print(f"加密后：{md5}")
    # 获取文本字符串的MD5哈希值，并截取特定部分
    text_hash = md5[5:21]
    print(text_hash)
    # 将文本哈希值添加到结果字符串
    result += text_hash

    # 生成最终的API签名的MD5哈希值
    api_sig = hashlib.md5()
    api_sig.update(result.encode("utf-8"))
    api_sig = api_sig.hexdigest()
    # 将哈希值转换为大写
    api_sig = api_sig.upper()
    print(f"加密后2：{api_sig}")
    # 返回API签名
    return api_sig


def get_qiandao_data(unionid, openid, mid):
    """
    获取签到数据函数

    本函数通过发送POST请求到指定的URL，获取用户的签到数据。
    请求需要携带一系列的参数以确保请求的合法性。
    返回值是用户签到状态和签到天数。
    """
    # 定义请求的URL
    url = "https://api.yaerxing.com/GetSTMyData5"

    # 构建请求参数字典
    payload = {
    'unionid': unionid,
    'openid': openid,
    'all_black_member': "1",
    'channel': "none",
    'mid': mid,
    'app_c': "166",
    'call_id': str(int(time.time() * 1000)),
    'os_v': "29",
    'um_token': "AvMLUX2j0GYdgAecv65QEZWtHdHKrOCJ9vJYVX1UGEQ2",
    'rom': "OPPO",
    'url_name': "",
    'app_v': "1.16.21",
    'api_key': "17bf6ed3b808eb7dcfa5wa0f1f0cf1de",
    'identity': "171231ok1717cf1.5w12fa178eot19bd3de5660218875aw1h",
    'appid': "wx2bd42ba7f4c547f5",
    'device_token': "",
    'platform_id': "2",
    'oam': "0",
    'model': "PJJ110",
    'brand': "OPPO"
    }

    # 构建请求头，指定为Android设备，接受JSON格式的数据
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; PJJ110 Build/SKQ1.221119.001)",
        "Connection": "Keep-Alive",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # 生成api_sig签名，确保请求的合法性
    payload["api_sig"] = get_api_sig(payload)
    print(f"api_sig:{payload['api_sig']}")

    # 发送POST请求，获取响应数据
    response = requests.post(url, data=payload, headers=headers)

    # 将响应数据解析为JSON格式
    response = response.json()

    print(response)

    # 返回签到状态和签到天数
    return int(response["get_coin_status"]), int(response["get_coin_day"])


def send_coin(unionid, openid, mid):
    status, day = get_qiandao_data(unionid, openid, mid)
    coin = ["1", "1", "1", "2", "1", "1", "3"]

    url = "https://api.yaerxing.com/AddSTCoin"

    payload = {
        'unionid': unionid,
        'openid': openid,
        'channel': "none",
        'mid': mid,
        'app_c': "166",
        'call_id': str(int(time.time() * 1000)),
        'os_v': "29",
        'um_token': "AvMLUX2j0GYdgAecv65QEZWtHdHKrOCJ9vJYVX1UGEQ2",
        'rom': "OPPO",
        'url_name': "",
        'app_v': "1.16.21",
        'api_key': "17bf6ed3b808eb7dcfa5wa0f1f0cf1de",
        'identity': "171231ok1717cf1.5w12fa178eot19bd3de5660218830aw1h",
        'appid': "wx2bd42ba7f4c547f5",
        'device_token': "",
        'platform_id': "2",
        'oam': "0",
        'model': "PJJ110",
        'brand': "OPPO",
        'day': day + 1,
        'coin': coin[day] if day < 7 else "1"
    }

    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; PJJ110 Build/SKQ1.221119.001)",
        "Connection": "Keep-Alive",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    api_sig = get_api_sig(payload)
    payload["api_sig"] = api_sig
    print(payload)

    if status:
        return False
    else:
        response = requests.post(url, data=payload, headers=headers)
        print(response.text)
        return True


if __name__ == "__main__":
    issues = get_issues()
    for issue in issues:
        print("*****************************************")
        print("Title:\n", issue["title"])
        print("Description:\n", issue["description"])

        unionid = re.search(r"unionid=([a-zA-Z0-9]+)", issue["description"])
        openid = re.search(r"openid=(.*)", issue["description"])
        mid = re.search(r"mid=(\d+)", issue["description"])
        if unionid and openid and mid:
            unionid = unionid.group(1)
            openid = openid.group(1)
            mid = mid.group(1)
            print("提取的 unionid:", unionid)
            print("提取的 openid:", openid)
            print("提取的 mid:", mid)
            if send_coin(unionid, openid, mid):
                print("签到成功")
            else:
                print("已经签到")
        else:
            print("未找到")