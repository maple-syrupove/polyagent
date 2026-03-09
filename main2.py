import json
import time
import base64
import pyautogui
import os
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

# 引入你提供的自定义 LLM Handler
from llm_inf import LLMHandler_inf
# 引入 encode.py 的加密函数
from tool.encode import encode_save
# 引入路径配置
import paths
# 引入自动加载存档模块
from tool import auto_load_savefiles

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
MODEL_NAME = os.getenv("MODEL_NAME", "claude-opus-4-5-2025110")
SCREENSHOT_PATH = "current_level.png"

SYSTEM_PROMPT = """
# Role & Objective
You are an expert Structural Engineer and Level Designer for the physics puzzle game *Poly Bridge*. Your goal is to solve any given level by designing a bridge that is structurally sound and cost-effective.
Crucially, you must translate your design into a topological layout (Nodes and Edges) and **output your solution STRICTLY as a raw JSON object**. The backend system will handle the complex geometric coordinate calculations.

# Part 1: Game Physics & Engineering Knowledge Base

## A. Material Properties (Stats & Costs)
Below is the general encyclopedia of game materials. **WARNING: You DO NOT have access to all of these in every level!** You must check the image to see what is unlocked.
* **Road (Type 1)**: Drivable surface. Strength: 900PN. Max Length: 2m. Cost: $200/m.
* **Wood (Type 2)**: Cheapest support. Strength: 800PN. Max Length: 2m. Cost: $180/m.
* **Steel (Type 8)**: High strength. Strength: 2000PN. Max Length: 4m. Cost: $450/m.
* **Hydraulics (Type 4)**: Active piston for movement. Strength: 1800PN. Max Length: 4m. Cost: $750/m. Requires `rate` parameter.
* **Rope (Type 5)**: Tensile strength only. Strength: 1200PN. Unlimited Length. Cost: $220/m.
* **Cable (Type 5/Map specific)**: High tensile strength. Strength: 2200PN. Unlimited Length. Cost: $400/m.

*(Note: Try your best to keep connections within these max length limits...)*

## B. Construction Mechanics & Tips
* **Triangles**: The strongest shape. Always aim for equilateral triangles to distribute load evenly.
* **Diamond Shapes**: Harness the power of two triangles to form a single support for increased strength.
* **Arches**: A curved shape that distributes load evenly across a structure. Essential for long spans.

---

# Part 2: Generation Protocols (Strict Rules)

**Rule #1: ADDING NEW NODES & SEQUENTIAL IDs**
You are allowed to create new dynamic nodes (Type 0) in the air to build trusses or supports. However, you MUST follow this strict ID numbering rule:
1. Identify the highest existing Node `id` from the `initial_save_code`.
2. Any NEW nodes you create MUST continue sequentially from that highest ID. 
3. Set `"isKinematic": false` for all new suspended dynamic nodes you create.

**Rule #2: EDGE TYPES MUST NEVER BE 0**
When defining materials in the `edges` array, the `type` field designates the material (1=Road, 2=Wood, 8=Steel, etc.). You MUST NEVER set an edge's type to 0. Type 0 is an internal system identifier reserved exclusively for Nodes.

**Rule #3: COGNITIVE LENGTH CHECK (SOFT CONSTRAINT)**
Before connecting two nodes, mentally estimate the Euclidean distance. Try your best to ensure the distance respects the material limits (Wood/Road <= 2m, Steel/Hydraulics <= 4m). If a gap is too large, you must add intermediate nodes.

**Rule #4: VISUAL INVENTORY CHECK (CRITICAL)**
Look at the **bottom-left corner** of the provided Level Image. This is your material inventory toolbar. You are STRICTLY PROHIBITED from using any material type that is not visibly unlocked in that toolbar. 
- Example: If the toolbar only shows the icons for Road (Type 1) and Wood (Type 2), you MUST NEVER output `type: 8` (Steel) or `type: 5` (Rope) in your edges. Doing so will corrupt the save file.

---

# Part 3: CRITICAL OUTPUT FORMAT (JSON SCHEMA)
You do NOT have access to a tool call function. You must construct the output yourself.
Your output MUST be a **SINGLE, VALID JSON OBJECT** containing exactly three keys: `thought_process`, `nodes`, and `edges`.
**DO NOT output any other text.** Do not use markdown blocks (no ```json).

**Schema:**
{
  "thought_process": "[String] 1. List explicitly what materials are unlocked in the bottom-left image. 2. Identify highest Node ID. 3. List new Node IDs. 4. Check lengths. I MUST NOT use missing materials.",
  "nodes": [
    {
      "id": [Integer, Sequential ID],
      "x": [Number],
      "y": [Number],
      "isKinematic": [Boolean, TRUE for initial ground anchors, FALSE for new joints]
    }
  ],
  "edges": [
    {
      "id": [Integer, Sequential ID after nodes],
      "type": [Integer, Material type > 0],
      "anchorAID": [Integer],
      "anchorBID": [Integer],
      "rate": [Number, Only for type 4 Hydraulics, otherwise 0]
    }
  ]
}

---

# Part 4: Few-Shot Example (Pure JSON Output)
**Context:** Initial nodes are IDs 1 and 2. We add two suspended nodes 3 and 4, and connect them with Road (1) and Wood (2).

**Your ENTIRE Output Must Look EXACTLY Like This:**
{
  "thought_process": "1. I see Road and Wood unlocked in the bottom-left. 2. Highest initial Node ID is 2. 3. I will add new nodes ID 3 and 4. 4. Wood lengths look to be ~1.5m, which is valid.",
  "nodes": [
    {"id": 1, "x": 0, "y": 0, "isKinematic": true},
    {"id": 2, "x": 4, "y": 0, "isKinematic": true},
    {"id": 3, "x": 1, "y": 1, "isKinematic": false},
    {"id": 4, "x": 3, "y": 1, "isKinematic": false}
  ],
  "edges": [
    {"id": 5, "type": 1, "anchorAID": 1, "anchorBID": 2, "rate": 0},
    {"id": 6, "type": 2, "anchorAID": 1, "anchorBID": 3, "rate": 0},
    {"id": 7, "type": 2, "anchorAID": 3, "anchorBID": 4, "rate": 0},
    {"id": 8, "type": 2, "anchorAID": 4, "anchorBID": 2, "rate": 0}
  ]
}

---

# Part 5: Current Task Execution
**Input Data:**
Level Image: [See Uploaded Image]
{picture}
Initial Save Code: {initial_save_code}

**Requirement:**
1. Visually inspect the bottom-left toolbar.
2. Select the best design using ONLY the unlocked materials.
3. Output the exact topological JSON payload according to the Schema.
"""

