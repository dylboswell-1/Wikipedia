# Ollama Backend API

A production-ready Python FastAPI application that exposes Ollama LLM models via HTTP APIs. Designed to run on NVIDIA Kubernetes clusters with GPU support, auto-scaling, and high availability.

## Features

✅ **FastAPI Backend**: Modern Python async HTTP API
✅ **Ollama Integration**: Proxy endpoints for inference
✅ **Streaming Support**: Server-sent events for real-time responses
✅ **GPU Optimized**: Docker image with NVIDIA CUDA support
✅ **Kubernetes Ready**: Complete K8s manifests with GPU support
✅ **Auto-scaling**: Horizontal Pod Autoscaler (HPA) included
✅ **Health Checks**: Liveness & readiness probes
✅ **Security**: Non-root user, resource limits, read-only filesystem
✅ **Production Ready**: Multi-worker setup with Uvicorn

## Project Structure

```
├── src/
│   └── main.py                 # FastAPI application
├── k8s/
│   ├── namespace-config.yaml   # Namespace and ConfigMap
│   ├── ollama-deployment.yaml  # Ollama server deployment
│   ├── backend-deployment.yaml # Backend API deployment + HPA
│   ├── ingress.yaml            # Ingress for external access
│   └── persistent-volume.yaml  # PersistentVolumeClaim for models
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Local testing setup
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## API Endpoints

### Health & Status
- `GET /health` - Health check endpoint (Kubernetes liveness probe)
- `GET /ready` - Readiness check endpoint (Kubernetes readiness probe)
- `GET /` - API root information

### Model Management
- `GET /api/models` - List all available models
- `POST /api/pull` - Pull a model from registry

### Inference
- `POST /api/generate` - Generate text from prompt
- `POST /api/chat` - Chat with multi-turn conversation support

## Quick Start

### Local Development with Docker Compose

1. **Clone and navigate to project:**
   ```bash
   cd /Users/kalyan/Desktop/API-Test
   ```

2. **Start services:**
   ```bash
   docker-compose up -d
   ```

3. **Wait for Ollama to start (takes a moment):**
   ```bash
   docker-compose logs -f ollama
   ```

4. **Pull a model:**
   ```bash
   curl -X POST http://localhost:8000/api/pull \
     -H "Content-Type: application/json" \
     -d '{"model": "llama2"}'
   ```

5. **Access API:**
   - API docs: http://localhost:8000/docs
   - Backend health: http://localhost:8000/health

### Stop Services
```bash
docker-compose down
```

## Docker Build & Push

### Build locally
```bash
docker build -t ollama-backend:latest .
```

### Push to registry (adjust registry URL)
```bash
docker tag ollama-backend:latest your-registry/ollama-backend:latest
docker push your-registry/ollama-backend:latest
```

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster 1.20+
- NVIDIA GPU support (nvidia.com/gpu)
- kubectl configured
- Container image available in registry or locally

### Step 1: Create Namespace & ConfigMap
```bash
kubectl apply -f k8s/namespace-config.yaml
```

### Step 2: Deploy Ollama Server
```bash
kubectl apply -f k8s/ollama-deployment.yaml
```

### Step 3: Deploy Backend API
```bash
kubectl apply -f k8s/backend-deployment.yaml
```

### Step 4: (Optional) Apply Ingress
```bash
# Update the hostname in ingress.yaml first
kubectl apply -f k8s/ingress.yaml
```

### Step 5: (Optional) Enable Persistent Storage
```bash
# First create the PVC
kubectl apply -f k8s/persistent-volume.yaml

# Then update ollama-deployment.yaml to use it and redeploy
kubectl apply -f k8s/ollama-deployment.yaml
```

### Verify Deployment
```bash
# Check pods
kubectl get pods -n ollama-backend

# Check services
kubectl get svc -n ollama-backend

# Check logs
kubectl logs -n ollama-backend deployment/ollama-backend
```

### Port Forward for Testing
```bash
kubectl port-forward -n ollama-backend svc/ollama-backend 8000:80
```

Then access API at http://localhost:8000/docs

## Usage Examples

### Generate Text
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "Why is Kubernetes useful?",
    "stream": false
  }'
```

### Stream Generation
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "Write a poem about containers",
    "stream": true
  }'
```

### Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [
      {"role": "user", "content": "Hello!"},
      {"role": "assistant", "content": "Hi there! How can I help?"},
      {"role": "user", "content": "What is Docker?"}
    ],
    "stream": false
  }'
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT` | `300` | Request timeout in seconds |
| `ENVIRONMENT` | `production` | Environment (development/production) |

### For Docker Compose
Edit `docker-compose.yml` environment sections

### For Kubernetes
Edit `k8s/namespace-config.yaml` ConfigMap

## Troubleshooting

### Ollama not reachable
```bash
# Check if Ollama pod is running
kubectl get pods -n ollama-backend -l app=ollama

# Check logs
kubectl logs -n ollama-backend -l app=ollama

# Port forward to test directly
kubectl port-forward -n ollama-backend svc/ollama 11434:11434
curl http://localhost:11434/api/tags
```

### Backend pods crashing
```bash
# Check pod logs
kubectl logs -n ollama-backend -l app=ollama-backend

# Check events
kubectl describe pod -n ollama-backend <pod-name>

# Check resource requests
kubectl top pods -n ollama-backend
```

### Models not loading
- Ensure model is pulled: `curl http://backend/api/models`
- Check Ollama logs: `kubectl logs -n ollama-backend -l app=ollama`
- Verify storage is available if using PVC

### High latency
- Check GPU availability on nodes
- Verify model is cached (not downloading)
- Monitor resource usage: `kubectl top pods -n ollama-backend`
- Check network between pods: `kubectl exec -n ollama-backend <pod> -- ping ollama`

## Scaling

### Manual scaling
```bash
# Scale backend replicas
kubectl scale deployment -n ollama-backend ollama-backend --replicas=5
```

### Auto-scaling
HPA is configured to scale 3-10 replicas based on CPU/memory. Monitor with:
```bash
kubectl get hpa -n ollama-backend -w
```

## Production Considerations

1. **Persistent Storage**: Uncomment PVC in `ollama-deployment.yaml` to persist models
2. **GPU Allocation**: Adjust GPU requests in `ollama-deployment.yaml`
3. **Ingress**: Update hostname and TLS settings in `ingress.yaml`
4. **Resource Limits**: Adjust CPU/memory in `backend-deployment.yaml`
5. **Registry**: Update image pull policy and registry in manifests
6. **Monitoring**: Add Prometheus scraping for metrics
7. **Logging**: Consider centralized logging (ELK, Loki, etc.)

## Security

- Backend runs as non-root user (UID 1000)
- Read-only root filesystem
- Resource limits prevent DoS
- Capabilities dropped for defense in depth

## Building & Testing

### Local testing
```bash
docker-compose up -d
# Wait for services
docker-compose logs -f backend
```

### Run tests (when added)
```bash
pytest tests/
```

## License

MIT

## Support

For issues or questions, check logs and verify:
1. Ollama service is running and responsive
2. Models are pulled and cached
3. Network connectivity between pods
4. GPU availability on nodes
