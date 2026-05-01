#!/bin/bash

# Deploy Ollama Backend to Kubernetes
# Usage: ./deploy.sh [apply|delete]

set -e

NAMESPACE="ollama-backend"
ACTION="${1:-apply}"

if [ "$ACTION" != "apply" ] && [ "$ACTION" != "delete" ]; then
  echo "Usage: $0 [apply|delete]"
  exit 1
fi

echo "📦 Ollama Backend Kubernetes Deployment"
echo "Action: $ACTION"
echo "Namespace: $NAMESPACE"
echo ""

if [ "$ACTION" = "apply" ]; then
  echo "✅ Creating namespace and config..."
  kubectl apply -f k8s/namespace-config.yaml
  
  echo "✅ Deploying Ollama server..."
  kubectl apply -f k8s/ollama-deployment.yaml
  
  echo "✅ Deploying backend API..."
  kubectl apply -f k8s/backend-deployment.yaml
  
  echo "✅ (Optional) Applying ingress..."
  kubectl apply -f k8s/ingress.yaml || echo "⚠️  Ingress failed (may need cert-manager setup)"
  
  echo ""
  echo "🚀 Deployment complete!"
  echo ""
  echo "Waiting for rollout..."
  kubectl rollout status -n $NAMESPACE deployment/ollama --timeout=5m || true
  kubectl rollout status -n $NAMESPACE deployment/ollama-backend --timeout=5m || true
  
  echo ""
  echo "📊 Status:"
  kubectl get pods -n $NAMESPACE
  echo ""
  echo "🔗 Services:"
  kubectl get svc -n $NAMESPACE
  
elif [ "$ACTION" = "delete" ]; then
  echo "🗑️  Deleting deployment..."
  kubectl delete -f k8s/ingress.yaml || true
  kubectl delete -f k8s/backend-deployment.yaml || true
  kubectl delete -f k8s/ollama-deployment.yaml || true
  kubectl delete -f k8s/namespace-config.yaml || true
  
  echo "✅ Deleted!"
fi
