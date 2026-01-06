#!/bin/bash

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Deploying Item Microservice System${NC}"
echo "========================================"

# Set your Docker Hub username here
REGISTRY="salon64"  # CHANGE THIS!

if [ "$REGISTRY" = "your-dockerhub-username" ]; then
    echo -e "${RED}❌ Please update REGISTRY in this script with your Docker Hub username!${NC}"
    exit 1
fi

# Step 1: Build images
echo -e "${BLUE}🔨 Building Docker images...${NC}"
cd item_service
docker build -t $REGISTRY/item-service:v1.0.0 .
cd ..

cd worker_service
docker build -t $REGISTRY/worker-service:v1.0.0 .
cd ..

# Step 2: Push images
echo -e "${BLUE}⬆️ Pushing images to registry...${NC}"
docker push $REGISTRY/item-service:v1.0.0
docker push $REGISTRY/worker-service:v1.0.0

# Step 3: Update deployment files
echo -e "${BLUE}📝 Updating deployment files...${NC}"
sed -i.bak "s|your-registry|$REGISTRY|g" item_service/k8s/deployment.yaml
sed -i.bak "s|your-registry|$REGISTRY|g" worker_service/k8s/deployment.yaml

# Step 4: Deploy namespace
echo -e "${BLUE}📦 Creating namespace...${NC}"
kubectl apply -f infrastructure/namespace.yaml

# Step 5: Deploy RabbitMQ (UPDATED SECTION)
echo -e "${BLUE}🐰 Deploying RabbitMQ...${NC}"

# First, create the modified StatefulSet with emptyDir
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: rabbitmq-config
  namespace: item-system
data:
  enabled_plugins: |
    [rabbitmq_management,rabbitmq_prometheus].
  rabbitmq.conf: |
    loopback_users.guest = false
    listeners.tcp.default = 5672
    management.tcp.port = 15672
    management.tcp.ip = 0.0.0.0
    prometheus.tcp.port = 15692
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: rabbitmq
  namespace: item-system
  labels:
    app: rabbitmq
spec:
  serviceName: rabbitmq-service
  replicas: 1
  selector:
    matchLabels:
      app: rabbitmq
  template:
    metadata:
      labels:
        app: rabbitmq
    spec:
      containers:
      - name: rabbitmq
        image: rabbitmq:3.12-management
        ports:
        - containerPort: 5672
          name: amqp
        - containerPort: 15672
          name: management
        - containerPort: 15692
          name: prometheus
        env:
        - name: RABBITMQ_DEFAULT_USER
          value: "guest"
        - name: RABBITMQ_DEFAULT_PASS
          value: "guest"
        volumeMounts:
        - name: rabbitmq-data
          mountPath: /var/lib/rabbitmq
        - name: rabbitmq-config
          mountPath: /etc/rabbitmq/enabled_plugins
          subPath: enabled_plugins
        - name: rabbitmq-config
          mountPath: /etc/rabbitmq/rabbitmq.conf
          subPath: rabbitmq.conf
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - rabbitmq-diagnostics
            - ping
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          exec:
            command:
            - rabbitmq-diagnostics
            - check_port_connectivity
          initialDelaySeconds: 20
          periodSeconds: 10
          timeoutSeconds: 5
      volumes:
      - name: rabbitmq-config
        configMap:
          name: rabbitmq-config
      - name: rabbitmq-data
        emptyDir: {}
EOF

# Apply RabbitMQ service
kubectl apply -f infrastructure/rabbitmq/service.yaml

echo "⏳ Waiting for RabbitMQ to be ready (this may take 2-3 minutes)..."
kubectl wait --for=condition=ready pod -l app=rabbitmq -n item-system --timeout=300s || {
    echo -e "${RED}❌ RabbitMQ failed to start. Checking status...${NC}"
    kubectl get pods -n item-system
    kubectl describe pod rabbitmq-0 -n item-system
    kubectl logs rabbitmq-0 -n item-system --tail=50
    exit 1
}

# Step 6: Deploy Monitoring
echo -e "${BLUE}📊 Deploying Prometheus...${NC}"
kubectl apply -f infrastructure/monitoring/prometheus/

echo -e "${BLUE}📈 Deploying Grafana...${NC}"
kubectl apply -f infrastructure/monitoring/grafana/

# Step 7: Deploy Services
echo -e "${BLUE}🔧 Deploying Item Service...${NC}"
kubectl apply -f item_service/k8s/

echo -e "${BLUE}⚙️ Deploying Worker Service...${NC}"
kubectl apply -f worker_service/k8s/

# Step 8: Wait for services
echo "⏳ Waiting for services to be ready..."
kubectl wait --for=condition=available deployment/item-service -n item-system --timeout=300s
kubectl wait --for=condition=available deployment/worker-service -n item-system --timeout=300s

# Step 9: Show status
echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo ""
echo "📊 Current Status:"
kubectl get pods -n item-system

echo ""
echo "📋 Access Information:"
echo "====================="
echo "To access services, use port-forwarding:"
echo ""
echo "Item Service:"
echo "  kubectl port-forward -n item-system svc/item-service-nodeport 8000:8000"
echo "  Then access: http://localhost:8000"
echo ""
echo "RabbitMQ Management:"
echo "  kubectl port-forward -n item-system svc/rabbitmq-management 15672:15672"
echo "  Then access: http://localhost:15672 (guest/guest)"
echo ""
echo "Prometheus:"
echo "  kubectl port-forward -n item-system svc/prometheus 9090:9090"
echo "  Then access: http://localhost:9090"
echo ""
echo "Grafana:"
echo "  kubectl port-forward -n item-system svc/grafana 3000:3000"
echo "  Then access: http://localhost:3000 (admin/admin)"
echo ""
echo "Worker Logs:"
echo "  kubectl logs -f deployment/worker-service -n item-system"