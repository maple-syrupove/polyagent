import base64
import zlib
import json

def encode_save(json_obj):
    # 1. 将 Python 对象转换回 JSON 字符串
    json_str = json.dumps(json_obj, separators=(',', ':'))
    # 2. 转换为字节流 (UTF-8)
    data_bytes = json_str.encode('utf-8')
    # 3. Zlib 压缩
    compressed = zlib.compress(data_bytes)
    # 4. Base64 编码
    encoded = base64.b64encode(compressed)
    return encoded.decode('utf-8')

# 从build.json读取JSON字符串
with open('gen/20260302_181237.json', 'r', encoding='utf-8') as f:
    raw_json_string = f.read()

# 让 Python 的 json 库去解析字符串，它能看懂 'true'
my_modified_bridge = json.loads(raw_json_string)

# 此时 my_modified_bridge 已经是合法的 Python 字典了（里面的 true 变成了 True）
result_string = encode_save(my_modified_bridge)

print("生成成功！同时输出到output.txt中。")
print(result_string)

# 将结果写入output.txt
with open('output.txt', 'w', encoding='utf-8') as f:
    f.write(result_string)