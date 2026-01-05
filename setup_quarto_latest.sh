#!/bin/bash

# Configuration
REPO="quarto-dev/quarto-cli"
ARCH_PATTERN="linux-amd64.deb"

# 1. Get the download URL for the latest stable asset
# The /releases/latest endpoint specifically excludes pre-releases
DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | \
    jq -r '.assets[] | select(.name | endswith("'"$ARCH_PATTERN"'")) | .browser_download_url')

# 2. Check if the URL was successfully retrieved
if [ -z "$DOWNLOAD_URL" ] || [ "$DOWNLOAD_URL" == "null" ]; then
    echo "Error: Could not find the stable .deb asset for $ARCH_PATTERN."
    exit 1
fi

FILE_NAME=$(basename "$DOWNLOAD_URL")
echo "Found latest stable version: $FILE_NAME"

# 3. Download to /tmp
curl -L -o "/tmp/$FILE_NAME" "$DOWNLOAD_URL"

# 4. Install using apt to resolve dependencies
sudo apt update
sudo apt install -y "/tmp/$FILE_NAME"

# 5. Cleanup
rm "/tmp/$FILE_NAME"

# Verify
quarto --version
