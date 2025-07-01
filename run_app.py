import threading
import webbrowser
import time
import requests
import app  # 直接匯入 app.py 內的 Flask 物件


def start_flask():
    app.app.run(port=8504, debug=False, use_reloader=False)


def wait_for_server(url, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url)
            if r.status_code == 200:
                print("Flask 成功啟動")
                return True
        except Exception as e:
            print("等待中...", e)
            time.sleep(0.5)
    print("Flask 啟動逾時")
    return False


if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    if wait_for_server("http://127.0.0.1:8504"):
        webbrowser.open("http://127.0.0.1:8504")
        print("Flask 正在啟動...")
        threading.Thread(target=start_flask, daemon=True).start()
    else:
        print("啟動 Flask 失敗")
