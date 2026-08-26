#!/bin/bash
curl -L https://github.com/m-javani/roomzin-quickstart/releases/download/latest/roomzin-quickstart.tar.gz | tar -xz

cd roomzin-quickstart

echo "📥 Downloading latest binaries..."
make download

echo "🏗️  Building Docker images..."
make build-images

echo "✅ Ready. cd roomzin-quickstart. Read the quick-start.txt. "