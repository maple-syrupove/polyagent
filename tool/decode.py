import base64
import zlib

# 从input.txt读取字符串
with open('../input.txt', 'r', encoding='utf-8') as f:
    data_str = f.read().strip()

# 1. Base64 解码
compressed_data = base64.b64decode(data_str)
# 2. Zlib 解压
original_json = zlib.decompress(compressed_data)

# 解码并写入build.json
result = original_json.decode('utf-8')

print("生成成功！同时输出到build.json中。")
print(result)

with open('../build.json', 'w', encoding='utf-8') as f:
    f.write(result)