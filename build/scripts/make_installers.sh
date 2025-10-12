#!/bin/bash
# Lucid RDP - Cross-Platform Installer Creation Script
# ===================================================
#
# Creates installers for Windows (WiX/NSIS), macOS (dmg), and Linux (AppImage)
# using the frozen GUI executables from PyInstaller.
#
# Based on SPEC-2 requirements:
# - Windows: build MSI (WiX) or EXE (NSIS). Include service-free run; per-user install default
# - macOS: .app inside signed .dmg; hardened runtime; notarize with Apple Developer ID; staple ticket
# - Linux: AppImage (primary) + tar.gz; optional .deb/.rpm via fpm
#
# Usage:
#     ./make_installers.sh --gui user --platform windows-x64 --installer-type msi
#     ./make_installers.sh --gui admin --platform macos-universal --installer-type dmg
#     ./make_installers.sh --gui node --platform linux-x64 --installer-type appimage
#
# Author: Lucid RDP Build System
# License: MIT

set -euo pipefail

# Default values
GUI_NAME=""
PLATFORM=""
INSTALLER_TYPE=""
INPUT_DIR="dist"
OUTPUT_DIR="installers"
VERSION=""
SIGN_INSTALLER=false
VERBOSE=false
HELP=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# GUI configurations
declare -A GUI_CONFIGS=(
    ["user"]="LucidUserGUI:Lucid RDP User Client:User GUI for session management and client controls"
    ["admin"]="LucidAdminGUI:Lucid RDP Admin Console:Admin GUI for Pi appliance management"
    ["node"]="LucidNodeGUI:Lucid RDP Node Monitor:Node GUI for PoOT monitoring and payouts"
)

# Platform configurations
declare -A PLATFORM_CONFIGS=(
    ["windows-x64"]="win-amd64:exe:msi"
    ["macos-universal"]="macos-universal:app:dmg"
    ["linux-x64"]="linux-x86_64:bin:appimage"
    ["linux-arm64"]="linux-aarch64:bin:appimage"
)

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print verbose output
verbose_print() {
    if [ "$VERBOSE" = true ]; then
        print_color "$GRAY" "VERBOSE: $1"
    fi
}

# Function to show help
show_help() {
    cat << EOF
Lucid RDP - Cross-Platform Installer Creation Script
==================================================

Creates installers for Windows (WiX/NSIS), macOS (dmg), and Linux (AppImage).

Usage: $0 [OPTIONS]

Options:
    -g, --gui <name>            GUI to create installer for (user|admin|node)
    -p, --platform <platform>   Target platform (windows-x64|macos-universal|linux-x64|linux-arm64)
    -t, --installer-type <type> Installer type (msi|exe|dmg|appimage|tar.gz|deb|rpm)
    -i, --input-dir <path>      Input directory with frozen executables (default: dist)
    -o, --output-dir <path>     Output directory for installers (default: installers)
    -v, --version <version>     Version string (default: auto-detect)
    --sign                      Sign installer after creation
    --verbose                   Enable verbose output
    -h, --help                  Show this help message

Environment Variables:
    INSTALLER_VERSION           Default version string
    INSTALLER_COMPANY           Company name for installers
    INSTALLER_PRODUCT_NAME      Product name for installers
    INSTALLER_COPYRIGHT         Copyright string
    INSTALLER_LICENSE_FILE      Path to license file

Examples:
    # Create Windows MSI installer
    $0 --gui user --platform windows-x64 --installer-type msi
    
    # Create macOS DMG installer
    $0 --gui admin --platform macos-universal --installer-type dmg
    
    # Create Linux AppImage
    $0 --gui node --platform linux-x64 --installer-type appimage
    
    # Create signed Windows installer
    $0 --gui user --platform windows-x64 --installer-type msi --sign

Supported Installer Types:
    Windows: msi (WiX), exe (NSIS)
    macOS:   dmg
    Linux:   appimage, tar.gz, deb, rpm

Prerequisites:
    Windows: WiX Toolset or NSIS
    macOS:   dmgbuild, create-dmg
    Linux:   appimagetool, fpm (for deb/rpm)
EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_color "$CYAN" "Checking prerequisites..."
    
    local platform=$1
    local installer_type=$2
    
    case "$platform" in
        "windows-x64")
            case "$installer_type" in
                "msi")
                    if ! command -v candle.exe &> /dev/null && ! command -v light.exe &> /dev/null; then
                        print_color "$RED" "✗ WiX Toolset not found. Install from: https://wixtoolset.org/"
                        exit 1
                    fi
                    ;;
                "exe")
                    if ! command -v makensis &> /dev/null; then
                        print_color "$RED" "✗ NSIS not found. Install from: https://nsis.sourceforge.io/"
                        exit 1
                    fi
                    ;;
            esac
            ;;
        "macos-universal")
            if ! command -v dmgbuild &> /dev/null; then
                print_color "$RED" "✗ dmgbuild not found. Install with: pip install dmgbuild"
                exit 1
            fi
            ;;
        "linux-x64"|"linux-arm64")
            case "$installer_type" in
                "appimage")
                    if ! command -v appimagetool &> /dev/null; then
                        print_color "$RED" "✗ appimagetool not found. Install from: https://github.com/AppImage/AppImageKit"
                        exit 1
                    fi
                    ;;
                "deb"|"rpm")
                    if ! command -v fpm &> /dev/null; then
                        print_color "$RED" "✗ fpm not found. Install with: gem install fpm"
                        exit 1
                    fi
                    ;;
            esac
            ;;
    esac
    
    verbose_print "✓ Prerequisites check passed"
}

