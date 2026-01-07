Scripts for setting up Jules's environment for working with R and (Lua)LaTeX. 

Use a setup script by adding `curl -f {desired_environment}.sh | sudo bash` with the setup script you want to Jules's environment.

## Setup Scripts Overview

The following scripts are available to configure the environment:

| Setup Script | R | Quarto | Tex | Total Installation Size |
|---|---|---|---|---|
| `setup_quarto_latest.sh` | No | Latest Stable | No | 381 MB |
| `setup_quarto_prerelease.sh` | No | Prerelease | No | 388 MB |
| `setup_r_only.sh` | Yes | No | No | 242 MB |
| `setup_r_quarto_tex.sh` | Yes | Prerelease | Standard (latex-extra, luatex, science) | 1.4 GB |
| `setup_r_tex_full.sh` | Yes | Prerelease | Full (texlive-full) | 8.2 GB |
