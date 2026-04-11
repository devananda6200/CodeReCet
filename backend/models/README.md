# Model Files

This directory contains the YOLO11 model for PPE detection.

## Setup

The model is stored as `best.pt.zip` (a compressed archive) and tracked with Git LFS for efficient storage.

### First Time Setup (After Cloning)

1. **Install Git LFS** (if not already installed):
   ```bash
   git lfs install
   ```

2. **Pull LFS files**:
   ```bash
   git lfs pull
   ```

3. **Extract the model**:
   ```bash
   # On Linux/macOS:
   bash extract_model.sh
   
   # On Windows (PowerShell):
   Expand-Archive -Path best.pt.zip -DestinationPath . -Force
   ```

After extraction, the `best.pt/` directory will be available for the application to use.

## File Structure

- `best.pt.zip` - Compressed model archive (tracked with Git LFS)
- `best.pt/` - Extracted model directory (generated after extraction, ignored by Git)
- `extract_model.sh` - Bash script to extract the model
- `exports/` - Location for model export outputs

## Note

The actual `best.pt/` directory is gitignored to avoid committing thousands of individual model files. Only the zip archive is tracked in version control.