# Function to get version
get_version() {
    if [ -n "$VERSION" ]; then
        echo "$VERSION"
        return
    fi
    
    # Try to get version from git tag
    if command -v git &> /dev/null && git rev-parse --is-inside-work-tree &> /dev/null; then
        local git_version
        if git_version=$(git describe --tags --exact-match 2>/dev/null); then
            echo "${git_version#v}"  # Remove 'v' prefix if present
            return
        fi
    fi
    
    # Try to get version from environment
    if [ -n "${INSTALLER_VERSION:-}" ]; then
        echo "$INSTALLER_VERSION"
        return
    fi
    
    # Default version
    echo "1.0.0"
}

# Function to get GUI information
get_gui_info() {
    local gui_name=$1
    local info=${GUI_CONFIGS[$gui_name]}
    
    if [ -z "$info" ]; then
        print_color "$RED" "✗ Unknown GUI: $gui_name"
        exit 1
    fi
    
    IFS=':' read -r binary_name display_name description <<< "$info"
    echo "$binary_name|$display_name|$description"
}

# Function to get platform information
get_platform_info() {
    local platform=$1
    local info=${PLATFORM_CONFIGS[$platform]}
    
    if [ -z "$info" ]; then
        print_color "$RED" "✗ Unknown platform: $platform"
        exit 1
    fi
    
    IFS=':' read -r target_platform executable_type installer_suffix <<< "$info"
    echo "$target_platform|$executable_type|$installer_suffix"
}

