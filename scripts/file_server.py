#!/usr/bin/env python3
import http.server
import socketserver
import os
import sys

PORT = 8080
DIRECTORY = "/root/users-data/Lulu"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def log_message(self, format, *args):
        # 禁用日志输出
        pass

def main():
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"服务器启动在端口 {PORT}")
        print(f"文件下载链接: http://你的服务器IP:{PORT}/约翰·列侬生平.xlsx")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
            httpd.shutdown()

if __name__ == "__main__":
    main()