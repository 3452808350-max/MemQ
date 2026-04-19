#!/bin/bash
# Fix Ollama to listen on all interfaces

# Create override directory
sudo mkdir -p /etc/systemd/system/ollama.service.d

# Create override file
cat << 'EOF' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

# Reload systemd
sudo systemctl daemon-reload

# Restart Ollama
sudo systemctl restart ollama

# Wait a moment
sleep 2

# Check status
echo "=== Ollama Status ==="
sudo systemctl status ollama --no-pager

echo ""
echo "=== Listening Ports ==="
ss -tlnp | grep 11434

echo ""
echo "=== Test Local API ==="
curl -s http://localhost:11434/api/tags | head -20
