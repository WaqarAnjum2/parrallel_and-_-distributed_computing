# Network & Firewall Configuration Guide

This guide details configuring communication across LAN and Wi-Fi networks between the Client and Worker nodes.

---

## 🌐 Network Topology

- **Worker Node**: Typically a workstation with an NVIDIA GPU connected via Gigabit Ethernet or high-speed Wi-Fi (e.g. `192.168.1.10`).
- **Client Node**: A laptop or lower-power desktop on the same local subnet (e.g. `192.168.1.25`).
- **Port**: `8000` (Default TCP port used for HTTP REST endpoints and WebSocket stream).

---

## 🛡️ Windows Firewall Configuration

By default, Windows Firewall blocks incoming connections to unlisted ports. You must open port `8000` on the **Worker computer**.

### Method 1: Using PowerShell (Run as Administrator)
```powershell
New-NetFirewallRule -DisplayName "Distributed GPU Worker (TCP 8000)" `
    -Direction Inbound `
    -LocalPort 8000 `
    -Protocol TCP `
    -Action Allow `
    -Profile Private
```

### Method 2: Windows Defender GUI
1. Open **Windows Defender Firewall with Advanced Security**.
2. Click **Inbound Rules** > **New Rule...**.
3. Select **Port** > Click **Next**.
4. Select **TCP** and specify Specific local ports: `8000`.
5. Select **Allow the connection** > Click **Next**.
6. Check **Private** (recommended for home/lab LANs) > Click **Next**.
7. Name the rule `Distributed GPU Worker` and click **Finish**.

---

## 🔍 Network Verification Commands

From the **Client computer**, test network visibility:

1. **Ping Worker IP**:
   ```powershell
   ping 192.168.1.10
   ```
2. **Test TCP Port Reachability**:
   ```powershell
   Test-NetConnection -ComputerName 192.168.1.10 -Port 8000
   ```
   Should output `TcpTestSucceeded : True`.
3. **Query Worker Health via curl**:
   ```powershell
   curl http://192.168.1.10:8000/health
   ```
