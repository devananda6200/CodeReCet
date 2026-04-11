#!/bin/bash
# Extract the packaged YOLO model

if [ -f "best.pt.zip" ]; then
    echo "Extracting best.pt.zip..."
    unzip -q best.pt.zip
    echo "Model extracted successfully. The best.pt directory is now ready for use."
else
    echo "Error: best.pt.zip not found in this directory."
    echo "Make sure Git LFS is installed and the file was properly downloaded:"
    echo "  git lfs install"
    echo "  git lfs pull"
    exit 1
fi
