#!/bin/bash

# Color codes for pretty printing
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'
CYAN='\033[0;36m'

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}          R2 Droid Driving Course Controller Installer            ${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo ""

# Helper function to ask yes/no questions (defaults to yes)
ask_yes_no() {
    local prompt=$1
    local default=$2
    local response
    
    if [ "$default" = "Y" ] || [ "$default" = "y" ] || [ -z "$default" ]; then
        prompt="$prompt [Y/n] "
        default="Y"
    else
        prompt="$prompt [y/N] "
        default="N"
    fi
    
    read -r -p "$prompt" response
    response=${response:-$default}
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        return 0 # True
    else
        return 1 # False
    fi
}

# --- Step 1: Install System Dependencies for Pygame & Python ---
if ask_yes_no "Step 1: Install system packages for Pygame (SDL2, python-dev, build tools)?" "Y"; then
    echo -e "${YELLOW}Installing system dependencies...${NC}"
    if sudo apt update && sudo apt install -y build-essential python3-dev \
        libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
        libfreetype6-dev libportmidi-dev libjpeg-dev; then
        echo -e "${GREEN}✓ System dependencies installed successfully.${NC}"
    else
        echo -e "${RED}✗ Failed to install system dependencies.${NC}"
    fi
else
    echo -e "${BLUE}Skipping Step 1.${NC}"
fi
echo ""

# --- Step 2: Install and Configure MQTT Broker ---
if ask_yes_no "Step 2: Install and configure Mosquitto MQTT broker?" "Y"; then
    echo -e "${YELLOW}Installing and configuring Mosquitto...${NC}"
    if sudo apt update && sudo apt install -y mosquitto mosquitto-clients; then
        # Configure anonymous connections for local devices on port 1883
        CONF_FILE="/etc/mosquitto/conf.d/local.conf"
        echo -e "${YELLOW}Checking Mosquitto configuration...${NC}"
        
        # Ensure directory exists
        sudo mkdir -p /etc/mosquitto/conf.d
        
        # Write config if it doesn't exist or isn't configured
        if [ ! -f "$CONF_FILE" ] || ! grep -q "listener 1883" "$CONF_FILE"; then
            echo -e "${YELLOW}Writing configuration to $CONF_FILE...${NC}"
            sudo tee "$CONF_FILE" > /dev/null <<EOF
listener 1883 0.0.0.0
allow_anonymous true
EOF
        else
            echo -e "${GREEN}✓ Mosquitto already configured.${NC}"
        fi
        
        echo -e "${YELLOW}Restarting Mosquitto service...${NC}"
        sudo systemctl restart mosquitto
        sudo systemctl enable mosquitto
        echo -e "${GREEN}✓ Mosquitto broker setup complete.${NC}"
    else
        echo -e "${RED}✗ Failed to install Mosquitto.${NC}"
    fi
else
    echo -e "${BLUE}Skipping Step 2.${NC}"
fi
echo ""

# --- Step 3: Setup Virtual Environment & Python Packages ---
if ask_yes_no "Step 3: Create Python virtual environment and install packages?" "Y"; then
    echo -e "${YELLOW}Creating Python virtual environment 'venv'...${NC}"
    python3 -m venv venv
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo -e "${YELLOW}Upgrading pip...${NC}"
        pip install --upgrade pip
        echo -e "${YELLOW}Installing Python dependencies (from requirements.txt)...${NC}"
        if pip install -r requirements.txt; then
            echo -e "${GREEN}✓ Python packages installed successfully.${NC}"
        else
            echo -e "${RED}✗ Failed to install Python dependencies.${NC}"
            echo -e "${YELLOW}If Pygame failed to compile, make sure Step 1 was executed and all SDL2 development packages were installed.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Failed to activate virtual environment.${NC}"
        exit 1
    fi
else
    echo -e "${BLUE}Skipping Step 3.${NC}"
fi
echo ""

# --- Step 4: Configure systemd Service ---
if ask_yes_no "Step 4: Configure systemd background service (r2course.service)?" "Y"; then
    CURRENT_USER=$USER
    CURRENT_DIR=$PWD
    SERVICE_FILE="/etc/systemd/system/r2course.service"
    
    echo -e "${YELLOW}Configuring systemd service for user: ${BLUE}$CURRENT_USER${YELLOW} and directory: ${BLUE}$CURRENT_DIR${NC}"
    
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=R2Course FastAPI Controller Service
After=network-online.target
Wants=network-online.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 $CURRENT_DIR/main_fast.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${YELLOW}Enabling and starting service...${NC}"
    sudo systemctl daemon-reload
    sudo systemctl enable r2course.service
    sudo systemctl start r2course.service
    echo -e "${GREEN}✓ systemd service installed and started.${NC}"
else
    echo -e "${BLUE}Skipping Step 4.${NC}"
fi
echo ""

# --- Step 5: Configure Wi-Fi Hotspot ---
if ask_yes_no "Step 5 (Optional): Configure 'r2course' Wi-Fi Access Point?" "N"; then
    echo -e "${YELLOW}Attempting to configure hotspot via NetworkManager (nmcli)...${NC}"
    if command -v nmcli &> /dev/null; then
        echo -e "${YELLOW}Creating hotspot...${NC}"
        if sudo nmcli device wifi hotspot ssid r2course password r2builders ifname wlan0; then
            echo -e "${YELLOW}Modifying hotspot configuration...${NC}"
            sudo nmcli connection modify Hotspot ipv4.addresses 192.168.43.1/24
            sudo nmcli connection modify Hotspot ipv4.method shared
            echo -e "${YELLOW}Restarting hotspot...${NC}"
            sudo nmcli connection down Hotspot
            sudo nmcli connection up Hotspot
            echo -e "${GREEN}✓ Wi-Fi Access Point 'r2course' successfully configured!${NC}"
        else
            echo -e "${RED}✗ Failed to create hotspot. Check that wlan0 interface is free and available.${NC}"
        fi
    else
        echo -e "${RED}✗ nmcli is not installed or not in PATH. NetworkManager is required.${NC}"
    fi
else
    echo -e "${BLUE}Skipping Step 5.${NC}"
fi

echo ""
echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}                Installation Process Complete!                    ${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo -e "You can activate the environment manually using:"
echo -e "  ${CYAN}source venv/bin/activate${NC}"
echo -e "Or check the service status with:"
echo -e "  ${CYAN}sudo systemctl status r2course.service${NC}"
echo -e "=================================================================="
