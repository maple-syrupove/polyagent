import json
import time
import base64
import pyautogui
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from PIL import Image

# 引入你提供的自定义 LLM Handler
from llm_inf import LLMHandler_inf
# 引入 encode.py 的加密函数
from encode import encode_save
# 引入路径配置
import paths

# ================= 加载环境变量 =================
def load_env(env_file: str = ".env"):
    """从 .env 文件加载环境变量"""
    env_path = Path(env_file)
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# ================= 配置区域 =================
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.2")
SCREENSHOT_PATH = "current_level.png"

# 请在这里粘贴你完整的 Prompt (包括所有的物理规则和 Few-shot examples)
SYSTEM_PROMPT = """
# Role & Objective
You are an expert Structural Engineer and Level Designer for the physics puzzle game *Poly Bridge*. Your goal is to solve any given level by designing a bridge that is structurally sound, cost-effective, and adheres strictly to the game's physics engine.
Crucially, you must translate your design into a **valid JSON save file** that can be loaded directly into the game.

# Part 1: Game Physics & Engineering Knowledge Base

## A. Material Properties (Stats & Costs)
Use these values to determine the best material for the specific gap and budget:
* **Road (Type 1)**: Drivable surface. Strength: 900PN (+300 w/ Wood, +600 w/ Steel). Max Length: 2m. Cost: $200/m.
* **Wood (Type 2)**: Cheapest support. Strength: 800PN. Max Length: 2m. Cost: $180/m.
* **Steel (Type 8)**: High strength. Strength: 2000PN. Max Length: 4m. Cost: $450/m.
* **Hydraulics (Type 4)**: Active piston for movement. Strength: 1800PN. Max Length: 4m. Cost: $750/m. Requires `rate` parameter.
* **Rope (Type 5)**: Tensile strength only (no compression). Strength: 1200PN. Unlimited Length. Cost: $220/m.
* **Cable (Type 5/Map specific)**: High tensile strength. Strength: 2200PN. Unlimited Length. Cost: $400/m.

## B. Construction Mechanics & Tips
* **Triangles**: The strongest shape. Always aim for equilateral triangles to distribute load evenly.
* **Diamond Shapes**: Harness the power of two triangles to form a single support for increased strength.
* **Arches**: A curved shape that distributes load evenly across a structure. Essential for long spans.
* **Static Joints (Red)**: Immovable anchor points. Connecting two static joints directly has no effect.
* **Land Braces**: Use the terrain! Terrain acts like a Static Joint. Rest structures against it or upon it for stability.
* **Pivot Points**: Created where two materials join. They act as hinges. Be careful not to create unintended pivot points that weaken the structure, but use them intentionally for drawbridges.

---

# Part 2: Save File Generation Protocols (Strict Rules)

## A. Core Data Structure
The save file is a JSON object containing:
* `"DisplayName"`: String. The name of the save slot (e.g., "Bridge_01").
* `"Objects"`: Array. A list of all game entities (nodes and materials).

## B. Object Parameter Definitions
Every item in the `"Objects"` array must adhere to these definitions:

| Parameter | Type | Definition & Constraints |
| :--- | :--- | :--- |
| `type` | Integer | Defines the material or object class (see "Material Type Mapping"). |
| `id` | Integer | Unique Identifier. Must be globally unique within the array. |
| `x` | Float | X-coordinate in the game world. |
| `y` | Float | Y-coordinate in the game world. |
| `anchorAID` | Integer | Connection Point A. The id of the first node this material connects to. (0 for Nodes). |
| `anchorBID` | Integer | Connection Point B. The id of the second node this material connects to. (0 for Nodes). |
| `isKinematic` | Boolean | Static Anchor Flag. Only valid for Nodes (Type 0). **true**: Fixed to world (ground/cliff). **false** (or omitted): Dynamic. |
| `splitForDrawBridge`| 0 or 1 | Drawbridge Split Joint. 1 allows the joint to detach during simulation. |
| `rate` | Float | Expansion/Contraction rate. Used for Hydraulics. Default is 0. |

## C. Material Type Mapping (ID Table)
* **Type 0**: Node (Joint/Vertex) - `anchorAID` and `anchorBID` are always 0.
* **Type 1**: Road
* **Type 2**: Wood
* **Type 4**: Hydraulics
* **Type 5**: Rope
* **Type 8**: Steel

## D. Strict Generation Logic (MUST FOLLOW)

**Rule #1: Topology Dependency (Nodes First)**
You cannot define a beam (Edge) before defining its Nodes (Vertices).
1.  **Step 1:** Define all Type 0 Nodes involved in the structure. Assign them unique `id`s.
2.  **Step 2:** Define materials (Type 1, 2, etc.) referencing those Node `id`s in their `anchorAID` and `anchorBID` fields.

**Rule #2: The Midpoint Geometry Formula**
The `x` and `y` coordinates for any connecting material (Road, Wood, Steel, etc.) are **NOT arbitrary**. They must be exactly the **geometric midpoint** of the two nodes they connect.
If a beam connects **Node A** $(x_1, y_1)$ and **Node B** $(x_2, y_2)$:
* **Beam X** = $(x_1 + x_2) / 2$
* **Beam Y** = $(y_1 + y_2) / 2$

**Rule #3: Static Anchors**
* Any node touching the ground or cliff (usually required for the bridge to stand) must have `"isKinematic": true`.
* Suspended nodes (bridge structure) must **not** have this flag (or set to `false`).

---

# Part 3: Few-Shot Example
**Example 1: The "M-Truss" (Standard Wooden Truss)***Description:* A 6-meter span bridge using a simple trapezoidal truss structure. It has static anchors at x=0 and x=6, with two dynamic road nodes in between. Wood beams form the upper support structure.

- **Nodes:** 4 Road nodes (0, 2, 4, 6) and 2 Upper support nodes at y=2.
- **Logic:** Demonstrates basic triangulation and multi-segment road connection.

```json
{"DisplayName":"M-Truss_6m","Objects":[{"type":0,"x":0,"y":0,"id":1,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true},{"type":0,"x":6,"y":0,"id":2,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true},{"type":0,"x":2,"y":0,"id":3,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0},{"type":0,"x":4,"y":0,"id":4,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0},{"type":0,"x":2,"y":2,"id":5,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0},{"type":0,"x":4,"y":2,"id":6,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0},{"type":1,"x":1,"y":0,"id":7,"anchorAID":1,"anchorBID":3,"splitForDrawBridge":0,"rate":0},{"type":1,"x":3,"y":0,"id":8,"anchorAID":3,"anchorBID":4,"splitForDrawBridge":0,"rate":0},{"type":1,"x":5,"y":0,"id":9,"anchorAID":4,"anchorBID":2,"splitForDrawBridge":0,"rate":0},{"type":2,"x":1,"y":1,"id":10,"anchorAID":1,"anchorBID":5,"splitForDrawBridge":0,"rate":0},{"type":2,"x":2,"y":1,"id":11,"anchorAID":3,"anchorBID":5,"splitForDrawBridge":0,"rate":0},{"type":2,"x":3,"y":2,"id":12,"anchorAID":5,"anchorBID":6,"splitForDrawBridge":0,"rate":0},{"type":2,"x":3,"y":1,"id":13,"anchorAID":3,"anchorBID":6,"splitForDrawBridge":0,"rate":0},{"type":2,"x":4,"y":1,"id":14,"anchorAID":4,"anchorBID":6,"splitForDrawBridge":0,"rate":0},{"type":2,"x":5,"y":1,"id":15,"anchorAID":6,"anchorBID":2,"splitForDrawBridge":0,"rate":0}]}

```
Part 4: Current Task Execution
Input Data:
Level Image: [See Uploaded Image] (Analyze geometry, gap size, and obstacles).
{picture}
Initial Save Code: [Provided Code] (Use this to extract the coordinate system and existing Anchor IDs).
{initial_save_code}

Requirement:
Analyze the input level. Select the appropriate materials (Wood vs Steel vs Rope) based on the "Game Physics" section (Part 1). Construct a solution that connects the anchor points.
Output ONLY the valid JSON code block representing the final save file, strictly following the "Generation Logic" in Part 2. Do not explain the math, just output the JSON.

"""
# ===========================================