# Function to create Windows MSI installer
create_windows_msi() {
    local input_dir=$1
    local output_dir=$2
    local gui_info=$3
    local platform_info=$4
    local version=$5
    
    IFS='|' read -r binary_name display_name description <<< "$gui_info"
    IFS='|' read -r target_platform executable_type installer_suffix <<< "$platform_info"
    
    print_color "$YELLOW" "Creating Windows MSI installer for $display_name"
    
    local gui_dir="$input_dir/$GUI_NAME/$PLATFORM"
    local app_dir="$gui_dir/$binary_name"
    
    if [ ! -d "$app_dir" ]; then
        print_color "$RED" "✗ Application directory not found: $app_dir"
        exit 1
    fi
    
    # Create WiX source file
    local wxs_file="$output_dir/${binary_name}.wxs"
    local company_name="${INSTALLER_COMPANY:-Lucid RDP}"
    local product_name="${INSTALLER_PRODUCT_NAME:-$display_name}"
    local copyright="${INSTALLER_COPYRIGHT:-Copyright (c) 2024 Lucid RDP}"
    local license_file="${INSTALLER_LICENSE_FILE:-LICENSE}"
    
    cat > "$wxs_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" 
           Name="$product_name" 
           Language="1033" 
           Version="$version" 
           Manufacturer="$company_name"
           UpgradeCode="$(uuidgen | tr '[:upper:]' '[:lower:]')">
    
    <Package InstallerVersion="200" 
             Compressed="yes" 
             InstallScope="perUser"
             Description="$description" />
    
    <MajorUpgrade DowngradeErrorMessage="A newer version is already installed." />
    <MediaTemplate />
    
    <Feature Id="ProductFeature" Title="$product_name" Level="1">
      <ComponentGroupRef Id="ProductComponents" />
    </Feature>
    
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="LocalAppDataFolder">
        <Directory Id="INSTALLFOLDER" Name="$binary_name" />
      </Directory>
    </Directory>
    
    <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
      <Component Id="MainExecutable" Guid="$(uuidgen | tr '[:upper:]' '[:lower:]')">
        <File Id="$binary_name.exe" 
              Source="$app_dir/$binary_name.exe" 
              KeyPath="yes" />
      </Component>
      
      <!-- Add all files from the application directory -->
      <Component Id="ApplicationFiles" Guid="$(uuidgen | tr '[:upper:]' '[:lower:]')">
        <CreateFolder />
        <RemoveFolder Id="RemoveApplicationFolder" On="uninstall" />
      </Component>
    </ComponentGroup>
    
    <!-- Add license file if it exists -->
EOF
    
    if [ -f "$license_file" ]; then
        cat >> "$wxs_file" << EOF
    <Component Id="LicenseFile" Guid="$(uuidgen | tr '[:upper:]' '[:lower:]')">
      <File Id="LICENSE" Source="$license_file" />
    </Component>
EOF
    fi
    
    cat >> "$wxs_file" << EOF
    
    <!-- UI Configuration -->
    <UIRef Id="WixUI_Minimal" />
    <WixVariable Id="WixUILicenseRtf" Value="$license_file" />
    
    <!-- Icon -->
    <Icon Id="icon.ico" SourceFile="icons/$GUI_NAME-icon.ico" />
    <Property Id="ARPPRODUCTICON" Value="icon.ico" />
    
  </Product>
</Wix>
EOF
    
    # Compile WiX source
    local wix_obj_dir="$output_dir/obj"
    mkdir -p "$wix_obj_dir"
    
    verbose_print "Compiling WiX source file: $wxs_file"
    if candle.exe -out "$wix_obj_dir/" "$wxs_file"; then
        print_color "$GREEN" "✓ WiX source compiled successfully"
    else
        print_color "$RED" "✗ WiX compilation failed"
        exit 1
    fi
    
    # Link WiX object files
    local msi_file="$output_dir/${binary_name}-${version}-${target_platform}.msi"
    local wixobj_file="$wix_obj_dir/${binary_name}.wixobj"
    
    verbose_print "Linking WiX object file: $wixobj_file"
    if light.exe -out "$msi_file" "$wixobj_file"; then
        print_color "$GREEN" "✓ MSI installer created: $msi_file"
    else
        print_color "$RED" "✗ WiX linking failed"
        exit 1
    fi
    
    echo "$msi_file"
}

# Function to create Windows EXE installer (NSIS)
create_windows_exe() {
    local input_dir=$1
    local output_dir=$2
    local gui_info=$3
    local platform_info=$4
    local version=$5
    
    IFS='|' read -r binary_name display_name description <<< "$gui_info"
    IFS='|' read -r target_platform executable_type installer_suffix <<< "$platform_info"
    
    print_color "$YELLOW" "Creating Windows EXE installer for $display_name"
    
    local gui_dir="$input_dir/$GUI_NAME/$PLATFORM"
    local app_dir="$gui_dir/$binary_name"
    
    if [ ! -d "$app_dir" ]; then
        print_color "$RED" "✗ Application directory not found: $app_dir"
        exit 1
    fi
    
    # Create NSIS script
    local nsi_file="$output_dir/${binary_name}.nsi"
    local company_name="${INSTALLER_COMPANY:-Lucid RDP}"
    local product_name="${INSTALLER_PRODUCT_NAME:-$display_name}"
    local copyright="${INSTALLER_COPYRIGHT:-Copyright (c) 2024 Lucid RDP}"
    
    cat > "$nsi_file" << EOF
; NSIS installer script for $display_name
!include "MUI2.nsh"

; General
Name "$product_name"
OutFile "$output_dir/${binary_name}-${version}-${target_platform}.exe"
InstallDir "\$LOCALAPPDATA\\$binary_name"
RequestExecutionLevel user

; Interface
!define MUI_ABORTWARNING
!define MUI_ICON "icons/$GUI_NAME-icon.ico"
!define MUI_UNICON "icons/$GUI_NAME-icon.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "$(LICENSE_FILE)"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer sections
Section "MainApplication" SecMain
    SetOutPath "\$INSTDIR"
    
    ; Copy all files from the application directory
    File /r "$app_dir\\*"
    
    ; Create shortcuts
    CreateDirectory "\$SMPROGRAMS\\$binary_name"
    CreateShortCut "\$SMPROGRAMS\\$binary_name\\$display_name.lnk" "\$INSTDIR\\$binary_name.exe"
    CreateShortCut "\$DESKTOP\\$display_name.lnk" "\$INSTDIR\\$binary_name.exe"
    
    ; Write uninstaller
    WriteUninstaller "\$INSTDIR\\Uninstall.exe"
    
    ; Write registry entries
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\$binary_name" "DisplayName" "$product_name"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\$binary_name" "UninstallString" "\$INSTDIR\\Uninstall.exe"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\$binary_name" "DisplayVersion" "$version"
    WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\$binary_name" "Publisher" "$company_name"
    WriteRegDWORD HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\$binary_name" "NoModify" 1
    WriteRegDWORD HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\$binary_name" "NoRepair" 1
SectionEnd

; Uninstaller section
Section "Uninstall"
    ; Remove files
    RMDir /r "\$INSTDIR"
    
    ; Remove shortcuts
    Delete "\$SMPROGRAMS\\$binary_name\\$display_name.lnk"
    RMDir "\$SMPROGRAMS\\$binary_name"
    Delete "\$DESKTOP\\$display_name.lnk"
    
    ; Remove registry entries
    DeleteRegKey HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\$binary_name"
SectionEnd

; License file
LicenseData "${INSTALLER_LICENSE_FILE:-LICENSE}"
EOF
    
    # Compile NSIS script
    verbose_print "Compiling NSIS script: $nsi_file"
    if makensis "$nsi_file"; then
        local exe_file="$output_dir/${binary_name}-${version}-${target_platform}.exe"
        print_color "$GREEN" "✓ EXE installer created: $exe_file"
        echo "$exe_file"
    else
        print_color "$RED" "✗ NSIS compilation failed"
        exit 1
    fi
}

