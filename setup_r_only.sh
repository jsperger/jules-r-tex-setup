#!/bin/bash

# ========================= R installation =========================
curl -f https://raw.githubusercontent.com/eddelbuettel/r2u/refs/heads/master/inst/scripts/add_cranapt_noble.sh | sudo bash

# ======================= Ark installation =========================
curl -LsSf https://github.com/posit-dev/air/releases/latest/download/air-installer.sh | sudo AIR_INSTALL_DIR=/usr/local/bin sh
sudo ln -sf /usr/local/bin/air /usr/local/bin/ark
