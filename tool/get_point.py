import pyautogui
import time

print("请将鼠标移动到你想点击的按钮上...")
try:
    while True:
        x, y = pyautogui.position()
        position_str = f'X: {x:>4} Y: {y:>4}'
        print(position_str, end='\r')
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n已退出。")


## settings x 45 y 41
## load x 39 y 112
## loadfiles x 1192 y 634

## sharevideo x1271 y833
## confirm x1593 y1078
## rerun  x1470 y830