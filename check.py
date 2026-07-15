"""环境诊断脚本"""
import sys
import os

print("=" * 50)
print("Python 版本:", sys.version.split()[0])
print("Python 路径:", sys.executable)
print()

print("sys.path:")
for p in sys.path[:5]:
    print(f"  {p}")
print()

# 检查 streamlit
try:
    import streamlit
    print(f"[OK] streamlit {streamlit.__version__}")
    print(f"     路径: {streamlit.__file__}")
except ImportError as e:
    print(f"[FAIL] streamlit: {e}")

# 检查 requests
try:
    import requests
    print(f"[OK] requests {requests.__version__}")
except ImportError as e:
    print(f"[FAIL] requests: {e}")

# 检查 uvicorn
try:
    import uvicorn
    print(f"[OK] uvicorn {uvicorn.__version__}")
except ImportError:
    print("[FAIL] uvicorn not found")

# 检查端口占用
import socket
for port in [8501, 8502, 3000]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = s.connect_ex(('localhost', port))
    s.close()
    status = "BUSY" if result == 0 else "free"
    print(f"  port {port}: {status}")

print("=" * 50)
