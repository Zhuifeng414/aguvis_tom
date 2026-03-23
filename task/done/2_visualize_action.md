Action Space:

Here’s the list organized line by line:

* pyautogui.moveTo(x, y)

* pyautogui.click(x, y)

* pyautogui.write('text')

* pyautogui.press('enter')

* pyautogui.hotkey('ctrl', 'c')

* pyautogui.scroll(200)

* pyautogui.dragTo(x, y)

* browser.select_option(x, y, value)

* mobile.swipe(from, to)

* mobile.home()

* mobile.back()

* mobile.open_app(name)

* terminate(status)

* answer(text)

the output may looks like above action space, now help me visualize the action in current UI design, the requests are as follows:

1. if the ouput action contain x, y, make a red box upon the (x, y), x axis is left to right 0 to 1, y axis is up to down 0 to one

2. when my mouse move upon the image area, you shoud show a coordination, and show the x and y of my mouse realtime
