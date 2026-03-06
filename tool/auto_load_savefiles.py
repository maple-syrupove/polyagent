import pyautogui
import time

def load_polybridge_save():
    """
    自动载入 Poly Bridge 的指定存档
    """
    print("开始执行自动载入...")
    
    # 步骤 1: 点击左上角的“设置”齿轮
    pyautogui.click(x=45, y=41)
    print("-> 已点击设置 (x=45, y=41)")
    time.sleep(0.5)  # 等待下拉菜单展开

    # 步骤 2: 点击下拉菜单中的“载入”按钮
    pyautogui.click(x=39, y=112)
    print("-> 已点击载入 (x=39, y=112)")
    time.sleep(1.0)  # 等待存档面板完全弹出

    # 步骤 3: 点击“自动存档槽”下方的特定存档
    pyautogui.click(x=1192, y=634)
    print("-> 已选中目标存档！ (x=1192, y=634)")
    time.sleep(0.5)
    
    print("🎉 载入流程执行完毕！")

if __name__ == "__main__":
    print("⏳ 请在 3 秒内切换回游戏界面...")
    time.sleep(3)
    load_polybridge_save()