# ================= 核心转换函数 =================
def convert_topology_to_objects(nodes, edges):
    """
    将拓扑结构 (nodes + edges) 转换为游戏存档格式的 Objects 数组
    系统自动计算 edges 的中点坐标，并遵循引擎序列化规则剔除默认的 false 字段
    """
    objects = []

    # 添加所有 nodes
    for node in nodes:
        obj = {
            "type": 0,
            "x": node["x"],
            "y": node["y"],
            "id": node["id"],
            "anchorAID": 0,
            "anchorBID": 0,
            "splitForDrawBridge": 0,
            "rate": 0
        }
        
        # 只有大模型明确给出 True 时，才把 isKinematic 写进游戏存档
        if node.get("isKinematic") is True:
            obj["isKinematic"] = True
            
        objects.append(obj)

    node_coords = {node["id"]: (node["x"], node["y"]) for node in nodes}

    # 添加所有 edges (自动计算中点坐标)
    for edge in edges:
        node_a_id = edge["anchorAID"]
        node_b_id = edge["anchorBID"]

        if node_a_id not in node_coords or node_b_id not in node_coords:
            print(f"⚠️ 警告：Edge {edge['id']} 引用的节点不存在 ({node_a_id} 或 {node_b_id})")
            continue

        x1, y1 = node_coords[node_a_id]
        x2, y2 = node_coords[node_b_id]

        mid_x = (x1 + x2) / 2.0
        mid_y = (y1 + y2) / 2.0

        obj = {
            "type": edge["type"],
            "x": mid_x,
            "y": mid_y,
            "id": edge["id"],
            "anchorAID": node_a_id,
            "anchorBID": node_b_id,
            "splitForDrawBridge": 0,
            "rate": edge.get("rate", 0)  # 液压杆动态参数，默认 0
        }
        objects.append(obj)

    return {"DisplayName": "Bridge_Generated", "Objects": objects}

# ================= 辅助函数 =================
def take_screenshot_and_get_base64(save_path):
    print("📸 正在截图...")
    screenshot = pyautogui.screenshot()
    screenshot.save(save_path)
    
    buffered = BytesIO()
    screenshot.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def extract_json_from_text(text):
    """暴力提取文本中的 JSON 块，并返回解析结果及可能的错误信息"""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str), None
        except json.JSONDecodeError as e:
            return None, f"JSONDecodeError: {str(e)}"
    return None, "No JSON object found in the response (Missing { and })."

# 这里请将下方的 SYSTEM_PROMPT 字符串放置于此或外部导入
# from prompt_file import SYSTEM_PROMPT

