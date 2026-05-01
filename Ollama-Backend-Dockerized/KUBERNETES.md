# NVIDIA Kubernetes Cluster Deployment Guide

This guide covers deploying the Ollama Backend on an NVIDIA Kubernetes cluster with GPU support.

## Prerequisites

- Kubernetes cluster 1.20+ with NVIDIA GPUs
- `kubectl` configured and authenticated
- NVIDIA device plugin installed
- Docker registry access (or local image availability)
- Container runtime with GPU support (Docker, containerd)

## Step 1: Verify NVIDIA Setup on Cluster

### Check NVIDIA device plugin
```bash
kubectl get nodes -L accelerator
# or
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, gpu: .status.allocatable["nvidia.com/gpu"]}'
```

### Verify GPU availability
```bash
kubectl describe nodes | grep -A 5 "allocatable\|nvidia.com"
```

### Test GPU access
```bash
kubectl run gpu-test --image=nvidia/cuda:12.2.2-base-ubuntu22.04 \
  --rm -it --restart=Never \
  --limits=nvidia.com/gpu=1 \
  -- nvidia-smi
```

## Step 2: Build and Push Container Image

### Option A: Build on local machine and push to registry

```bash
# Build image
docker build -t ollama-backend:1.0 .

# Tag for registry (adjust registry URL)
docker tag ollama-backend:1.0 <your-registry>/ollama-backend:1.0

# Push to registry
docker push <your-registry>/ollama-backend:1.0
```

### Option B: Build directly on cluster using BuildKit

```bash
# Requires Kubernetes with BuildKit support
kubectl create configmap docker-daemon --from-file=/var/run/docker.sock
# (Not recommended, use docker push instead)
```

## Step 3: Update Kubernetes Manifests

### Edit image references
Update the image in `k8s/backend-deployment.yaml`:

```yaml
spec:
  containers:
  - name: backend
    image: <your-registry>/ollama-backend:1.0  # Update this
    imagePullPolicy: IfNotPresent              # or Always
```

### (Optional) Configure image pull secrets
If using private registry:

```bash
kubectl create secret docker-registry regcred \
  --docker-server=<your-registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n ollama-backend
```

Then add to deployment:
```yaml
spec:
  imagePullSecrets:
  - name: regcred
```

## Step 4: Deploy to Kubernetes

### Quick deployment
```bash
cd /path/to/ollama-backend
./deploy.sh apply
```

### Manual deployment
```bash
kubectl apply -f k8s/namespace-config.yaml
kubectl apply -f k8s/ollama-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/ingress.yaml  # Optional
```

### Verify deployment
```bash
kubectl get pods -n ollama-backend -w
```

Wait for all pods to be Running:
```bash
kubectl rollout status -n ollama-backend deployment/ollama -t 5m
kubectl rollout status -n ollama-backend deployment/ollama-backend -t 5m
```

## Step 5: Verify GPU Allocation

### Check GPU allocation
```bash
kubectl describe nodes | grep nvidia.com
```

### Verify pod using GPU
```bash
kubectl get pods -n ollama-backend -o wide
kubectl describe pod -n ollama-backend <ollama-pod-name> | grep -A 5 "Resources"
```

### Check NVIDIA GPU usage
```bash
kubectl exec -n ollama-backend <ollama-pod-name> -- nvidia-smi
```

## Step 6: Access the API

### Port forward for testing
```bash
kubectl port-forward -n ollama-backend svc/ollama-backend 8000:80 &
```

### Test API
```bash
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Swagger UI
```

### Run test suite
```bash
./test.sh http://localhost:8000
```

## Step 7: Pull Models into Ollama

```bash
# List available models
curl http://localhost:8000/api/models

# Pull a model (takes time)
curl -X POST http://localhost:8000/api/pull \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2"}'

# Monitor pull progress
kubectl logs -n ollama-backend -l app=ollama -f
```

## Advanced Configuration

### Enable Persistent Storage for Models

1. Create PVC (adjust storage class for your cluster):
```bash
kubectl apply -f k8s/persistent-volume.yaml
```

2. Update `ollama-deployment.yaml` to use PVC:
```yaml
volumes:
- name: ollama-data
  persistentVolumeClaim:
    claimName: ollama-pvc
```

3. Reapply deployment:
```bash
kubectl apply -f k8s/ollama-deployment.yaml
```

### Configure GPU Node Affinity

Edit `k8s/ollama-deployment.yaml` to target specific GPU nodes:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: accelerator
          operator: In
          values:
          - nvidia-gpu
```

Or use node labels:
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - gpu-node-01
```

### Adjust GPU and Resource Requests

Edit `k8s/ollama-deployment.yaml`:

```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "4"
    nvidia.com/gpu: "2"    # Request 2 GPUs
  limits:
    memory: "16Gi"
    cpu: "8"
    nvidia.com/gpu: "2"
```

### Enable Ingress with TLS

1. Install cert-manager (if not installed):
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

2. Update hostname in `k8s/ingress.yaml`:
```yaml
- host: ollama-api.yourdomain.com
```

3. Apply ingress:
```bash
kubectl apply -f k8s/ingress.yaml
```

## Monitoring and Troubleshooting

### View logs
```bash
# Ollama logs
kubectl logs -n ollama-backend -l app=ollama -f

# Backend logs
kubectl logs -n ollama-backend -l app=ollama-backend -f

# Specific pod
kubectl logs -n ollama-backend <pod-name> -c backend
```

### Describe pod for errors
```bash
kubectl describe pod -n ollama-backend <pod-name>
```

### Check resource usage
```bash
kubectl top pods -n ollama-backend
kubectl top nodes
```

### Check pod events
```bash
kubectl get events -n ollama-backend --sort-by='.lastTimestamp'
```

### Troubleshoot networking
```bash
# Test connectivity from backend pod to Ollama
kubectl exec -n ollama-backend <backend-pod> -- \
  curl -v http://ollama:11434/api/tags

# DNS resolution
kubectl exec -n ollama-backend <backend-pod> -- nslookup ollama
```

## Scaling and Performance

### Horizontal scaling (manual)
```bash
kubectl scale deployment -n ollama-backend ollama-backend --replicas=5
```

### Monitor HPA
```bash
kubectl get hpa -n ollama-backend -w
```

### Check autoscaling status
```bash
kubectl describe hpa -n ollama-backend ollama-backend-hpa
```

### Increase resource limits for HPA
Edit `k8s/backend-deployment.yaml` HPA section:
```yaml
maxReplicas: 20  # Increase max
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 60  # Lower threshold = more scaling
```

## Production Checklist

- [ ] Test GPU allocation on target nodes
- [ ] Configure persistent storage for models
- [ ] Set up private container registry
- [ ] Configure Ingress with TLS certificate
- [ ] Set resource requests/limits appropriately
- [ ] Configure monitoring (Prometheus, etc.)
- [ ] Set up centralized logging (ELK, Loki, etc.)
- [ ] Create backup strategy for model storage
- [ ] Test failover and recovery
- [ ] Document cluster-specific configurations
- [ ] Set up alerts for pod/service health

## Cleanup

### Delete entire deployment
```bash
./deploy.sh delete
```

### Manual cleanup
```bash
kubectl delete namespace ollama-backend
```

## Support

For NVIDIA-specific issues:
- Check NVIDIA device plugin status: `kubectl get daemonset -n kube-system`
- Review NVIDIA docs: https://github.com/NVIDIA/k8s-device-plugin
- Test GPU access with official CUDA image

For Ollama-specific issues:
- Check Ollama GitHub: https://github.com/ollama/ollama
- Review model availability: https://ollama.ai/library
