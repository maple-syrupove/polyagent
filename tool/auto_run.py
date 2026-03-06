import pyautogui
import time
import os
import shutil
import glob
from datetime import datetime
from PIL import Image

def run_and_save_replay():
    """
    运行测试，保存回放并返回搭建界面
    """
    print("▶️ 开始运行桥梁测试...")
    
    # 1. 空格键开始运行
    pyautogui.press('space')
    print("-> ⌨️ 已按下 [Space] 键，等待 8 秒钟的物理模拟...")
    time.sleep(8.0)

    print("❌ 模拟结束，开始保存回放...")

    # 2. 点击“分享回放”按钮
    pyautogui.click(x=1271, y=833)
    print("-> 🎥 已点击分享回放 (1271, 833)")
    time.sleep(1.0)

    # 3. 点击“对钩”确认保存
    pyautogui.click(x=1593, y=1078)
    print("-> ✔️ 已点击确认保存 (1593, 1078)，等待 5 秒钟处理视频并写入硬盘...")
    # 稍微延长了这里的等待时间，确保 GIF 已经完全写入上一级目录中
    time.sleep(5.0) 

    # 4. 再次按下空格键返回搭建界面
    pyautogui.press('space')
    print("-> ⌨️ 已按下 [Space] 键返回搭建界面")
    time.sleep(1.0)
    
    print("✅ 回放保存完毕，已成功回到初始状态！")


def process_and_extract_gif():
    """
    找到上一级目录中的最新 GIF，将其移动到同级的 pic 目录中，并抽取 3 帧图像
    """
    print("\n📂 开始处理并抽帧 GIF 回放文件...")
    
    # 获取当前脚本运行的绝对路径，并推算出上一级目录
    current_dir = os.path.abspath(os.getcwd())
    parent_dir = os.path.dirname(current_dir)
    
    # 定义上一级目录中的 PolyBridgeGIFs 和 pic 文件夹路径
    gif_dir = os.path.join(parent_dir, "PolyBridgeGIFs")
    pic_base_dir = os.path.join(parent_dir, "pic")
    
    # 1. 检查上一级的 PolyBridgeGIFs 目录是否存在
    if not os.path.exists(gif_dir):
        print(f"⚠️ 找不到目录: {gif_dir}\n请确认当前运行目录的上一级是否存在该文件夹！")
        return
        
    # 查找 GIF 文件
    gif_files = glob.glob(os.path.join(gif_dir, "*.gif"))
    
    if not gif_files:
        print(f"⚠️ 在 {gif_dir} 中没有找到任何 GIF 文件！可能游戏保存太慢，或者路径不对。")
        return
        
    # 取出该目录下唯一存在的文件
    source_gif_path = gif_files[0] 
    gif_filename = os.path.basename(source_gif_path)
    
    # 2. 在上一级的 pic 目录下，创建一个以当前时间命名的子目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = os.path.join(pic_base_dir, timestamp)
    os.makedirs(target_dir, exist_ok=True)
    
    # 3. 将 GIF 移动到新建立的子目录中
    target_gif_path = os.path.join(target_dir, gif_filename)
    shutil.move(source_gif_path, target_gif_path)
    print(f"-> 📦 已将原 GIF 移动至: {target_dir}")
    
    # 4. 开始对移动后的 GIF 进行抽帧操作
    try:
        with Image.open(target_gif_path) as img:
            total_frames = img.n_frames
            # 计算我们需要抽取的 3 帧索引：第一帧(0)、最中间一帧、最后一帧
            indices = [0, total_frames // 2, total_frames - 1]
            
            for i, frame_idx in enumerate(indices):
                img.seek(frame_idx)
                # 将图像转为 RGB 模式（因为保存为 JPG 不支持透明通道）
                frame = img.copy().convert("RGB")
                frame_path = os.path.join(target_dir, f"frame_{i+1}.jpg")
                frame.save(frame_path, "JPEG")
                print(f"-> 🖼️ 提取帧 {i+1}/3 (原视频第 {frame_idx} 帧) 保存为: {frame_path}")
                
        print("✅ 抽帧并归档流程彻底完成！")
        
    except Exception as e:
        print(f"❌ 抽帧处理时发生错误: {e}")


if __name__ == "__main__":
    print("⏳ 脚本已启动！请在 3 秒内切换回 Poly Bridge 游戏界面...")
    time.sleep(3)
    
    # 阶段 1: 执行运行和保存流程
    run_and_save_replay()
    
    # 阶段 2: 将保存好的 GIF 进行移动归档并抽取 3 张图片
    process_and_extract_gif()
    
    print("🎉 自动化跑测与录像处理全流程执行完毕！")