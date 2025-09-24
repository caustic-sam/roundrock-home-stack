#!/usr/bin/env python3
"""
Universal Raspberry Pi Diagnostics Server
Auto-discovers hardware and serves results via web interface
Usage: python3 rpi_diagnostics.py [port]
"""

import os
import sys
import time
import subprocess
import socket
import json
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import signal

class RPiDiagnostics:
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.hardware_info = self.detect_hardware()
        
    def run_command(self, cmd, shell=True):
        """Run command and return output safely"""
        try:
            result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=10)
            return result.stdout.strip()
        except:
            return ""
    
    def detect_hardware(self):
        """Detect Pi hardware configuration"""
        info = {
            'model': 'Unknown',
            'revision': 'Unknown', 
            'memory': '0 GB',
            'has_wifi': False,
            'has_ethernet': False,
            'has_ai_hat': False,
            'has_cooling': False
        }
        
        # Get Pi model info
        cpuinfo = self.run_command("cat /proc/cpuinfo")
        for line in cpuinfo.split('\n'):
            if 'Model' in line:
                info['model'] = line.split(':', 1)[1].strip()
            elif 'Revision' in line:
                info['revision'] = line.split(':', 1)[1].strip()
        
        # Get memory info
        meminfo = self.run_command("grep MemTotal /proc/meminfo")
        if meminfo:
            mem_kb = int(meminfo.split()[1])
            info['memory'] = f"{mem_kb/1024/1024:.0f} GB"
        
        # Detect network interfaces
        info['has_wifi'] = bool(self.run_command("ip link show | grep wlan"))
        info['has_ethernet'] = bool(self.run_command("ip link show | grep eth"))
        
        # Detect AI HAT (look for neural devices, I2C activity)
        usb_devices = self.run_command("lsusb")
        info['has_ai_hat'] = any(keyword in usb_devices.lower() 
                                for keyword in ['coral', 'neural', 'tpu', 'edge'])
        
        # Check I2C for AI HAT
        if not info['has_ai_hat']:
            i2c_check = self.run_command("ls /dev/i2c-* 2>/dev/null")
            if i2c_check:
                info['has_ai_hat'] = True
        
        # Detect cooling
        cooling_check1 = self.run_command("find /sys/class/thermal -name '*fan*' 2>/dev/null")
        cooling_check2 = self.run_command("systemctl is-active fancontrol 2>/dev/null")
        cooling_check3 = self.run_command("pgrep -f 'gpio.*fan' 2>/dev/null")
        info['has_cooling'] = bool(cooling_check1 or cooling_check2 == "active" or cooling_check3)
        
        return info
    
    def get_system_status(self):
        """Get current system status metrics"""
        status = {}
        
        # Uptime
        status['uptime'] = self.run_command("uptime -p")
        
        # Load average
        uptime_out = self.run_command("uptime")
        if 'load average:' in uptime_out:
            status['load'] = uptime_out.split('load average:')[1].strip()
        
        # Memory usage
        mem_out = self.run_command("free")
        if mem_out:
            lines = mem_out.split('\n')
            if len(lines) > 1:
                mem_line = lines[1].split()
                total = int(mem_line[1])
                used = int(mem_line[2])
                status['memory_usage'] = f"{used*100/total:.1f}% of {total/1024/1024:.1f}GB"
        
        # Temperature
        temp = self.run_command("vcgencmd measure_temp 2>/dev/null")
        if temp:
            status['temperature'] = temp.split('=')[1] if '=' in temp else "N/A"
        else:
            # Try alternative temperature reading
            temp_file = self.run_command("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
            if temp_file and temp_file.isdigit():
                temp_c = int(temp_file) / 1000
                status['temperature'] = f"{temp_c:.1f}'C"
            else:
                status['temperature'] = "N/A"
        
        return status
    
    def get_power_status(self):
        """Get power supply status"""
        power = {}
        
        # Throttling status
        throttled = self.run_command("vcgencmd get_throttled 2>/dev/null")
        power['throttled'] = throttled if throttled else "N/A"
        power['has_issues'] = throttled != "throttled=0x0" if throttled else False
        
        # Voltages
        voltages = {}
        for rail in ['core', 'sdram_c', 'sdram_i', 'sdram_p']:
            volt = self.run_command(f"vcgencmd measure_volts {rail} 2>/dev/null")
            if volt and '=' in volt:
                voltages[rail] = volt.split('=')[1]
            else:
                voltages[rail] = "N/A"
        power['voltages'] = voltages
        
        # Power events in dmesg
        power_events = self.run_command("dmesg | grep -i 'under-voltage\\|voltage\\|power\\|pmic' | tail -5")
        power['recent_events'] = power_events.split('\n') if power_events else []
        
        return power
    
    def get_network_status(self):
        """Get network connectivity status"""
        network = {}
        
        # Interface status
        if self.hardware_info['has_ethernet']:
            eth_link = self.run_command("ip link show eth0 2>/dev/null")
            eth_status = "Connected" if "state UP" in eth_link else "Disconnected"
            network['ethernet'] = {'status': eth_status}
            if eth_status == "Connected":
                eth_ip = self.run_command("ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1")
                network['ethernet']['ip'] = eth_ip if eth_ip else "No IP"
        
        if self.hardware_info['has_wifi']:
            wifi_info = self.run_command("iwconfig wlan0 2>/dev/null")
            wifi_connected = "ESSID" in wifi_info and "Not-Associated" not in wifi_info
            network['wifi'] = {'status': "Connected" if wifi_connected else "Disconnected"}
            if wifi_connected:
                # Extract SSID
                ssid_match = re.search(r'ESSID:"([^"]*)"', wifi_info)
                if ssid_match:
                    network['wifi']['ssid'] = ssid_match.group(1)
                # Extract signal strength
                signal_match = re.search(r'Signal level=([^\s]*)', wifi_info)
                if signal_match:
                    network['wifi']['signal'] = signal_match.group(1)
        
        # Connectivity tests
        gateway = self.run_command("ip route | grep default | awk '{print $3}' | head -1")
        network['gateway_reachable'] = False
        network['internet_reachable'] = False
        network['dns_working'] = False
        
        if gateway:
            gateway_test = self.run_command(f"ping -c 2 -W 3 {gateway} >/dev/null 2>&1; echo $?")
            network['gateway_reachable'] = gateway_test == "0"
        
        internet_test = self.run_command("ping -c 2 -W 3 8.8.8.8 >/dev/null 2>&1; echo $?")
        network['internet_reachable'] = internet_test == "0"
        
        dns_test = self.run_command("nslookup google.com >/dev/null 2>&1; echo $?")
        network['dns_working'] = dns_test == "0"
        
        # Interface details
        network['interfaces'] = self.run_command("ip addr show")
        network['routes'] = self.run_command("ip route show")
        network['stats'] = self.run_command("cat /proc/net/dev | grep -E '(eth0|wlan0)'")
        
        return network
    
    def get_storage_info(self):
        """Get storage and USB information"""
        storage = {}
        
        storage['disk_usage'] = self.run_command("df -h")
        storage['block_devices'] = self.run_command("lsblk")
        storage['usb_devices'] = self.run_command("lsusb")
        storage['mounts'] = self.run_command("mount | grep -v 'tmpfs\\|proc\\|sys'")
        
        return storage
    
    def get_ai_hat_info(self):
        """Get AI HAT specific information"""
        if not self.hardware_info['has_ai_hat']:
            return {}
        
        ai_info = {}
        
        # Neural devices
        ai_info['usb_neural'] = self.run_command("lsusb | grep -i 'coral\\|neural\\|tpu\\|edge'")
        if not ai_info['usb_neural']:
            ai_info['usb_neural'] = "No USB neural devices found"
        
        # I2C devices
        i2c_info = []
        i2c_buses = self.run_command("ls /dev/i2c-* 2>/dev/null").split()
        for bus in i2c_buses:
            if bus:
                bus_num = bus.split('-')[-1]
                bus_devices = self.run_command(f"i2cdetect -y {bus_num} 2>/dev/null")
                if bus_devices:
                    i2c_info.append(f"Bus {bus_num}:\n{bus_devices}")
        ai_info['i2c_devices'] = '\n'.join(i2c_info) if i2c_info else "No I2C devices found"
        
        # GPIO info
        ai_info['gpio_info'] = self.run_command("pinout 2>/dev/null | head -20")
        if not ai_info['gpio_info']:
            ai_info['gpio_info'] = "GPIO info not available"
        
        # Power consumption
        power_files = self.run_command("ls /sys/class/hwmon/hwmon*/power1_input 2>/dev/null").split()
        if power_files:
            for power_file in power_files:
                if power_file:
                    power_uw = self.run_command(f"cat {power_file} 2>/dev/null")
                    if power_uw and power_uw.isdigit():
                        power_w = int(power_uw) / 1000000
                        ai_info['power_draw'] = f"{power_w:.2f}W"
                        break
        
        if 'power_draw' not in ai_info:
            ai_info['power_draw'] = "Power monitoring not available"
        
        return ai_info
    
    def get_system_logs(self):
        """Get relevant system logs"""
        logs = {}
        
        logs['critical_events'] = self.run_command("dmesg | grep -i -E '(error|fail|warn|critical|panic)' | tail -10")
        if not logs['critical_events']:
            logs['critical_events'] = "No critical events found"
            
        logs['network_events'] = self.run_command("dmesg | grep -i -E '(network|wifi|eth|usb)' | tail -10")
        if not logs['network_events']:
            logs['network_events'] = "No network events found"
            
        logs['power_events'] = self.run_command("dmesg | grep -i -E '(power|thermal|voltage|temperature)' | tail -10")
        if not logs['power_events']:
            logs['power_events'] = "No power/thermal events found"
        
        return logs
    
    def generate_html_report(self):
        """Generate comprehensive HTML report"""
        
        # Collect all diagnostics data
        system_status = self.get_system_status()
        power_status = self.get_power_status()
        network_status = self.get_network_status()
        storage_info = self.get_storage_info()
        ai_info = self.get_ai_hat_info()
        logs = self.get_system_logs()
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raspberry Pi Diagnostics Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            line-height: 1.6; 
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: #333; 
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ font-size: 1.2em; opacity: 0.9; }}
        .content {{ padding: 30px; }}
        .hardware-overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .hw-card {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .hw-card.available {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        .hw-card.warning {{ background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }}
        .hw-card.error {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }}
        .hw-card.success {{ background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%); }}
        .section {{
            background: #f8f9fa;
            margin: 20px 0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }}
        .section-header {{
            background: linear-gradient(135deg, #36d1dc 0%, #5b86e5 100%);
            color: white;
            padding: 15px 20px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        .section-content {{ padding: 20px; }}
        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            overflow-x: auto;
            font-size: 0.9em;
            white-space: pre-wrap;
        }}
        .status-good {{ color: #27ae60; font-weight: bold; }}
        .status-warning {{ color: #f39c12; font-weight: bold; }}
        .status-error {{ color: #e74c3c; font-weight: bold; }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        .metric {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}
        .metric.warning {{ border-left-color: #f39c12; }}
        .metric.error {{ border-left-color: #e74c3c; }}
        .metric.success {{ border-left-color: #27ae60; }}
        .metric .label {{ font-size: 0.9em; color: #7f8c8d; }}
        .metric .value {{ font-size: 1.3em; font-weight: bold; margin-top: 5px; }}
        .refresh-btn {{
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
        }}
        .refresh-btn:hover {{ transform: translateY(-2px); }}
        .timestamp {{ text-align: center; color: #7f8c8d; margin-top: 30px; }}
        .collapsible {{
            cursor: pointer;
            user-select: none;
        }}
        .collapsible:hover {{ opacity: 0.8; }}
        @media (max-width: 768px) {{
            .container {{ margin: 10px; border-radius: 10px; }}
            .header {{ padding: 20px; }}
            .header h1 {{ font-size: 2em; }}
            .content {{ padding: 20px; }}
        }}
    </style>
    <script>
        function refreshPage() {{ window.location.reload(); }}
        function toggleSection(id) {{
            const content = document.getElementById(id);
            const display = content.style.display === 'none' ? 'block' : 'none';
            content.style.display = display;
        }}
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
            <div class="hardware-overview">
                <div class="hw-card success">
                    <h3>🖥️ System</h3>
                    <div style="font-size: 1.1em; margin: 10px 0;">{self.hardware_info['model']}</div>
                    <div>Memory: {self.hardware_info['memory']}</div>
                    <div style="font-size: 0.9em; opacity: 0.8;">Rev: {self.hardware_info['revision']}</div>
                </div>"""
        
        # Ethernet card
        if self.hardware_info['has_ethernet']:
            eth_status = network_status.get('ethernet', {}).get('status', 'Unknown')
            eth_class = "success" if eth_status == "Connected" else "warning"
            eth_ip = network_status.get('ethernet', {}).get('ip', '')
            html_content += f"""
                <div class="hw-card {eth_class}">
                    <h3>🔌 Ethernet</h3>
                    <div style="font-size: 1.1em; margin: 10px 0;">{eth_status}</div>
                    {'<div>IP: ' + eth_ip + '</div>' if eth_ip and eth_ip != 'No IP' else ''}
                </div>"""
        
        # WiFi card
        if self.hardware_info['has_wifi']:
            wifi_status = network_status.get('wifi', {}).get('status', 'Unknown')
            wifi_class = "success" if wifi_status == "Connected" else "warning"
            wifi_ssid = network_status.get('wifi', {}).get('ssid', '')
            wifi_signal = network_status.get('wifi', {}).get('signal', '')
            html_content += f"""
                <div class="hw-card {wifi_class}">
                    <h3>📶 WiFi</h3>
                    <div style="font-size: 1.1em; margin: 10px 0;">{wifi_status}</div>
                    {'<div>SSID: ' + wifi_ssid + '</div>' if wifi_ssid else ''}
                    {'<div>Signal: ' + wifi_signal + '</div>' if wifi_signal else ''}
                </div>"""
        
        # AI HAT card
        if self.hardware_info['has_ai_hat']:
            html_content += """
                <div class="hw-card available">
                    <h3>🤖 AI HAT</h3>
                    <div style="font-size: 1.1em; margin: 10px 0;">Detected</div>
                    <div style="font-size: 0.9em;">Neural Processing Unit</div>
                </div>"""
        
        # Cooling card
        if self.hardware_info['has_cooling']:
            temp = system_status.get('temperature', 'N/A')
            temp_class = "success"
            if temp != 'N/A' and any(char.isdigit() for char in temp):
                try:
                    temp_val = float(''.join(c for c in temp.split('°')[0].split("'")[0] if c.isdigit() or c == '.'))
                    if temp_val > 70:
                        temp_class = "warning"
                    if temp_val > 80:
                        temp_class = "error"
                except:
                    pass
                    
            html_content += f"""
                <div class="hw-card {temp_class}">
                    <h3>🌪️ Cooling</h3>
                    <div style="font-size: 1.1em; margin: 10px 0;">Active</div>
                    <div>Temp: {temp}</div>
                </div>"""
        
        # Storage card
        storage_usage = self.run_command("df -h / | awk 'NR==2{printf \"%s used of %s\", $3, $2}'")
        if not storage_usage:
            storage_usage = "Storage info unavailable"
        html_content += f"""
                <div class="hw-card available">
                    <h3>💾 Storage</h3>
                    <div style="font-size: 0.9em; margin: 10px 0;">{storage_usage}</div>
                </div>
            </div>"""
        
        # System Status Section
        html_content += f"""
            <div class="section">
                <div class="section-header">📊 System Status</div>
                <div class="section-content">
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="label">Uptime</div>
                            <div class="value">{system_status.get('uptime', 'N/A')}</div>
                        </div>
                        <div class="metric">
                            <div class="label">Load Average</div>
                            <div class="value">{system_status.get('load', 'N/A')}</div>
                        </div>
                        <div class="metric">
                            <div class="label">Memory Usage</div>
                            <div class="value">{system_status.get('memory_usage', 'N/A')}</div>
                        </div>
                        <div class="metric">
                            <div class="label">Temperature</div>
                            <div class="value">{system_status.get('temperature', 'N/A')}</div>
                        </div>
                    </div>
                </div>
            </div>"""
        
        # Power Supply Section
        power_class = "status-good" if not power_status.get('has_issues', True) else "status-error"
        power_icon = "✅" if not power_status.get('has_issues', True) else "❌"
        power_msg = "No power issues detected" if not power_status.get('has_issues', True) else "Power/thermal throttling detected!"
        
        html_content += f"""
            <div class="section">
                <div class="section-header">⚡ Power Supply Analysis</div>
                <div class="section-content">
                    <div class="{power_class}">{power_icon} {power_msg}</div>
                    <div class="metric-grid">"""
        
        for rail, voltage in power_status.get('voltages', {}).items():
            html_content += f"""
                        <div class="metric">
                            <div class="label">{rail} voltage</div>
                            <div class="value">{voltage}</div>
                        </div>"""
        
        html_content += f"""
                    </div>
                    <pre>Throttling Status: {power_status.get('throttled', 'N/A')}
{chr(10).join(power_status.get('recent_events', ['No recent power events']))}</pre>
                </div>
            </div>"""
        
        # AI HAT Section
        if self.hardware_info['has_ai_hat']:
            html_content += f"""
            <div class="section">
                <div class="section-header">🤖 AI HAT Diagnostics</div>
                <div class="section-content">
                    <pre>=== AI/Neural Processing Devices ===
{ai_info.get('usb_neural', 'No USB neural devices found')}

=== I2C Devices ===
{ai_info.get('i2c_devices', 'No I2C devices found')}

=== GPIO Usage ===
{ai_info.get('gpio_info', 'GPIO info not available')}

=== Power Consumption Estimate ===
{ai_info.get('power_draw', 'Power monitoring not available')}</pre>
                </div>
            </div>"""
        
        # Network Diagnostics
        gateway_status = "✅ Reachable" if network_status.get('gateway_reachable') else "❌ Unreachable"
        gateway_class = "success" if network_status.get('gateway_reachable') else "error"
        internet_status = "✅ Connected" if network_status.get('internet_reachable') else "❌ No Connection"
        internet_class = "success" if network_status.get('internet_reachable') else "error"
        dns_status = "✅ Working" if network_status.get('dns_working') else "❌ Failed"
        dns_class = "success" if network_status.get('dns_working') else "error"
        
        html_content += f"""
            <div class="section">
                <div class="section-header">🌐 Network Diagnostics</div>
                <div class="section-content">
                    <div class="metric-grid">
                        <div class="metric {gateway_class}">
                            <div class="label">Gateway</div>
                            <div class="value status-{'good' if network_status.get('gateway_reachable') else 'error'}">{gateway_status}</div>
                        </div>
                        <div class="metric {internet_class}">
                            <div class="label">Internet</div>
                            <div class="value status-{'good' if network_status.get('internet_reachable') else 'error'}">{internet_status}</div>
                        </div>
                        <div class="metric {dns_class}">
                            <div class="label">DNS</div>
                            <div class="value status-{'good' if network_status.get('dns_working') else 'error'}">{dns_status}</div>
                        </div>
                    </div>
                    <pre>=== Network Interfaces ===
{network_status.get('interfaces', 'N/A')}

=== Routing Table ===
{network_status.get('routes', 'N/A')}

=== Network Statistics ===
{network_status.get('stats', 'N/A')}</pre>
                </div>
            </div>"""
        
        # Storage & USB Section
        html_content += f"""
            <div class="section">
                <div class="section-header">💾 Storage & USB</div>
                <div class="section-content">
                    <pre>=== Disk Usage ===
{storage_info.get('disk_usage', 'N/A')}

=== External Storage ===
{storage_info.get('block_devices', 'N/A')}

=== USB Devices ===
{storage_info.get('usb_devices', 'N/A')}

=== Mount Points ===
{storage_info.get('mounts', 'N/A')}</pre>
                </div>
            </div>"""
        
        # System Logs Section
        html_content += f"""
            <div class="section">
                <div class="section-header collapsible" onclick="toggleSection('logs')">📋 System Logs (Click to toggle)</div>
                <div class="section-content" id="logs" style="display: none;">
                    <pre>=== Recent Critical Events ===
{logs.get('critical_events', 'No critical events')}

=== Network Events ===
{logs.get('network_events', 'No network events')}

=== Power/Thermal Events ===
{logs.get('power_events', 'No power/thermal events')}</pre>
                </div>
            </div>"""
        
        # Recommendations Section
        html_content += """
            <div class="section">
                <div class="section-header">💡 Recommendations</div>
                <div class="section-content">
                    <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">
                        <h4>Hardware-Specific Recommendations:</h4>
                        <ul>"""
        
        if "Pi 5" in self.hardware_info['model']:
            html_content += "<li><strong>Pi 5 Power:</strong> Ensure you have the official 27W USB-C power supply</li>"
            if self.hardware_info['has_ai_hat']:
                html_content += "<li><strong>AI HAT Power:</strong> AI HAT increases power requirements - monitor for under-voltage warnings</li>"
        
        if self.hardware_info['has_ai_hat']:
            html_content += "<li><strong>AI HAT Cooling:</strong> Neural processing generates heat - ensure adequate cooling</li>"
            html_content += "<li><strong>AI HAT Performance:</strong> Monitor I2C communication and GPIO usage</li>"
        
        if self.hardware_info['has_wifi'] and self.hardware_info['has_ethernet']:
            html_content += "<li><strong>Dual Network:</strong> Consider disabling WiFi if using Ethernet to avoid routing conflicts</li>"
        
        if self.hardware_info['has_cooling']:
            html_content += "<li><strong>Active Cooling:</strong> Monitor fan operation and clean dust regularly</li>"
        
        html_content += """
                        </ul>
                    </div>
                </div>
            </div>"""
        
        # Footer
        html_content += f"""
            <div class="timestamp">
                Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                Auto-refresh available via refresh button
            </div>
        </div>
    </div>
</body>
</html>"""
        
        return html_content


class DiagnosticsHTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, diagnostics_instance, *args, **kwargs):
        self.diagnostics = diagnostics_instance
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            
            # Generate fresh report
            html_content = self.diagnostics.generate_html_report()
            self.wfile.write(html_content.encode('utf-8'))
            
        elif self.path == '/refresh':
            # Redirect to main page to trigger refresh
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            
        elif self.path == '/api/status':
            # JSON API endpoint for programmatic access
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status_data = {
                'hardware': self.diagnostics.hardware_info,
                'system': self.diagnostics.get_system_status(),
                'network': self.diagnostics.get_network_status(),
                'power': self.diagnostics.get_power_status(),
                'timestamp': datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(status_data, indent=2).encode('utf-8'))
            
        else:
            self.send_error(404, "File not found")
    
    def log_message(self, format, *args):
        # Suppress default HTTP logging for cleaner output
        pass


def create_server(port, diagnostics):
    def handler(*args, **kwargs):
        DiagnosticsHTTPHandler(diagnostics, *args, **kwargs)
    
    return HTTPServer(("", port), handler)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    
    print("🚀 Starting Raspberry Pi Diagnostics Server...")
    print("🔍 Detecting hardware configuration...")
    
    # Initialize diagnostics
    diagnostics = RPiDiagnostics()
    
    print(f"✅ Hardware detected:")
    print(f"   Model: {diagnostics.hardware_info['model']}")
    print(f"   Memory: {diagnostics.hardware_info['memory']}")
    print(f"   WiFi: {'Yes' if diagnostics.hardware_info['has_wifi'] else 'No'}")
    print(f"   Ethernet: {'Yes' if diagnostics.hardware_info['has_ethernet'] else 'No'}")
    print(f"   AI HAT: {'Yes' if diagnostics.hardware_info['has_ai_hat'] else 'No'}")
    print(f"   Cooling: {'Yes' if diagnostics.hardware_info['has_cooling'] else 'No'}")
    
    # Create and start server
    def signal_handler(sig, frame):
        print(f"\n🛑 Shutting down server...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server = create_server(port, diagnostics)
    
    print(f"\n🌐 Raspberry Pi Diagnostics Server")
    print(f"📊 Web Interface: http://localhost:{port}")
    print(f"🔄 Auto-refresh: http://localhost:{port}/refresh")
    print(f"📡 JSON API: http://localhost:{port}/api/status")
    print(f"⏹️  Press Ctrl+C to stop")
    print("-" * 50)
    
    # Get local IP addresses for remote access
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"🌍 Remote access: http://{local_ip}:{port}")
        
        # Try to get all network interfaces
        ip_output = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if ip_output.returncode == 0:
            ips = ip_output.stdout.strip().split()
            if len(ips) > 1:
                print(f"🔗 Additional IPs: {', '.join([f'http://{ip}:{port}' for ip in ips if ip != local_ip])}")
    except:
        pass
    
    print("-" * 50)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print(f"\n👋 Server stopped")


if __name__ == "__main__":
    # Check if running as root for certain operations
    if os.geteuid() != 0:
        print("⚠️  Some diagnostics require root privileges.")
        print("🔄 Run with sudo for complete hardware analysis.")
        print("💡 Continuing with limited diagnostics...")
        print()
    
    main()