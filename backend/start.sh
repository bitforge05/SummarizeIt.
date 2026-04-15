#!/bin/bash
# SummarizeIt — Backend Start Script
# Uses the correct Python with all packages installed

PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"

# Fallback to system python3 if 3.12 not found
if [ ! -f "$PYTHON" ]; then
  PYTHON="/usr/bin/python3"
fi

echo "▶ Starting backend with $($PYTHON --version)"
echo "▶ ffmpeg: $(which ffmpeg || echo '/opt/homebrew/bin/ffmpeg')"
echo ""

export PATH="/opt/homebrew/bin:$PATH"
$PYTHON main.py
