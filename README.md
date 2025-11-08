# ===== NOTES =====
# 1. Place server_fastapi.py, client_pyqt5.py, start_server.sh and run_client.sh in same folder.
# 2. If you already have 'dogrotadb.sqlite' from previous versions, this server will reuse it.
# 3. Install packages for server: pip install fastapi uvicorn[standard] aiosqlite python-multipart
# 4. Install packages for client: pip install pyqt5 pillow requests websocket-client
# 5. Because all users are on the same Mac, clients connect to ws://127.0.0.1:8000/ws and http://127.0.0.1:8000
# 6. The WebSocket broadcasts whenever a change happens (children added/removed, mark_done, image uploaded, password changed, etc.).
#
# If you want, אני יכול:
# - להוסיף קובץ launchd/automator ל-mac כדי ליצור קיצור (אייקון) לכל משתמש.
# - להוסיף התקנה שנכנסת ל-Applications.
# - להוסיף הצפנה בסיסית לסיסמה במקום לשמור אותה בטקסט בגלוי (hashing + salted).
