"""Open the local 3D workbench on an available loopback port."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


def main():
    root = Path(__file__).resolve().parent
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(root)))
    url = f"http://127.0.0.1:{server.server_port}/web/map-prototype/"
    print("三维工作台：" + url, flush=True)
    print("需要联网加载固定版本 Three.js / MapLibre。按 Ctrl+C 退出。", flush=True)
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
