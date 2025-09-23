#!/bin/bash
# =============================================================================
# RPiCortex AI Engine Setup Script
# =============================================================================
# Enterprise-grade AI/ML environment for Raspberry Pi 5 with 16GB RAM
# Designed for cybersecurity professional with cloud architecture background
# =============================================================================

set -e

echo "🤖 RPiCortex AI Engine Initialization"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# System info
echo -e "${BLUE}📊 System Information:${NC}"
echo "Hostname: $(hostname)"
echo "Memory: $(free -h | grep '^Mem:' | awk '{print $2}')"
echo "CPU: $(nproc) cores"
echo "Architecture: $(uname -m)"
echo ""

# Update system
echo -e "${YELLOW}🔄 Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install essential development tools
echo -e "${YELLOW}🛠️ Installing development essentials...${NC}"
sudo apt install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    unzip \
    htop \
    iotop \
    stress-ng \
    python3-dev \
    python3-pip \
    python3-venv \
    libopenblas-dev \
    libhdf5-dev \
    libssl-dev \
    pkg-config \
    libffi-dev

# Install Docker (if not already installed)
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo -e "${GREEN}✅ Docker already installed${NC}"
fi

# Create AI workspace
echo -e "${BLUE}📁 Setting up AI workspace...${NC}"
mkdir -p ~/rpicortex/{models,datasets,experiments,notebooks,scripts}
cd ~/rpicortex

# Create Python virtual environment for AI
echo -e "${PURPLE}🐍 Setting up Python AI environment...${NC}"
python3 -m venv ai-env
source ai-env/bin/activate

# Install core AI/ML libraries optimized for ARM64
echo -e "${PURPLE}📦 Installing AI/ML packages...${NC}"
pip install --upgrade pip

# PyTorch for ARM64 (optimized for Apple Silicon/ARM)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Core ML libraries
pip install \
    numpy \
    pandas \
    scikit-learn \
    matplotlib \
    seaborn \
    jupyter \
    jupyterlab \
    transformers \
    datasets \
    tokenizers \
    accelerate \
    bitsandbytes \
    peft \
    trl

# Computer Vision & NLP
pip install \
    opencv-python \
    pillow \
    nltk \
    spacy \
    sentence-transformers

# Monitoring and MLOps
pip install \
    wandb \
    mlflow \
    prometheus-client \
    psutil

# LLM inference engines
pip install \
    llama-cpp-python \
    ctransformers \
    gguf

# Create systemd service for Jupyter Lab
echo -e "${BLUE}🔧 Setting up Jupyter Lab service...${NC}"
sudo tee /etc/systemd/system/rpicortex-jupyter.service > /dev/null <<EOF
[Unit]
Description=RPiCortex Jupyter Lab
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/rpicortex
Environment=PATH=/home/$USER/rpicortex/ai-env/bin
ExecStart=/home/$USER/rpicortex/ai-env/bin/jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Create AI model monitoring exporter
echo -e "${BLUE}🔍 Setting up AI metrics exporter...${NC}"
cat > ~/rpicortex/scripts/ai_metrics_exporter.py << 'EOF'
#!/usr/bin/env python3
"""
RPiCortex AI Metrics Exporter for Prometheus
Monitors AI workloads, model inference, and system resources
"""

import time
import psutil
import json
import subprocess
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import threading
import os

