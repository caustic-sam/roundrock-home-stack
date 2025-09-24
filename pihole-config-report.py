#!/bin/bash

# Universal Raspberry Pi Diagnostics with HTTP Server
# Auto-discovers hardware and serves results via web interface
# Usage: sudo bash rpi_diagnostics_server.sh [port]

PORT=${1:-8080}
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
HTML_FILE="/tmp/rpi_diagnostics_${TIMESTAMP}.html"
TEMP_DIR="/tmp/rpi_diagnostics"

# Create temp directory
mkdir -p "$TEMP_DIR"

# Detect Pi Model and Hardware
detect_pi_hardware() {
    local pi_model=""
    local pi_revision=""
    local pi_memory=""
    local has_wifi=false
    local has_ethernet=false
    local has_ai_hat=false
    local has_cooling=false
    
    # Get Pi model info
    if [ -f /proc/cpuinfo ]; then
        pi_model=$(grep "Model" /proc/cpuinfo | cut -d':' -f2 | xargs)
        pi_revision=$(grep "Revision" /proc/cpuinfo | cut -d':' -f2 | xargs)
    fi
    
    # Get memory info
    pi_memory=$(grep MemTotal /proc/meminfo | awk '{printf "%.0f GB", $2/1024/1024}')
    
    # Detect network interfaces
    ip link show | grep -q "wlan" && has_wifi=true
    ip link show | grep -q "eth" && has_ethernet=true
    
    # Detect AI HAT (look for neural compute devices, I2C devices, etc.)
    if lsusb | grep -iq "coral\|neural\|tpu"; then
        has_ai_hat=true
    elif ls /dev/i2c-* 2>/dev/null | xargs -I {} i2cdetect -y {} 2>/dev/null | grep -q "[0-9a-f][0-9a-f]"; then
        # Check for I2C devices that might indicate AI HAT
        has_ai_hat=true
    fi
    
    # Detect cooling (fan control, temperature sensors)
    if [ -f /sys/class/thermal/cooling_device*/type ]; then
        grep -q "fan" /sys/class/thermal/cooling_device*/type 2>/dev/null && has_cooling=true
    fi
    
    # Check for GPIO fan control
    if pgrep -f "gpio.*fan" >/dev/null 2>&1 || systemctl is-active --quiet fancontrol; then
        has_cooling=true
    fi
    
    echo "$pi_model|$pi_revision|$pi_memory|$has_wifi|$has_ethernet|$has_ai_hat|$has_cooling"
}

