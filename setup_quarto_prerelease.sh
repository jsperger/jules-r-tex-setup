#!/bin/bash
# Define repository and architecture
REPO="quarto-dev/quarto-cli"
ARCH_PATTERN="linux-amd64.deb"

# 1. Fetch the download URL for the latest release (including pre-releases)
DOWNLOAD_URL=$(curl -s https://api.github.com/repos/$REPO/releases | \
    jq -r '.[0].assets[] | select(.name | endswith("'"$ARCH_PATTERN"'")) | .browser_download_url')

# 2. Check if URL was found
if [ -z "$DOWNLOAD_URL" ] || [ "$DOWNLOAD_URL" == "null" ]; then
    echo "Error: Could not find the latest .deb asset for $ARCH_PATTERN."
    exit 1
fi

echo "Found latest version: $(basename $DOWNLOAD_URL)"

# 3. Download and install
# We use /tmp to avoid cluttering the current directory
DEST="/tmp/$(basename $DOWNLOAD_URL)"
curl -L -o "$DEST" "$DOWNLOAD_URL"
sudo apt update
sudo apt install -y "$DEST"

# 4. Cleanup
rm "$DEST"

# Verify installation
quarto --version