# Function to create macOS DMG installer
create_macos_dmg() {
    local input_dir=$1
    local output_dir=$2
    local gui_info=$3
    local platform_info=$4
    local version=$5
    
    IFS='|' read -r binary_name display_name description <<< "$gui_info"
    IFS='|' read -r target_platform executable_type installer_suffix <<< "$platform_info"
    
    print_color "$YELLOW" "Creating macOS DMG installer for $display_name"
    
    local gui_dir="$input_dir/$GUI_NAME/$PLATFORM"
    local app_dir="$gui_dir/$binary_name.app"
    
    if [ ! -d "$app_dir" ]; then
        print_color "$RED" "✗ Application bundle not found: $app_dir"
        exit 1
    fi
    
    # Create DMG configuration
    local dmg_config_file="$output_dir/${binary_name}_dmg_settings.py"
    local company_name="${INSTALLER_COMPANY:-Lucid RDP}"
    local product_name="${INSTALLER_PRODUCT_NAME:-$display_name}"
    
    cat > "$dmg_config_file" << EOF
# DMG configuration for $display_name

import os.path

# DMG settings
format = 'UDBZ'
size = None
files = ['$app_dir']
symlinks = {'Applications': '/Applications'}
icon = 'icons/$GUI_NAME-icon.icns'
icon_locations = {
    '$binary_name.app': (200, 200),
    'Applications': (400, 200)
}
background = 'background.png'
window_rect = ((100, 100), (600, 400))
default_view = 'icon-view'
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
sidebar_width = 180
text_size = 16
icon_size = 128
EOF
    
    # Create DMG
    local dmg_file="$output_dir/${binary_name}-${version}-${target_platform}.dmg"
    
    verbose_print "Creating DMG: $dmg_file"
    if dmgbuild -s "$dmg_config_file" "$product_name" "$dmg_file"; then
        print_color "$GREEN" "✓ DMG installer created: $dmg_file"
        echo "$dmg_file"
    else
        print_color "$RED" "✗ DMG creation failed"
        exit 1
    fi
}

