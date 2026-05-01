# Quick Start Guide

## 
A production-ready **Ollama Backend API** on NVIDIA Kubernetes clusters with:
-  FastAPI server with async HTTP proxy for Ollama
-  Multi-stage Docker build (NVIDIA/CUDA optimized)
-  Complete Kubernetes manifests (deployment, service, HPA)
-  Docker Compose for local testing
-  Comprehensive documentation and troubleshooting

## 
### Option 1: Local Development (Fastest)

```bash
cd /Users/kalyan/Desktop/API-Test

# Start services
./dev.sh start

# Wait a moment, then test
./test.sh

# Access at http://localhost:8000/docs
```

**Common commands:**
```bash
./dev.sh logs-ollama       # View Ollama logs
./dev.sh logs-backend      # View API logs
./dev.sh restart           # Restart services
./dev.sh stop              # Stop services
./dev.sh clean             # Remove everything
```

### Option 2: Kubernetes on NVIDIA Cluster

```bash
cd /Users/kalyan/Desktop/API-Test

# Build and push image to your registry
docker build -t your-registry/ollama-backend:1.0 .
docker push your-registry/ollama-backend:1.0

# Update image reference in k8s/backend-deployment.yaml
# Then deploy:
./deploy.sh apply

# Monitor deployment
kubectl get pods -n ollama-backend -w

# Port forward for testing
kubectl port-forward -n ollama-backend svc/ollama-backend 8000:80
```

### Option 3: Manual Docker

```bash
# Build
docker build -t ollama-backend:latest .

# Run with docker run
docker run -p 8000:8000 \
  -e OLLAMA_HOST=http://ollama-container:11434 \
  ollama-backend:latest
```

## 
```
 src/main.py                 # FastAPI app
 Dockerfile                  # Docker image (NVIDIA/CUDA)
 docker-compose.yml          # Local dev setup
 requirements.txt            # Python deps
 k8s/                        # Kubernetes manifests
 namespace-config.yaml   
 ollama-deployment.yaml   
 backend-deployment.yaml   
 ingress.yaml   
 persistent-volume.yaml   
 README.md                   # Full documentation
 KUBERNETES.md               # K8s deployment guide
 QUICKSTART.md              # This file
 dev.sh                      # Dev helper commands
 deploy.sh                   # K8s deployment script
 test.sh                     # API test suite
```

## 
```bash
# Health checks
GET /health
GET /ready

# Models
GET /api/models
POST /api/pull

# Inference
POST /api/generate
POST /api/chat

# Documentation
GET /docs          # Swagger UI
GET /redoc         # ReDoc
```

## 
```bash
# Against local service
./test.sh

# Against Kubernetes
./test.sh http://<your-k8s-service>:8000

# Against specific URL
./test.sh http://localhost:8000
```

## 
```bash
# List models
curl http://localhost:8000/api/models

# Pull llama2 (large, takes time)
curl -X POST http://localhost:8000/api/pull \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2"}'
```

## 
Environment variables:

| Variable | Default | Use |
|----------|---------|-----|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT` | `300` | Request timeout (sec) |
| `ENVIRONMENT` | `production` | production or development |

Edit `.env` or docker-compose.yml environment sections.

## 
- **README.md** - Complete API reference & features
- **KUBERNETES.md** - NVIDIA cluster deployment (GPU, ingress, HPA, etc.)
- **API Docs** - Interactive at http://localhost:8000/docs

## 
### Ollama not reachable
```bash
# Check Ollama pod is running
kubectl get pods -n ollama-backend -l app=ollama

# Test connectivity
kubectl exec -n ollama-backend <backend-pod> -- \
  curl http://ollama:11434/api/tags
```

### Backend pod crashing
```bash
# View logs
kubectl logs -n ollama-backend -l app=ollama-backend

# Check resources
kubectl describe pod -n ollama-backend <pod-name>
```

### Models not available
```bash
# Verify models are pulled
curl http://localhost:8000/api/models
```

##  Production Checklist

- [ ] Build and push image to your registry
- [ ] Configure persistent storage (if needed)
- [ ] Set GPU node affinity
- [ ] Configure Ingress with TLS
- [ ] Adjust resource requests/limits
- [ ] Set up monitoring & logging
- [ ] Test failover & recovery
- [ ] Document cluster-specific setup

## 
1. **Local Testing**: Run `./dev.sh start` to test locally
2. **Deploy to Cluster**: Follow KUBERNETES.md for your NVIDIA cluster
3. **Load Models**: Pull models via `/api/pull` endpoint
4. **Integrate**: Use API from your applications

## 
- Check README.md for feature details
- Check KUBERNETES.md for GPU/cluster issues
- Run ./test.sh to validate setup
- Check logs: `./dev.sh logs` or `kubectl logs -n ollama-backend`

---

**Ready to go!** 
Start with: `./dev.sh start`