def take_screenshot_and_get_base64(save_path):
    """截取屏幕，保存图片，并返回可供 API 使用的 Base64 字符串"""
    print("📸 正在截图...")
    screenshot = pyautogui.screenshot()
    screenshot.save(save_path)
    
    # 将图片转换为 Base64
    buffered = BytesIO()
    screenshot.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def clean_json_response(response_text):
    """清理大模型可能返回的 Markdown 标记 (例如 ```json ... ```)"""
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def generate_bridge_design(base64_image, initial_save_code):
    """通过你封装的 API 请求大模型生成桥梁设计"""
    print("🧠 正在调用 LLM 生成桥梁设计...")
    
    handler = LLMHandler_inf(api_key=API_KEY, model=MODEL_NAME)
    
    # 构造给大模型的额外提示
    task_prompt = f"Please design the bridge. Here is the initial save code for reference:\n```json\n{initial_save_code}\n```"

    # OpenAI Vision 的标准 message 结构
    messages = [
        {
            "role": "system", 
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": task_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        }
    ]

    try:
        # 强制要求返回 JSON 格式 (利用你的 response_format 参数)
        raw_response = handler.get_completion(
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        # 解析返回结果
        json_str = clean_json_response(raw_response)
        return json.loads(json_str)
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败，模型返回的内容可能格式有误:\n{raw_response}")
        return None
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        return None

def validate_design_json(design_data):
    """
    质量检控：严格审查大模型生成的 JSON 是否符合规则
    """
    print("🔍 正在审查生成的 JSON 质量...")
    if not design_data or "Objects" not in design_data:
        print("❌ 校验失败：缺少 'Objects' 数组。")
        return False
        
    objects = design_data["Objects"]
    nodes = {obj["id"]: (obj["x"], obj["y"]) for obj in objects if obj.get("type") == 0}
            
    for obj in objects:
        obj_type = obj.get("type")
        if obj_type > 0: # 连接材料
            obj_id, aid, bid = obj.get("id"), obj.get("anchorAID"), obj.get("anchorBID")
            
            # 校验 1：锚点是否存在
            if aid not in nodes or bid not in nodes:
                print(f"❌ 校验失败：物体 ID {obj_id} 引用了不存在的锚点 ({aid} 或 {bid})。")
                return False
                
            # 校验 2：检查中点坐标公式是否正确
            node_a_x, node_a_y = nodes[aid]
            node_b_x, node_b_y = nodes[bid]
            expected_x = (node_a_x + node_b_x) / 2.0
            expected_y = (node_a_y + node_b_y) / 2.0
            actual_x, actual_y = obj.get("x"), obj.get("y")
            
            if abs(expected_x - actual_x) > 0.001 or abs(expected_y - actual_y) > 0.001:
                print(f"❌ 校验失败：物体 ID {obj_id} 坐标计算错误！模型:({actual_x}, {actual_y}), 正确:({expected_x}, {expected_y})")
                return False

    print("✅ 校验通过：拓扑关系与坐标计算准确无误！")
    return True

def save_to_layout_file(design_data, timestamp):
    """保存为游戏可读取的存档，自动存入 gen 目录下的时间子目录"""
    # 创建以时间命名的子目录
    save_dir = os.path.join("gen", timestamp)
    os.makedirs(save_dir, exist_ok=True)

    # 保存 JSON 文件
    json_filename = f"{timestamp}.json"
    json_filepath = os.path.join(save_dir, json_filename)
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(design_data, f, indent=4)
    print(f"💾 JSON 存档已落盘至: {json_filepath}")

    # 采用 encode.py 的逻辑：读取 JSON 文件并用 json.loads 解析后再加密
    with open(json_filepath, 'r', encoding='utf-8') as f:
        raw_json_string = f.read()
    my_modified_bridge = json.loads(raw_json_string)
    encoded_data = encode_save(my_modified_bridge)

    # 保存为文件 "0"（无后缀）
    encoded_filepath = os.path.join(save_dir, "0")
    with open(encoded_filepath, 'w', encoding='utf-8') as f:
        f.write(encoded_data)
    print(f"🔐 加密文件已落盘至: {encoded_filepath}")

    # 复制到游戏存档目录，覆盖原有文件
    target_dir = paths.GAME_SAVE_DIR
    target_filepath = os.path.join(target_dir, "0")
    try:
        os.makedirs(target_dir, exist_ok=True)
        with open(encoded_filepath, 'r', encoding='utf-8') as src:
            content = src.read()
        with open(target_filepath, 'w', encoding='utf-8') as dst:
            dst.write(content)
        print(f"📂 已复制到游戏存档目录: {target_filepath}")
    except Exception as e:
        print(f"❌ 复制到游戏存档目录失败: {e}")

if __name__ == "__main__":
    # 测试用的初始存档数据
    initial_code = """
    {"DisplayName":"1","Objects":[{"type":0,"x":0,"y":0,"id":1,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true},{"type":0,"x":8,"y":0,"id":2,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true},{"type":0,"x":0,"y":-2,"id":3,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true},{"type":0,"x":8,"y":-2,"id":4,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true}]}
    """
    
    print("▶️ 请在 3 秒内切换到游戏画面...")
    time.sleep(3)
    
    # 1. 截图并转换为 Base64
    base64_img = take_screenshot_and_get_base64(SCREENSHOT_PATH)
    
    # 2. 调用 GPT-4o 生成设计
    bridge_json = generate_bridge_design(base64_img, initial_code)
    
    # 3. 无论对错强制保存，然后再校验
    if bridge_json:
        # 按照当前时间生成文件名 (例如: 20240520_153022)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 立刻保存 (存入 gen/时间戳 子目录)
        save_to_layout_file(bridge_json, timestamp)

        # 保存完了再检查内容质量
        if validate_design_json(bridge_json):
            print("✅ 此 JSON 文件质量达标，准备进入模拟流程...")
            # 成功后，这里可以无缝衔接你加载存档跑模拟的代码
        else:
            print("⚠️ 注意：生成的 JSON 未通过严谨校验。已保存供事后排查分析。")
    else:
        print("❌ 流程终止：大模型未能生成有效的 JSON 格式数据。")