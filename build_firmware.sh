#!/bin/bash

# Ensure we are in the workspace root
cd "$(dirname "$0")"

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "=========================================================="
    echo "Usage: ./build_firmware.sh <project_dir> <type> <version>"
    echo "=========================================================="
    echo "Example: ./build_firmware.sh Arduino/Bump_Sensor bump 2.0.2"
    echo "Example: ./build_firmware.sh Arduino/Timer timer 1.5.0"
    exit 1
fi

PROJECT_DIR=$1
TYPE=$2
VERSION=$3
OUTPUT_FILE="firmware_binaries/${TYPE}_${VERSION}.bin"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Directory '$PROJECT_DIR' does not exist."
    exit 1
fi

# Ensure output directory exists
mkdir -p firmware_binaries

echo "🔨 Compiling $PROJECT_DIR with PlatformIO..."
platformio run -d "$PROJECT_DIR"

if [ $? -ne 0 ]; then
    echo "❌ Compilation failed!"
    exit 1
fi

echo "📦 Searching for compiled binary..."
BIN_FILE=$(find "$PROJECT_DIR/.pio/build" -name "firmware.bin" | head -n 1)

if [ -f "$BIN_FILE" ]; then
    cp "$BIN_FILE" "$OUTPUT_FILE"
    echo "✅ Success! Binary published and ready for OTA at: $OUTPUT_FILE"
else
    echo "❌ Error: Could not find compiled firmware.bin"
    exit 1
fi