# Function to create Linux AppImage
create_linux_appimage() {
    local input_dir=$1
    local output_dir=$2
    local gui_info=$3
    local platform_info=$4
    local version=$5
    
    IFS='|' read -r binary_name display_name description <<< "$gui_info"
    IFS='|' read -r target_platform executable_type installer_suffix <<< "$platform_info"
    
    print_color "$YELLOW" "Creating Linux AppImage for $display_name"
    
    local gui_dir="$input_dir/$GUI_NAME/$PLATFORM"
    local app_dir="$gui_dir/$binary_name"
    
    if [ ! -d "$app_dir" ]; then
        print_color "$RED" "✗ Application directory not found: $app_dir"
        exit 1
    fi
    
    # Create AppDir structure
    local appdir="$output_dir/${binary_name}.AppDir"
    rm -rf "$appdir"
    mkdir -p "$appdir"
    
    # Copy application files
    cp -r "$app_dir"/* "$appdir/"
    
    # Create AppRun script
    cat > "$appdir/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/LucidUserGUI" "$@"
EOF
    chmod +x "$appdir/AppRun"
    
    # Create desktop file
    local product_name="${INSTALLER_PRODUCT_NAME:-$display_name}"
    cat > "$appdir/${binary_name}.desktop" << EOF
[Desktop Entry]
Name=$product_name
Comment=$description
Exec=LucidUserGUI
Icon=$binary_name
Type=Application
Categories=Network;
StartupNotify=true
EOF
    
    # Create AppImage
    local appimage_file="$output_dir/${binary_name}-${version}-${target_platform}.AppImage"
    
    verbose_print "Creating AppImage: $appimage_file"
    if appimagetool "$appdir" "$appimage_file"; then
        print_color "$GREEN" "✓ AppImage created: $appimage_file"
        echo "$appimage_file"
    else
        print_color "$RED" "✗ AppImage creation failed"
        exit 1
    fi
}

# Function to create Linux package (deb/rpm)
create_linux_package() {
    local input_dir=$1
    local output_dir=$2
    local gui_info=$3
    local platform_info=$4
    local version=$5
    local package_type=$6
    
    IFS='|' read -r binary_name display_name description <<< "$gui_info"
    IFS='|' read -r target_platform executable_type installer_suffix <<< "$platform_info"
    
    print_color "$YELLOW" "Creating Linux $package_type package for $display_name"
    
    local gui_dir="$input_dir/$GUI_NAME/$PLATFORM"
    local app_dir="$gui_dir/$binary_name"
    
    if [ ! -d "$app_dir" ]; then
        print_color "$RED" "✗ Application directory not found: $app_dir"
        exit 1
    fi
    
    # Create package with fpm
    local package_name="${binary_name,,}"  # Convert to lowercase
    local package_file="$output_dir/${package_name}-${version}-${target_platform}.${package_type}"
    local company_name="${INSTALLER_COMPANY:-Lucid RDP}"
    
    local fpm_args=(
        "--input-type" "dir"
        "--output-type" "$package_type"
        "--name" "$package_name"
        "--version" "$version"
        "--maintainer" "$company_name"
        "--description" "$description"
        "--vendor" "$company_name"
        "--license" "MIT"
        "--url" "https://github.com/HamiGames/Lucid"
        "--architecture" "$target_platform"
        "--package" "$package_file"
        "--prefix" "/opt/$package_name"
        "$app_dir"
    )
    
    verbose_print "Creating package with fpm: ${fpm_args[*]}"
    if fpm "${fpm_args[@]}"; then
        print_color "$GREEN" "✓ $package_type package created: $package_file"
        echo "$package_file"
    else
        print_color "$RED" "✗ $package_type package creation failed"
        exit 1
    fi
}

# Function to create tar.gz archive
create_tar_gz() {
    local input_dir=$1
    local output_dir=$2
    local gui_info=$3
    local platform_info=$4
    local version=$5
    
    IFS='|' read -r binary_name display_name description <<< "$gui_info"
    IFS='|' read -r target_platform executable_type installer_suffix <<< "$platform_info"
    
    print_color "$YELLOW" "Creating tar.gz archive for $display_name"
    
    local gui_dir="$input_dir/$GUI_NAME/$PLATFORM"
    local app_dir="$gui_dir/$binary_name"
    
    if [ ! -d "$app_dir" ]; then
        print_color "$RED" "✗ Application directory not found: $app_dir"
        exit 1
    fi
    
    # Create tar.gz archive
    local tar_file="$output_dir/${binary_name}-${version}-${target_platform}.tar.gz"
    
    verbose_print "Creating tar.gz archive: $tar_file"
    if tar -czf "$tar_file" -C "$gui_dir" "$binary_name"; then
        print_color "$GREEN" "✓ tar.gz archive created: $tar_file"
        echo "$tar_file"
    else
        print_color "$RED" "✗ tar.gz archive creation failed"
        exit 1
    fi
}

# Function to sign installer
sign_installer() {
    local installer_file=$1
    local platform=$2
    
    print_color "$YELLOW" "Signing installer: $installer_file"
    
    case "$platform" in
        "windows-x64")
            # Use Windows signing script
            if [ -f "build/scripts/sign_win.ps1" ]; then
                powershell.exe -File "build/scripts/sign_win.ps1" -InputPath "$installer_file" -CertificateThumbprint "${WINDOWS_CERT_THUMBPRINT:-}"
            else
                print_color "$YELLOW" "⚠ Windows signing script not found, skipping signing"
            fi
            ;;
        "macos-universal")
            # Use macOS signing script
            if [ -f "build/scripts/sign_mac.sh" ]; then
                bash "build/scripts/sign_mac.sh" -i "$installer_file" --notarize --staple
            else
                print_color "$YELLOW" "⚠ macOS signing script not found, skipping signing"
            fi
            ;;
        *)
            print_color "$YELLOW" "⚠ Signing not supported for platform: $platform"
            ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--gui)
            GUI_NAME="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -t|--installer-type)
            INSTALLER_TYPE="$2"
            shift 2
            ;;
        -i|--input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --sign)
            SIGN_INSTALLER=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            HELP=true
            shift
            ;;
        *)
            print_color "$RED" "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Show help if requested
if [ "$HELP" = true ]; then
    show_help
    exit 0
fi

# Main execution
main() {
    print_color "$CYAN" "Lucid RDP - Cross-Platform Installer Creation Script"
    print_color "$CYAN" "=================================================="
    
    # Validate required parameters
    if [ -z "$GUI_NAME" ]; then
        print_color "$RED" "✗ GUI name is required"
        show_help
        exit 1
    fi
    
    if [ -z "$PLATFORM" ]; then
        print_color "$RED" "✗ Platform is required"
        show_help
        exit 1
    fi
    
    if [ -z "$INSTALLER_TYPE" ]; then
        print_color "$RED" "✗ Installer type is required"
        show_help
        exit 1
    fi
    
    # Check prerequisites
    check_prerequisites "$PLATFORM" "$INSTALLER_TYPE"
    
    # Get version
    local version=$(get_version)
    verbose_print "Using version: $version"
    
    # Get GUI and platform information
    local gui_info=$(get_gui_info "$GUI_NAME")
    local platform_info=$(get_platform_info "$PLATFORM")
    
    verbose_print "GUI info: $gui_info"
    verbose_print "Platform info: $platform_info"
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Create installer based on type
    local installer_file=""
    
    case "$PLATFORM" in
        "windows-x64")
            case "$INSTALLER_TYPE" in
                "msi")
                    installer_file=$(create_windows_msi "$INPUT_DIR" "$OUTPUT_DIR" "$gui_info" "$platform_info" "$version")
                    ;;
                "exe")
                    installer_file=$(create_windows_exe "$INPUT_DIR" "$OUTPUT_DIR" "$gui_info" "$platform_info" "$version")
                    ;;
                *)
                    print_color "$RED" "✗ Unsupported installer type for Windows: $INSTALLER_TYPE"
                    exit 1
                    ;;
            esac
            ;;
        "macos-universal")
            case "$INSTALLER_TYPE" in
                "dmg")
                    installer_file=$(create_macos_dmg "$INPUT_DIR" "$OUTPUT_DIR" "$gui_info" "$platform_info" "$version")
                    ;;
                *)
                    print_color "$RED" "✗ Unsupported installer type for macOS: $INSTALLER_TYPE"
                    exit 1
                    ;;
            esac
            ;;
        "linux-x64"|"linux-arm64")
            case "$INSTALLER_TYPE" in
                "appimage")
                    installer_file=$(create_linux_appimage "$INPUT_DIR" "$OUTPUT_DIR" "$gui_info" "$platform_info" "$version")
                    ;;
                "tar.gz")
                    installer_file=$(create_tar_gz "$INPUT_DIR" "$OUTPUT_DIR" "$gui_info" "$platform_info" "$version")
                    ;;
                "deb"|"rpm")
                    installer_file=$(create_linux_package "$INPUT_DIR" "$OUTPUT_DIR" "$gui_info" "$platform_info" "$version" "$INSTALLER_TYPE")
                    ;;
                *)
                    print_color "$RED" "✗ Unsupported installer type for Linux: $INSTALLER_TYPE"
                    exit 1
                    ;;
            esac
            ;;
        *)
            print_color "$RED" "✗ Unsupported platform: $PLATFORM"
            exit 1
            ;;
    esac
    
    # Sign installer if requested
    if [ "$SIGN_INSTALLER" = true ]; then
        sign_installer "$installer_file" "$PLATFORM"
    fi
    
    print_color "$GREEN" "✓ Installer creation completed successfully"
    print_color "$CYAN" "Installer file: $installer_file"
}

# Run main function
main
