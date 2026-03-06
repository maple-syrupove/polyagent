import base64
import zlib
import json

# 这里的字符串就是 Poly Bridge 存档或关卡里的核心加密数据
original_str = """
eAG9z88KwjAMBvB3ybnCNj1Ib44iiKAPIB5iVzTi/pBGtIy9u6NV0Lt6Ccl3+H6kB0O+u2DYYO1AQw4Ktoezs+JB73qQ0I1xpuAeZ4iTKtC5AmzsqeXFysQwXeXzGjtJli0bxlvJVB1TC6OkhfyaGlejkAUtfHWD+sTm71jxYyyL2KRI2vQvr7202be1/fAAmCuQ+w==
"""

def decode_polybridge_save():
    # 1. 清洗输入（防止多余的换行符和空格导致 Base64 解码失败）
    clean_original = original_str.replace('\n', '').replace(' ', '').replace('\r', '')
    
    print("🔄 正在解码 Poly Bridge 数据...")
    
    try:
        # 2. Base64 解码
        compressed_data = base64.b64decode(clean_original)
        
        # 3. Zlib 解压缩
        raw_bytes = zlib.decompress(compressed_data)
        
        # 4. 解析为 JSON 对象
        json_obj = json.loads(raw_bytes)
        
        print("✅ 解码成功！\n")
        print("=== 存档 JSON 内容 ===")
        
        # 5. 格式化输出 JSON，方便人类和大模型阅读
        formatted_json = json.dumps(json_obj, indent=4, ensure_ascii=False)
        print(formatted_json)
        
        return json_obj
        
    except Exception as e:
        print(f"❌ 解码阶段出错: {e}")
        return None

if __name__ == "__main__":
    # 运行并提取 JSON
    level_json = decode_polybridge_save()