import json

# 读取build.json
with open('build.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 格式化并写入build_formatted.json
with open('build_formatted.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("格式化完成！已保存到 build_formatted.json")
