#!/usr/bin/env python3
"""
Simple AI HAT Monitor for Project Cortez
Monitors your AI HAT temperature and utilization
"""

import time
import subprocess
import re
import logging
from prometheus_client import start_http_server, Gauge

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleAIHatMonitor:
    def __init__(self):
        # Prometheus metrics
        self.ai_hat_temp = Gauge('ai_hat_temperature_celsius', 'AI HAT temperature')
        self.cpu_temp = Gauge('cpu_temperature_celsius', 'CPU temperature') 
        self.ai_hat_detected = Gauge('ai_hat_detected', 'AI HAT detection status')
        
    def get_cpu_temperature(self):
        """Get Raspberry Pi CPU temperature"""
        try:
            result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                temp_match = re.search(r'temp=(\d+\.?\d*)\'C', result.stdout)
                if temp_match:
                    return float(temp_match.group(1))
        except Exception as e:
            logger.warning(f"Could not read CPU temperature: {e}")
        return None
    
    def detect_ai_hat(self):
        """Simple AI HAT detection"""
        try:
            # Check for common AI HAT indicators
            result = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=5)
            ai_keywords = ['hailo', 'coral', 'tpu', 'npu', 'ai']
            
            for keyword in ai_keywords:
                if keyword in result.stdout.lower():
                    logger.info(f"AI HAT detected: {keyword}")
                    return True
                    
            # Check for AI devices
            result = subprocess.run(['ls', '/dev/'], capture_output=True, text=True, timeout=5)
            if 'apex' in result.stdout or 'dri' in result.stdout:
                logger.info("AI HAT device detected")
                return True
                
        except Exception as e:
            logger.warning(f"AI HAT detection failed: {e}")
        
        logger.info("No AI HAT detected")
        return False
    
    def collect_metrics(self):
        """Collect and update metrics"""
        try:
            # CPU temperature (use as AI HAT temp if no specific sensor)
            cpu_temp = self.get_cpu_temperature()
            if cpu_temp:
                self.cpu_temp.set(cpu_temp)
                self.ai_hat_temp.set(cpu_temp)  # Use CPU temp as proxy
                logger.debug(f"Temperature: {cpu_temp}°C")
            
            # AI HAT detection
            ai_hat_present = self.detect_ai_hat()
            self.ai_hat_detected.set(1 if ai_hat_present else 0)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    def run(self):
        """Start the monitor"""
        logger.info("Starting Simple AI HAT Monitor on port 9102")
        
        # Start Prometheus server
        start_http_server(9102)
        logger.info("Metrics available at http://localhost:9102/metrics")
        
        while True:
            try:
                self.collect_metrics()
                time.sleep(30)  # Update every 30 seconds
            except KeyboardInterrupt:
                logger.info("Shutting down")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)

if __name__ == '__main__':
    monitor = SimpleAIHatMonitor()
    monitor.run()
