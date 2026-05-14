# How to Find iDRAC IP Address

## If You're Already in iDRAC Settings

### Method 1: From iDRAC Configuration Menu (During Boot)
1. **During server boot**, press **Ctrl+E** when prompted
2. Navigate to **Network Settings** or **LAN Parameters**
3. Look for **IP Address** field
4. Note down the IP address shown (e.g., 192.168.1.100)

### Method 2: From BIOS/System Setup
1. Press **F2** during boot to enter System Setup
2. Navigate to **iDRAC Settings**
3. Select **Network**
4. The IP address will be displayed under **IPv4 Settings**

### Method 3: From iDRAC Web Interface (If Already Logged In)
1. Click on **Overview** or **Dashboard**
2. Look for **Network Information** section
3. IP address is displayed under **iDRAC Network Settings**

## Your Server's iDRAC Configuration

| Setting | Value |
|---------|-------|
| **IP Address** | 192.168.0.120 |
| **Gateway** | 192.168.0.1 |
| **Subnet Mask** | 255.255.255.0 |

---

## Network Connectivity Requirements

### YES - Same Network Required

Your device and the server **must be on the same local network** to access iDRAC.

| Your Device | Server Connection | Can Access iDRAC? |
|-------------|-------------------|-------------------|
| WiFi (same router) | Ethernet (same router) | ✅ Yes |
| WiFi (different network) | Ethernet (different router) | ❌ No |
| Ethernet (same switch) | Ethernet (same switch) | ✅ Yes |
| Phone on cellular | Ethernet (any network) | ❌ No |

### How to Check

**On your computer:**
```bash
# Check your IP address
ipconfig  # Windows
ifconfig  # macOS/Linux
ip addr   # Linux
```

Your device should have an IP in the **192.168.0.x** range (same subnet as the server).

**If your IP is different (e.g., 192.168.1.x):**
- Connect your device to the WiFi that the server is plugged into
- Or plug your computer into the same Ethernet switch/router

### Quick Test

Open a browser and go to: `http://192.168.0.120`

- **Works** → You're on the same network
- **Times out / Can't reach** → Different network or firewall blocking

---

## Default iDRAC Settings for Dell PowerEdge R620

| Setting | Default Value |
|---------|---------------|
| **IP Address** | Usually 192.168.1.100 or DHCP-assigned |
| **Username** | root |
| **Password** | calvin |
| **Network Mode** | DHCP (unless manually configured) |

## Finding iDRAC IP from Your Router

If you can't access iDRAC settings directly:

1. Log into your router's admin panel
2. Look for **DHCP Client List** or **Connected Devices**
3. Find device named **iDRAC** or with MAC address starting with Dell's prefix
4. Note the assigned IP address

## Finding iDRAC IP from Server OS (If Installed)

If you have Ubuntu/Linux installed on the server:

```bash
# Install ipmitool if not present
sudo apt install ipmitool

# Get iDRAC IP address
sudo ipmitool lan print 1 | grep "IP Address"
```

## Accessing iDRAC Web Interface

Once you have the IP address:

1. Open browser to: `http://<idrac-ip-address>`
2. Login with credentials (default: root/calvin)
3. You'll see the full management interface

## Common iDRAC IP Ranges

- **192.168.1.100** - Common default
- **192.168.0.120** - Alternative default
- **DHCP assigned** - Check your router's DHCP range (e.g., 192.168.1.2-254)

## Setting a Static IP for iDRAC

**Recommended for server stability:**

1. Access iDRAC settings (Ctrl+E during boot)
2. Navigate to **Network Settings**
3. Change from **DHCP** to **Static**
4. Set:
   - IP Address: `192.168.1.100` (or your preferred static IP)
   - Subnet Mask: `255.255.255.0`
   - Gateway: `192.168.1.1` (your router's IP)
5. Save and reboot

## Quick Reference

**Access during boot:**
- BIOS Setup: Press **F2**
- iDRAC Setup: Press **Ctrl+E**

**Default login:**
- Username: `root`
- Password: `calvin`

**Common URLs:**
- iDRAC Web: `http://192.168.1.100`
- Alternative: `https://192.168.1.100` (HTTPS)