# Generate comprehensive diagnostics
generate_diagnostics() {
    local output_file="$1"
    
    # Detect hardware
    IFS='|' read -r PI_MODEL PI_REVISION PI_MEMORY HAS_WIFI HAS_ETHERNET HAS_AI_HAT HAS_COOLING <<< "$(detect_pi_hardware)"
    
    cat > "$output_file" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raspberry Pi Diagnostics Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            line-height: 1.6; 
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: #333; 
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header .subtitle { font-size: 1.2em; opacity: 0.9; }
        .content { padding: 30px; }
        .hardware-overview {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .hw-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .hw-card.available { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .hw-card.warning { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .hw-card.error { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }
        .hw-card.success { background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%); }
        .section {
            background: #f8f9fa;
            margin: 20px 0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }
        .section-header {
            background: linear-gradient(135deg, #36d1dc 0%, #5b86e5 100%);
            color: white;
            padding: 15px 20px;
            font-weight: bold;
            font-size: 1.1em;
        }
        .section-content { padding: 20px; }
        pre {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            overflow-x: auto;
            font-size: 0.9em;
        }
        .status-good { color: #27ae60; font-weight: bold; }
        .status-warning { color: #f39c12; font-weight: bold; }
        .status-error { color: #e74c3c; font-weight: bold; }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .metric {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        .metric.warning { border-left-color: #f39c12; }
        .metric.error { border-left-color: #e74c3c; }
        .metric .label { font-size: 0.9em; color: #7f8c8d; }
        .metric .value { font-size: 1.3em; font-weight: bold; margin-top: 5px; }
        .refresh-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        }
        .refresh-btn:hover { transform: translateY(-2px); }
        .timestamp { text-align: center; color: #7f8c8d; margin-top: 30px; }
        @media (max-width: 768px) {
            .container { margin: 10px; border-radius: 10px; }
            .header { padding: 20px; }
            .header h1 { font-size: 2em; }
            .content { padding: 20px; }
        }
    </style>
    <script>
        function refreshPage() { window.location.reload(); }
        function toggleSection(id) {
            const content = document.getElementById(id);
            const display = content.style.display === 'none' ? 'block' : 'none';
            content.style.display = display;
        }
    </script>
</head>
<body>
    <button class="refresh-btn" onclick="refreshPage()">🔄 Refresh</button>
    <div class="container">
        <div class="header">
            <h1>🥧 Raspberry Pi Diagnostics</h1>
            <div class="subtitle">Comprehensive Hardware & Network Analysis</div>
        </div>
        <div class="content">
EOF

    # Hardware Overview Section
    echo '<div class="hardware-overview">' >> "$output_file"
    
    # Pi Model Card
    cat >> "$output_file" << EOF
            <div class="hw-card success">
                <h3>🖥️ System</h3>
                <div style="font-size: 1.1em; margin: 10px 0;">$PI_MODEL</div>
                <div>Memory: $PI_MEMORY</div>
                <div style="font-size: 0.9em; opacity: 0.8;">Rev: $PI_REVISION</div>
            </div>
EOF

    # Network Cards
    if [ "$HAS_ETHERNET" = "true" ]; then
        ETH_STATUS=$(ip link show eth0 2>/dev/null | grep "state UP" && echo "Connected" || echo "Disconnected")
        ETH_CLASS=$([ "$ETH_STATUS" = "Connected" ] && echo "success" || echo "warning")
        cat >> "$output_file" << EOF
            <div class="hw-card $ETH_CLASS">
                <h3>🔌 Ethernet</h3>
                <div style="font-size: 1.1em; margin: 10px 0;">$ETH_STATUS</div>
EOF
        if [ "$ETH_STATUS" = "Connected" ]; then
            ETH_IP=$(ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
            echo "                <div>IP: $ETH_IP</div>" >> "$output_file"
        fi
        echo "            </div>" >> "$output_file"
    fi

    if [ "$HAS_WIFI" = "true" ]; then
        WIFI_STATUS=$(iwconfig wlan0 2>/dev/null | grep -q "ESSID" && echo "Connected" || echo "Disconnected")
        WIFI_CLASS=$([ "$WIFI_STATUS" = "Connected" ] && echo "success" || echo "warning")
        cat >> "$output_file" << EOF
            <div class="hw-card $WIFI_CLASS">
                <h3>📶 WiFi</h3>
                <div style="font-size: 1.1em; margin: 10px 0;">$WIFI_STATUS</div>
EOF
        if [ "$WIFI_STATUS" = "Connected" ]; then
            WIFI_SSID=$(iwconfig wlan0 2>/dev/null | grep ESSID | cut -d'"' -f2)
            WIFI_SIGNAL=$(iwconfig wlan0 2>/dev/null | grep "Signal level" | awk -F'Signal level=' '{print $2}' | awk '{print $1}')
            echo "                <div>SSID: $WIFI_SSID</div>" >> "$output_file"
            echo "                <div>Signal: $WIFI_SIGNAL</div>" >> "$output_file"
        fi
        echo "            </div>" >> "$output_file"
    fi

    # AI HAT Card
    if [ "$HAS_AI_HAT" = "true" ]; then
        cat >> "$output_file" << EOF
            <div class="hw-card available">
                <h3>🤖 AI HAT</h3>
                <div style="font-size: 1.1em; margin: 10px 0;">Detected</div>
                <div style="font-size: 0.9em;">Neural Processing Unit</div>
            </div>
EOF
    fi

    # Cooling Card
    if [ "$HAS_COOLING" = "true" ]; then
        TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d'=' -f2 | cut -d"'" -f1 || echo "N/A")
        TEMP_CLASS="success"
        if [ "$TEMP" != "N/A" ] && [ "${TEMP%.*}" -gt 70 ]; then
            TEMP_CLASS="warning"
        elif [ "$TEMP" != "N/A" ] && [ "${TEMP%.*}" -gt 80 ]; then
            TEMP_CLASS="error"
        fi
        cat >> "$output_file" << EOF
            <div class="hw-card $TEMP_CLASS">
                <h3>🌪️ Cooling</h3>
                <div style="font-size: 1.1em; margin: 10px 0;">Active</div>
                <div>Temp: ${TEMP}°C</div>
            </div>
EOF
    fi

    # Storage Card
    STORAGE_INFO=$(df -h / | awk 'NR==2{printf "%s used of %s (%.0f%%)", $3, $2, ($3/$2)*100}')
    cat >> "$output_file" << EOF
            <div class="hw-card available">
                <h3>💾 Storage</h3>
                <div style="font-size: 0.9em; margin: 10px 0;">$STORAGE_INFO</div>
            </div>
EOF

    echo '</div>' >> "$output_file"

    # System Status Section
    echo '<div class="section">' >> "$output_file"
    echo '<div class="section-header">📊 System Status</div>' >> "$output_file"
    echo '<div class="section-content"><div class="metric-grid">' >> "$output_file"
    
    # Uptime
    UPTIME=$(uptime -p)
    echo "<div class=\"metric\"><div class=\"label\">Uptime</div><div class=\"value\">$UPTIME</div></div>" >> "$output_file"
    
    # Load Average
    LOAD=$(uptime | awk -F'load average:' '{print $2}' | xargs)
    echo "<div class=\"metric\"><div class=\"label\">Load Average</div><div class=\"value\">$LOAD</div></div>" >> "$output_file"
    
    # Memory Usage
    MEM_USAGE=$(free | awk 'NR==2{printf "%.1f%% of %.1fGB", $3*100/$2, $2/1024/1024 }')
    echo "<div class=\"metric\"><div class=\"label\">Memory Usage</div><div class=\"value\">$MEM_USAGE</div></div>" >> "$output_file"
    
    # Temperature
    if command -v vcgencmd &> /dev/null; then
        TEMP=$(vcgencmd measure_temp | cut -d'=' -f2)
        TEMP_CLASS=""
        TEMP_NUM=$(echo $TEMP | cut -d"'" -f1)
        if [ "${TEMP_NUM%.*}" -gt 70 ]; then TEMP_CLASS="warning"; fi
        if [ "${TEMP_NUM%.*}" -gt 80 ]; then TEMP_CLASS="error"; fi
        echo "<div class=\"metric $TEMP_CLASS\"><div class=\"label\">Temperature</div><div class=\"value\">$TEMP</div></div>" >> "$output_file"
    fi
    
    echo '</div></div></div>' >> "$output_file"

    # Power Supply Section (Critical for Pi 5 with AI HAT)
    echo '<div class="section">' >> "$output_file"
    echo '<div class="section-header">⚡ Power Supply Analysis</div>' >> "$output_file"
    echo '<div class="section-content">' >> "$output_file"
    
    if command -v vcgencmd &> /dev/null; then
        THROTTLED=$(vcgencmd get_throttled)
        if [ "$THROTTLED" = "throttled=0x0" ]; then
            echo '<div class="status-good">✅ No power issues detected</div>' >> "$output_file"
        else
            echo '<div class="status-error">❌ Power/thermal throttling detected!</div>' >> "$output_file"
        fi
        
        echo '<div class="metric-grid">' >> "$output_file"
        for voltage in core sdram_c sdram_i sdram_p; do
            VOLT=$(vcgencmd measure_volts $voltage | cut -d'=' -f2)
            echo "<div class=\"metric\"><div class=\"label\">$voltage voltage</div><div class=\"value\">$VOLT</div></div>" >> "$output_file"
        done
        echo '</div>' >> "$output_file"
        
        echo '<pre>' >> "$output_file"
        echo "Throttling Status: $THROTTLED" >> "$output_file"
        dmesg | grep -i "under-voltage\|voltage\|power\|pmic" | tail -5 >> "$output_file"
        echo '</pre>' >> "$output_file"
    fi
    echo '</div></div>' >> "$output_file"

    # AI HAT Specific Diagnostics
    if [ "$HAS_AI_HAT" = "true" ]; then
        echo '<div class="section">' >> "$output_file"
        echo '<div class="section-header">🤖 AI HAT Diagnostics</div>' >> "$output_file"
        echo '<div class="section-content">' >> "$output_file"
        
        echo '<pre>' >> "$output_file"
        echo "=== AI/Neural Processing Devices ===" >> "$output_file"
        lsusb | grep -i "coral\|neural\|tpu\|edge" >> "$output_file" 2>/dev/null || echo "No USB neural devices found" >> "$output_file"
        
        echo "" >> "$output_file"
        echo "=== I2C Devices ===" >> "$output_file"
        for i2c_bus in /dev/i2c-*; do
            if [ -c "$i2c_bus" ]; then
                bus_num=$(basename "$i2c_bus" | sed 's/i2c-//')
                echo "Bus $bus_num:" >> "$output_file"
                i2cdetect -y "$bus_num" 2>/dev/null | grep -v "^     " >> "$output_file"
            fi
        done 2>/dev/null || echo "No I2C buses found" >> "$output_file"
        
        echo "" >> "$output_file"
        echo "=== GPIO Usage ===" >> "$output_file"
        if command -v pinout &> /dev/null; then
            pinout | head -20 >> "$output_file"
        else
            echo "pinout command not available" >> "$output_file"
        fi
        
        echo "" >> "$output_file"
        echo "=== Power Consumption Estimate ===" >> "$output_file"
        if [ -f /sys/class/hwmon/hwmon*/power1_input ]; then
            for power_file in /sys/class/hwmon/hwmon*/power1_input; do
                if [ -r "$power_file" ]; then
                    power_uw=$(cat "$power_file")
                    power_w=$(echo "scale=2; $power_uw / 1000000" | bc -l)
                    echo "Current power draw: ${power_w}W" >> "$output_file"
                fi
            done
        else
            echo "Power monitoring not available" >> "$output_file"
        fi
        echo '</pre>' >> "$output_file"
        echo '</div></div>' >> "$output_file"
    fi

    # Network Diagnostics
    echo '<div class="section">' >> "$output_file"
    echo '<div class="section-header">🌐 Network Diagnostics</div>' >> "$output_file"
    echo '<div class="section-content">' >> "$output_file"
    
    # Connectivity Tests
    echo '<div class="metric-grid">' >> "$output_file"
    
    # Gateway ping
    GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
    if [ ! -z "$GATEWAY" ]; then
        if ping -c 2 -W 3 "$GATEWAY" >/dev/null 2>&1; then
            echo '<div class="metric success"><div class="label">Gateway</div><div class="value status-good">✅ Reachable</div></div>' >> "$output_file"
        else
            echo '<div class="metric error"><div class="label">Gateway</div><div class="value status-error">❌ Unreachable</div></div>' >> "$output_file"
        fi
    fi
    
    # Internet connectivity
    if ping -c 2 -W 3 8.8.8.8 >/dev/null 2>&1; then
        echo '<div class="metric success"><div class="label">Internet</div><div class="value status-good">✅ Connected</div></div>' >> "$output_file"
    else
        echo '<div class="metric error"><div class="label">Internet</div><div class="value status-error">❌ No Connection</div></div>' >> "$output_file"
    fi
    
    # DNS Resolution
    if nslookup google.com >/dev/null 2>&1; then
        echo '<div class="metric success"><div class="label">DNS</div><div class="value status-good">✅ Working</div></div>' >> "$output_file"
    else
        echo '<div class="metric error"><div class="label">DNS</div><div class="value status-error">❌ Failed</div></div>' >> "$output_file"
    fi
    
    echo '</div>' >> "$output_file"
    
    # Interface Details
    echo '<pre>' >> "$output_file"
    echo "=== Network Interfaces ===" >> "$output_file"
    ip addr show >> "$output_file"
    echo "" >> "$output_file"
    echo "=== Routing Table ===" >> "$output_file"
    ip route show >> "$output_file"
    echo "" >> "$output_file"
    echo "=== Network Statistics ===" >> "$output_file"
    cat /proc/net/dev | grep -E "(eth0|wlan0)" >> "$output_file"
    echo '</pre>' >> "$output_file"
    
    echo '</div></div>' >> "$output_file"

    # Storage & USB Diagnostics
    echo '<div class="section">' >> "$output_file"
    echo '<div class="section-header">💾 Storage & USB</div>' >> "$output_file"
    echo '<div class="section-content">' >> "$output_file"
    echo '<pre>' >> "$output_file"
    echo "=== Disk Usage ===" >> "$output_file"
    df -h >> "$output_file"
    echo "" >> "$output_file"
    echo "=== External Storage ===" >> "$output_file"
    lsblk >> "$output_file"
    echo "" >> "$output_file"
    echo "=== USB Devices ===" >> "$output_file"
    lsusb >> "$output_file"
    echo "" >> "$output_file"
    echo "=== Mount Points ===" >> "$output_file"
    mount | grep -v "tmpfs\|proc\|sys" >> "$output_file"
    echo '</pre>' >> "$output_file"
    echo '</div></div>' >> "$output_file"

    # System Logs
    echo '<div class="section">' >> "$output_file"
    echo '<div class="section-header" onclick="toggleSection('"'"'logs'"'"')" style="cursor: pointer;">📋 System Logs (Click to toggle)</div>' >> "$output_file"
    echo '<div class="section-content" id="logs" style="display: none;">' >> "$output_file"
    echo '<pre>' >> "$output_file"
    echo "=== Recent Critical Events ===" >> "$output_file"
    dmesg | grep -i -E "(error|fail|warn|critical|panic)" | tail -10 >> "$output_file"
    echo "" >> "$output_file"
    echo "=== Network Events ===" >> "$output_file"
    dmesg | grep -i -E "(network|wifi|eth|usb)" | tail -10 >> "$output_file"
    echo "" >> "$output_file"
    echo "=== Power/Thermal Events ===" >> "$output_file"
    dmesg | grep -i -E "(power|thermal|voltage|temperature)" | tail -10 >> "$output_file"
    echo '</pre>' >> "$output_file"
    echo '</div></div>' >> "$output_file"

    # Recommendations
    echo '<div class="section">' >> "$output_file"
    echo '<div class="section-header">💡 Recommendations</div>' >> "$output_file"
    echo '<div class="section-content">' >> "$output_file"
    
    # Generate smart recommendations based on detected hardware
    echo '<div style="background: #e8f4f8; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">' >> "$output_file"
    echo '<h4>Hardware-Specific Recommendations:</h4><ul>' >> "$output_file"
    
    if [[ "$PI_MODEL" == *"Pi 5"* ]]; then
        echo '<li><strong>Pi 5 Power:</strong> Ensure you have the official 27W USB-C power supply</li>' >> "$output_file"
        if [ "$HAS_AI_HAT" = "true" ]; then
            echo '<li><strong>AI HAT Power:</strong> AI HAT increases power requirements - monitor for under-voltage warnings</li>' >> "$output_file"
        fi
    fi
    
    if [ "$HAS_AI_HAT" = "true" ]; then
        echo '<li><strong>AI HAT Cooling:</strong> Neural processing generates heat - ensure adequate cooling</li>' >> "$output_file"
        echo '<li><strong>AI HAT Performance:</strong> Monitor I2C communication and GPIO usage</li>' >> "$output_file"
    fi
    
    if [ "$HAS_WIFI" = "true" ] && [ "$HAS_ETHERNET" = "true" ]; then
        echo '<li><strong>Dual Network:</strong> Consider disabling WiFi if using Ethernet to avoid routing conflicts</li>' >> "$output_file"
    fi
    
    if [ "$HAS_COOLING" = "true" ]; then
        echo '<li><strong>Active Cooling:</strong> Monitor fan operation and clean dust regularly</li>' >> "$output_file"
    fi
    
    echo '</ul></div>' >> "$output_file"
    echo '</div></div>' >> "$output_file"

    # Footer
    echo '<div class="timestamp">Report generated: '"$(date)"'<br>Auto-refresh available via refresh button</div>' >> "$output_file"
    echo '</div></div></body></html>' >> "$output_file"
}

# Python HTTP Server
create_http_server() {
    cat > "$TEMP_DIR/server.py" << 'EOF'
#!/usr/bin/env python3
import http.server
import socketserver
import os
import sys
import threading
import time
import subprocess
import signal

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/tmp", **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            # Find the latest diagnostics file
            import glob
            diag_files = glob.glob('/tmp/rpi_diagnostics_*.html')
            if diag_files:
                latest_file = max(diag_files, key=os.path.getctime)
                self.path = '/' + os.path.basename(latest_file)
        elif self.path == '/refresh':
            # Regenerate diagnostics
            subprocess.run(['sudo', 'bash', sys.argv[0], sys.argv[1]], 
                         capture_output=True, text=True)
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return
        
        super().do_GET()

    def log_message(self, format, *args):
        # Suppress default logging
        pass

def signal_handler(sig, frame):
    print(f"\n🛑 Shutting down server...")
    sys.exit(0)

if __name__ == "__main__":
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"🌐 Raspberry Pi Diagnostics Server")
        print(f"📊 Serving diagnostics at: http://localhost:{PORT}")
        print(f"🔄 Auto-refresh: http://localhost:{PORT}/refresh")
        print(f"⏹️  Press Ctrl+C to stop")
        print("-" * 50)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            print(f"\n👋 Server stopped")
EOF
}

# Main execution
main() {
    echo "🚀 Starting Raspberry Pi Diagnostics Server..."
    echo "🔍 Detecting hardware configuration..."
    
    # Generate diagnostics report
    generate_diagnostics "$HTML_FILE"
    
    # Create HTTP server
    create_http_server
    
    echo "✅ Diagnostics report generated: $HTML_FILE"
    echo "🌐 Starting web server on port $PORT..."
    
    # Start the server
    cd "$TEMP_DIR"
    python3 server.py "$PORT"
}

# Check if running as root for certain operations
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Some diagnostics require root privileges. Run with sudo for complete analysis."
    echo "🔄 Continuing with limited diagnostics..."
fi

main "$@"