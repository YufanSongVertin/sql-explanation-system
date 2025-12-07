#!/bin/bash
cd "$(dirname "$0")"

echo "====================================="
echo " SQL Explain - Setup and Run (macOS)"
echo "====================================="

# ---- 1. Check Python 3 ----
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] Python 3 is not installed. Please install Python 3.10+ first."
    read -n 1 -s -r -p "Press any key to exit..."
    exit 1
fi

# ---- 2. Create virtual environment if needed ----
VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating Python virtual environment in '$VENV_DIR'..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        read -n 1 -s -r -p "Press any key to exit..."
        exit 1
    fi

    echo "[INFO] Activating virtual environment..."
    source "$VENV_DIR/bin/activate"

    echo "[INFO] Upgrading pip..."
    pip install --upgrade pip

    echo "[INFO] Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies."
        read -n 1 -s -r -p "Press any key to exit..."
        exit 1
    fi
else
    echo "[INFO] Virtual environment already exists. Activating..."
    source "$VENV_DIR/bin/activate"
fi

# ---- 3. Start Streamlit app ----
echo "[INFO] Starting Streamlit app..."
# Run in background so the script can continue
streamlit run app_streamlit.py &

# ---- 4. Wait a bit and open browser ----
echo "[INFO] Waiting for Streamlit server to start..."
sleep 4

echo "[INFO] Opening browser at http://localhost:8501 ..."
open "http://localhost:8501"

echo "====================================="
echo " SQL Explain UI should now be running."
echo " Keep this window open to see logs."
echo "====================================="

# Prevent terminal from closing immediately
read -n 1 -s -r -p "Press any key to close this window..."