def generate_bridge_design(base64_image, initial_save_code):
    """请求大模型生成桥梁设计 (纯文本架构，单次请求无重试)"""
    print("🧠 正在调用 LLM 生成桥梁设计...")

    handler = LLMHandler_inf(api_key=API_KEY, model=MODEL_NAME)
    task_prompt = f"Please design the bridge. Here is the initial save code for reference:\n```json\n{initial_save_code}\n```"

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
        # 单次请求，无 tools 参数
        raw_response = handler.get_completion(messages=messages)
        
        # 强制转为 string
        response_text = str(getattr(raw_response, 'content', raw_response))
        
        # 使用正则提取并尝试解析 JSON
        topology_data, error_msg = extract_json_from_text(response_text)

        # 如果解析成功，且包含我们需要的核心字段
        if topology_data and "nodes" in topology_data and "edges" in topology_data:
            print("✅ JSON 提取解析成功！")
            design_data = convert_topology_to_objects(
                topology_data["nodes"],
                topology_data["edges"]
            )
            return design_data
        else:
            print(f"❌ 解析失败: {error_msg if error_msg else 'Missing nodes or edges'}")
            print(f"模型原始返回内容:\n{response_text}")
            return None

    except Exception as e:
        print(f"❌ API 调用通信失败: {e}")
        return None

def validate_design_json(design_data):
    """质量检控：严格审查大模型生成的 JSON 是否符合规则"""
    print("🔍 正在审查生成的 JSON 质量...")
    if not design_data or "Objects" not in design_data:
        return False
        
    objects = design_data["Objects"]
    nodes = {obj["id"]: (obj["x"], obj["y"]) for obj in objects if obj.get("type") == 0}
            
    for obj in objects:
        obj_type = obj.get("type")
        if obj_type > 0: # 连接材料
            obj_id, aid, bid = obj.get("id"), obj.get("anchorAID"), obj.get("anchorBID")
            if aid not in nodes or bid not in nodes:
                print(f"❌ 校验失败：物体 ID {obj_id} 引用了不存在的锚点 ({aid} 或 {bid})。")
                return False
                
            node_a_x, node_a_y = nodes[aid]
            node_b_x, node_b_y = nodes[bid]
            expected_x = (node_a_x + node_b_x) / 2.0
            expected_y = (node_a_y + node_b_y) / 2.0
            actual_x, actual_y = obj.get("x"), obj.get("y")
            
            if abs(expected_x - actual_x) > 0.001 or abs(expected_y - actual_y) > 0.001:
                print(f"❌ 校验失败：物体 ID {obj_id} 坐标计算错误！")
                return False

    print("✅ 校验通过：拓扑关系与坐标计算准确无误！")
    return True

def save_to_layout_file(design_data, timestamp):
    """保存为游戏可读取的存档"""
    save_dir = os.path.join("gen", timestamp)
    os.makedirs(save_dir, exist_ok=True)

    json_filepath = os.path.join(save_dir, f"{timestamp}.json")
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(design_data, f, indent=4)
    print(f"💾 JSON 存档已落盘至: {json_filepath}")

    with open(json_filepath, 'r', encoding='utf-8') as f:
        my_modified_bridge = json.loads(f.read())
    encoded_data = encode_save(my_modified_bridge)

    encoded_filepath = os.path.join(save_dir, "0")
    with open(encoded_filepath, 'w', encoding='utf-8') as f:
        f.write(encoded_data)

    target_dir = paths.GAME_SAVE_DIR
    target_filepath = os.path.join(target_dir, "0")
    try:
        os.makedirs(target_dir, exist_ok=True)
        with open(encoded_filepath, 'r', encoding='utf-8') as src:
            with open(target_filepath, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        print("🎮 准备加载存档到游戏界面...")
        auto_load_savefiles.load_polybridge_save()
    except Exception as e:
        print(f"❌ 复制到游戏存档目录失败: {e}")

if __name__ == "__main__":
    initial_code = """
    {"DisplayName":"1","Objects":[{"type":0,"x":0,"y":0,"id":1,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true},{"type":0,"x":8,"y":0,"id":2,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true},{"type":0,"x":0,"y":-2,"id":3,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true},{"type":0,"x":8,"y":-2,"id":4,"anchorAID":0,"anchorBID":0,"splitForDrawBridge":0,"rate":0,"isKinematic":true}]}
    """
    
    print("▶️ 请在 3 秒内切换到游戏画面...")
    time.sleep(3)
    
    base64_img = take_screenshot_and_get_base64(SCREENSHOT_PATH)
    bridge_json = generate_bridge_design(base64_img, initial_code)
    
    if bridge_json:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_to_layout_file(bridge_json, timestamp)
        if validate_design_json(bridge_json):
            print("✅ 此 JSON 文件质量达标，准备进入模拟流程...")
        else:
            print("⚠️ 注意：生成的 JSON 未通过严谨校验。已保存供事后排查分析。")
    else:
        print("❌ 流程终止：大模型未能生成有效的 JSON 格式数据。")