#!/bin/bash

# Update package list
sudo apt-get update

# Target system config file
INTERFACES_FILE="/etc/network/interfaces"

# Interfaces
WLAN_IFACE="wlan0"
ETH_IFACE="eth0"

# Static IP configuration for eth0
STATIC_IP="192.168.1.5"
NETMASK="255.255.255.0"

# Scan for networks
echo "Scanning available Wi-Fi networks..."
IFS=$'\n' read -d '' -r -a networks <<< "$(nmcli -t -f SSID dev wifi | grep -v '^$' | sort -u)"

# Display networks
echo "Found networks:"
for i in "${!networks[@]}"; do
    echo "$((i+1))) ${networks[$i]}"
done

# User selects network
read -p "Please enter the number of the network you want to connect to: " choice

# Validate input
if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#networks[@]} )); then
    echo "Invalid selection."
    exit 1
fi

SSID="${networks[$((choice-1))]}"
read -s -p "Enter password for '$SSID': " PASSWORD
echo

sudo apt install ifupdown -y
sudo systemctl disable --now NetworkManager

# Create config content
CONFIG_CONTENT=$(cat <<EOF
auto lo
iface lo inet loopback

auto $WLAN_IFACE
iface $WLAN_IFACE inet dhcp
    wpa-ssid "$SSID"
    wpa-psk "$PASSWORD"

auto $ETH_IFACE
iface $ETH_IFACE inet static
    address $STATIC_IP
    netmask $NETMASK
EOF
)

# Write to /etc/network/interfaces using sudo
echo "Writing new network configuration..."
echo "$CONFIG_CONTENT" | sudo tee "$INTERFACES_FILE" > /dev/null

echo "Network configuration has been written to $INTERFACES_FILE."

ifdown --force wlan0 lo
ifup -a
systemctl unmask networking
systemctl enable networking
systemctl restart networking

# Install required packages
sudo apt-get install -y python3-numpy
sudo apt-get install -y libblas-dev
sudo apt-get install -y libcap-dev
sudo apt-get install -y liblapack-dev
sudo apt-get install -y python3-dev
sudo apt-get install -y libatlas-base-dev
sudo apt-get install -y gfortran
sudo apt-get install -y python3-setuptools
sudo apt-get install -y python3-scipy
sudo apt-get install -y python3-h5py
sudo apt-get install -y python3-opencv
sudo apt-get install -y python3-virtualenv
sudo apt-get install -y python3-picamera2
sudo apt-get install -y python3-libcamera
sudo apt-get install -y python3-matplotlib
sudo apt-get install -y python3-virtualenv
sudo apt-get install -y libcap-dev
sudo apt-get install -y libatlas-base-dev 
sudo apt-get install -y ffmpeg 
sudo apt-get install -y libopenjp2-7
sudo apt-get install -y libcamera-dev
sudo apt-get install -y libkms++-dev 
sudo apt-get install -y libfmt-dev 
sudo apt-get install -y libdrm-dev

# Create virtual environment
virtualenv --system-site-packages dobot
source dobot/bin/activate

# Install Python packages via pip
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

sudo chown -R pi .
