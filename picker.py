import cv2
import pyautogui
import numpy as np
import configparser
import win32gui
import win32con
import win32ui
import subprocess

GAME_WINDOW_NAME = "Android Screen"

rectangles = []
slot_index = 1

def get_game_window_rect():
    hwnd = win32gui.FindWindow(None, GAME_WINDOW_NAME)
    if not hwnd:
        raise Exception(f"Game window '{GAME_WINDOW_NAME}' not found.")
    win32gui.SetForegroundWindow(hwnd)
    rect = win32gui.GetWindowRect(hwnd)
    return rect  # (left, top, right, bottom)

def screenshot_window(rect):
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top

    hwnd = win32gui.WindowFromPoint((left + 5, top + 5))
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
    saveDC.SelectObject(saveBitMap)

    saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    img = np.frombuffer(bmpstr, dtype='uint8')
    img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    return img

def get_screenshot():
    # Use adb to get a screenshot
    result = subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=subprocess.PIPE)
    image_data = result.stdout

    # Convert binary PNG data to a NumPy array
    image_array = np.frombuffer(image_data, dtype=np.uint8)

    # Decode the image
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return img

def mouse_callback(event, x, y, flags, param):
    global rectangles, slot_index
    if event == cv2.EVENT_LBUTTONDOWN:
        rectangles.append([(x, y)])
    elif event == cv2.EVENT_LBUTTONUP:
        rectangles[-1].append((x, y))
        print(f"Slot {slot_index} drawn: {rectangles[-1]}")
        slot_index += 1

def main():
    img = get_screenshot()
    clone = img.copy()

    cv2.namedWindow("Draw Slots (Press Enter When Done)")
    cv2.setMouseCallback("Draw Slots (Press Enter When Done)", mouse_callback)

    while True:
        temp = clone.copy()
        for box in rectangles:
            if len(box) == 2:
                x1, y1 = box[0]
                x2, y2 = box[1]
                cv2.rectangle(temp, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.imshow("Draw Slots (Press Enter When Done)", temp)
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter
            break

    cv2.destroyAllWindows()

    # Save to config.ini using relative values
    width, height = img.shape[1], img.shape[0]
    config = configparser.ConfigParser()
    config["Slots"] = {}
    for i, box in enumerate(rectangles):
        if len(box) == 2:
            x1, y1 = box[0]
            x2, y2 = box[1]
            x, y = min(x1,x2), min(y1,y2)
            w, h = abs(x2 - x1), abs(y2 - y1)
            rel_x = x / width
            rel_y = y / height
            rel_w = w / width
            rel_h = h / height
            config["Slots"][f"slot_{i+1}"] = f"{rel_x:.3f},{rel_y:.3f},{rel_w:.3f},{rel_h:.3f}"

    with open("config.ini", "w") as f:
        config.write(f)

    print("✅ config.ini updated using window-relative slot positions.")

if __name__ == "__main__":
    main()