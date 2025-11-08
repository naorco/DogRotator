# ===== start_server.sh =====
# Make executable: chmod +x start_server.sh
# Run: ./start_server.sh

#!/bin/bash
echo "🚀 Starting Dog Rotator server on 127.0.0.1:8000"
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