class RPiCortexExporter:
    def __init__(self, port=9103):
        self.port = port
        
        # System metrics
        self.cpu_temp = Gauge('rpicortex_cpu_temperature_celsius', 'CPU temperature')
        self.cpu_usage = Gauge('rpicortex_cpu_usage_percent', 'CPU usage percentage')
        self.memory_usage = Gauge('rpicortex_memory_usage_bytes', 'Memory usage in bytes')
        self.memory_total = Gauge('rpicortex_memory_total_bytes', 'Total memory in bytes')
        
        # AI-specific metrics
        self.ai_inference_duration = Histogram('rpicortex_inference_duration_seconds', 'Model inference time')
        self.ai_model_load_time = Histogram('rpicortex_model_load_duration_seconds', 'Model loading time')
        self.ai_active_models = Gauge('rpicortex_active_models', 'Number of loaded models')
        self.ai_gpu_memory = Gauge('rpicortex_gpu_memory_usage_bytes', 'GPU memory usage')
        
        # Process metrics
        self.ai_processes = Gauge('rpicortex_ai_processes', 'Number of AI processes')
        self.jupyter_sessions = Gauge('rpicortex_jupyter_sessions', 'Active Jupyter sessions')
        
    def get_cpu_temperature(self):
        """Get CPU temperature from thermal zone"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read().strip()) / 1000.0
                return temp
        except:
            return 0
    
    def count_ai_processes(self):
        """Count running AI/ML processes"""
        ai_keywords = ['python', 'jupyter', 'torch', 'tensorflow', 'model', 'inference']
        count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                if any(keyword in cmdline for keyword in ai_keywords):
                    count += 1
            except:
                continue
        return count
    
    def update_metrics(self):
        """Update all metrics"""
        while True:
            try:
                # System metrics
                self.cpu_temp.set(self.get_cpu_temperature())
                self.cpu_usage.set(psutil.cpu_percent())
                
                memory = psutil.virtual_memory()
                self.memory_usage.set(memory.used)
                self.memory_total.set(memory.total)
                
                # AI process metrics
                self.ai_processes.set(self.count_ai_processes())
                
                # Mock Jupyter sessions (would need actual Jupyter API)
                self.jupyter_sessions.set(1)  # Placeholder
                
                time.sleep(15)  # Update every 15 seconds
                
            except Exception as e:
                print(f"Error updating metrics: {e}")
                time.sleep(15)
    
    def run(self):
        """Start the metrics server"""
        start_http_server(self.port)
        print(f"🤖 RPiCortex AI Metrics Exporter running on port {self.port}")
        
        # Start metrics collection in background
        metrics_thread = threading.Thread(target=self.update_metrics)
        metrics_thread.daemon = True
        metrics_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")

if __name__ == "__main__":
    exporter = RPiCortexExporter()
    exporter.run()
EOF

# Make exporter executable
chmod +x ~/rpicortex/scripts/ai_metrics_exporter.py

# Create systemd service for AI metrics exporter
sudo tee /etc/systemd/system/rpicortex-metrics.service > /dev/null <<EOF
[Unit]
Description=RPiCortex AI Metrics Exporter
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/rpicortex/scripts
Environment=PATH=/home/$USER/rpicortex/ai-env/bin
ExecStart=/home/$USER/rpicortex/ai-env/bin/python ai_metrics_exporter.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Create sample AI experiment script
echo -e "${PURPLE}🧪 Creating sample AI experiment...${NC}"
cat > ~/rpicortex/experiments/model_benchmark.py << 'EOF'
#!/usr/bin/env python3
"""
RPiCortex Model Benchmarking Suite
Tests inference performance of various models on Raspberry Pi 5
"""

import time
import torch
import numpy as np
import psutil
from transformers import pipeline
import json

class ModelBenchmark:
    def __init__(self):
        self.results = {}
        
    def benchmark_text_generation(self):
        """Benchmark small text generation model"""
        print("🔤 Testing text generation...")
        start_time = time.time()
        
        # Use a small model suitable for Pi
        generator = pipeline('text-generation', 
                           model='distilgpt2',
                           device=-1)  # CPU only
        
        load_time = time.time() - start_time
        
        # Run inference
        inference_start = time.time()
        result = generator("RPiCortex is", max_length=50, num_return_sequences=1)
        inference_time = time.time() - inference_start
        
        self.results['text_generation'] = {
            'model': 'distilgpt2',
            'load_time': load_time,
            'inference_time': inference_time,
            'output': result[0]['generated_text']
        }
        
    def benchmark_sentiment_analysis(self):
        """Benchmark sentiment analysis"""
        print("😊 Testing sentiment analysis...")
        start_time = time.time()
        
        classifier = pipeline('sentiment-analysis',
                             model='distilbert-base-uncased-finetuned-sst-2-english',
                             device=-1)
        
        load_time = time.time() - start_time
        
        inference_start = time.time()
        result = classifier("RPiCortex AI engine is working perfectly!")
        inference_time = time.time() - inference_start
        
        self.results['sentiment_analysis'] = {
            'model': 'distilbert-base-uncased-finetuned-sst-2-english',
            'load_time': load_time,
            'inference_time': inference_time,
            'output': result
        }
    
    def system_stats(self):
        """Capture system statistics during benchmark"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_used_gb': psutil.virtual_memory().used / (1024**3),
            'cpu_temp': self.get_cpu_temp()
        }
    
    def get_cpu_temp(self):
        """Get CPU temperature"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                return int(f.read().strip()) / 1000.0
        except:
            return 0
    
    def run_benchmarks(self):
        """Run all benchmarks"""
        print("🤖 Starting RPiCortex AI Benchmarks...")
        print("=" * 50)
        
        start_stats = self.system_stats()
        
        self.benchmark_text_generation()
        self.benchmark_sentiment_analysis()
        
        end_stats = self.system_stats()
        
        self.results['system_stats'] = {
            'start': start_stats,
            'end': end_stats
        }
        
        # Save results
        with open('/home/pi/rpicortex/experiments/benchmark_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print("\n📊 Benchmark Results:")
        print("=" * 50)
        for task, result in self.results.items():
            if task != 'system_stats':
                print(f"{task}:")
                print(f"  Load time: {result['load_time']:.2f}s")
                print(f"  Inference time: {result['inference_time']:.2f}s")
                print()

if __name__ == "__main__":
    benchmark = ModelBenchmark()
    benchmark.run_benchmarks()
EOF

# Enable and start services
echo -e "${GREEN}🚀 Starting services...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable rpicortex-jupyter
sudo systemctl enable rpicortex-metrics
sudo systemctl start rpicortex-jupyter
sudo systemctl start rpicortex-metrics

# Add to Prometheus config
echo -e "${BLUE}📊 Adding to Prometheus configuration...${NC}"
PROMETHEUS_CONFIG="/home/$USER/roundrock-home-stack/svc/monitoring/svc-prometheus/prometheus.yml"
if [ -f "$PROMETHEUS_CONFIG" ]; then
    echo "
  # RPiCortex AI Engine Metrics
  - job_name: 'rpicortex-ai'
    static_configs:
      - targets: ['localhost:9103']
    scrape_interval: 15s" >> "$PROMETHEUS_CONFIG"
    echo -e "${GREEN}✅ Added RPiCortex to Prometheus config${NC}"
else
    echo -e "${YELLOW}⚠️ Prometheus config not found at expected location${NC}"
fi

echo ""
echo -e "${GREEN}🎉 RPiCortex AI Engine Setup Complete!${NC}"
echo "=" * 50
echo -e "${BLUE}📊 Services:${NC}"
echo "  • Jupyter Lab: http://$(hostname -I | awk '{print $1}'):8888"
echo "  • AI Metrics: http://$(hostname -I | awk '{print $1}'):9103/metrics"
echo ""
echo -e "${BLUE}📁 Workspace: ~/rpicortex/${NC}"
echo "  • models/     - Store your AI models"
echo "  • datasets/   - Training and test data"
echo "  • experiments/ - AI experiments and benchmarks"
echo "  • notebooks/  - Jupyter notebooks"
echo "  • scripts/    - Utility scripts"
echo ""
echo -e "${PURPLE}🧪 Next Steps:${NC}"
echo "  1. Run: cd ~/rpicortex && source ai-env/bin/activate"
echo "  2. Test: python experiments/model_benchmark.py"
echo "  3. Access Jupyter Lab and start experimenting!"
echo ""
echo -e "${YELLOW}💡 Pro Tips:${NC}"
echo "  • Monitor temperature during intensive AI workloads"
echo "  • Use quantized models (4-bit/8-bit) for better performance"
echo "  • Consider external cooling for sustained AI workloads"