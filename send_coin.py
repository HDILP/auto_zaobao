import hashlib
import time
import requests
import re

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