#!bin/bash
# scripts/lib/lucid-host-config-path.sh
# File: /app/scripts/lib/lucid-host-config-path.sh
# x-lucid-file-path: /app/scripts/lib/lucid-host-config-path.sh
# x-lucid-file-directory: /app/scripts/lib
# x-lucid-file-type: shell
#
# Purpose:
# - operates in the Dockerfile image creation process
# - uses the Dockerfile WORKDIR /app as the starting path for all scripts
# - uses the x-files-listing.txt to resolve the pathway conflicts for all .py files in the project
# - sets starting path as: /app for ./
# - only runs while the image is created for the project
# - in the builder stage, runs before any scripts are executed
# - sets all service names according to ./configs/host-configs.yml
# - sets all ENV variables according to ./configs/.env.master & ./configs/.env.secrets
# - checks that the edit made is valid and not conflicting with other services
# - removes all duplicate paths and only keeps the most specific pat
# - unifies the directories for ./scripts across all services
# - sets the WORKDIR /build aka ./ as the REPO_ROOT_PATH for all scripts to use



