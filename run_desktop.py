import sys
import os
import threading
import time
import socket
from pathlib import Path

# Setup Django Environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'military_leaves_project.settings')

import django
django.setup()

from django.core.servers.basehttp import WSGIServer, WSGIRequestHandler
from military_leaves_project.wsgi import application

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

PORT = 8000
# Check if 8000 is available, otherwise pick a free port
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', PORT))
except OSError:
    PORT = get_free_port()

class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy HTTP logs in desktop mode
        pass

def start_django_server(port):
    server = WSGIServer(('127.0.0.1', port), QuietHandler)
    server.set_app(application)
    server.serve_forever()

def main():
    # 1. Start Django in a background thread
    server_thread = threading.Thread(target=start_django_server, args=(PORT,), daemon=True)
    server_thread.start()
    time.sleep(0.5)

    # 2. Launch Native Desktop Window using PySide6 (Qt)
    from PySide6.QtWidgets import QApplication, QMainWindow
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtCore import QUrl, Qt
    from PySide6.QtGui import QIcon

    app = QApplication(sys.argv)
    app.setApplicationName("منظومة متابعة إجازات العاملين المدنيين")

    # Main Desktop Window
    main_window = QMainWindow()
    main_window.setWindowTitle("منظومة متابعة وتصديق إجازات العاملين المدنيين - قيادة المنطقة العسكرية")
    main_window.resize(1300, 850)

    # Embedded WebEngine View (No browser bars, 100% desktop app look)
    web_view = QWebEngineView()
    web_view.setUrl(QUrl(f"http://127.0.0.1:{PORT}/login/"))
    main_window.setCentralWidget(web_view)

    # Maximize and show window
    main_window.showMaximized()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
