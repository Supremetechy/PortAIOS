# MiniKernel Deployment Examples

Complete examples for deploying MiniKernel in various scenarios.

## Table of Contents

1. [Local Development](#local-development)
2. [Cloud Deployments](#cloud-deployments)
3. [Container Orchestration](#container-orchestration)
4. [Edge Computing](#edge-computing)
5. [CI/CD Integration](#cicd-integration)
6. [Multi-Environment Setup](#multi-environment-setup)

---

## Local Development

### 1. Quick Local Test

**Docker Compose:**
```bash
cd minikernel/deploy/docker
docker-compose up
```

**Native:**
```bash
python3 minikernel/boot.py --mode text --log-level DEBUG
```

### 2. Development with Hot Reload

Create `docker-compose.dev.yml`:
```yaml
version: '3.8'
services:
  minikernel-dev:
    build:
      context: ../../..
      dockerfile: minikernel/deploy/docker/Dockerfile
    volumes:
      - ../../../minikernel:/opt/minikernel/minikernel:ro
    environment:
      - MINIKERNEL_MODE=text
      - MINIKERNEL_LOG_LEVEL=DEBUG
    command: ["--mode", "text", "--log-level", "DEBUG"]
```

Run:
```bash
docker-compose -f docker-compose.dev.yml up
```

---

## Cloud Deployments

### AWS

#### ECS (Elastic Container Service)

**Task Definition:**
```json
{
  "family": "minikernel",
  "containerDefinitions": [
    {
      "name": "minikernel",
      "image": "minikernel:latest",
      "memory": 2048,
      "cpu": 1024,
      "essential": true,
      "environment": [
        {"name": "MINIKERNEL_MODE", "value": "text"},
        {"name": "MINIKERNEL_LOG_LEVEL", "value": "INFO"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/minikernel",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "minikernel"
        }
      }
    }
  ]
}
```

Deploy:
```bash
aws ecs create-service \
  --cluster minikernel-cluster \
  --service-name minikernel \
  --task-definition minikernel \
  --desired-count 2
```

#### EKS (Elastic Kubernetes Service)

```bash
# Create EKS cluster
eksctl create cluster \
  --name minikernel-cluster \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3

# Install with Helm
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set persistence.data.storageClass=gp3 \
  --namespace minikernel \
  --create-namespace
```

### Azure

#### ACI (Azure Container Instances)

```bash
az container create \
  --resource-group minikernel-rg \
  --name minikernel \
  --image minikernel:latest \
  --cpu 2 \
  --memory 4 \
  --environment-variables \
    MINIKERNEL_MODE=text \
    MINIKERNEL_LOG_LEVEL=INFO \
  --restart-policy Always
```

#### AKS (Azure Kubernetes Service)

```bash
# Create AKS cluster
az aks create \
  --resource-group minikernel-rg \
  --name minikernel-cluster \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3 \
  --enable-managed-identity

# Get credentials
az aks get-credentials \
  --resource-group minikernel-rg \
  --name minikernel-cluster

# Install with Helm
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set persistence.data.storageClass=managed-premium \
  --namespace minikernel \
  --create-namespace
```

### Google Cloud

#### Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/minikernel

# Deploy
gcloud run deploy minikernel \
  --image gcr.io/PROJECT_ID/minikernel \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars MINIKERNEL_MODE=text,MINIKERNEL_LOG_LEVEL=INFO
```

#### GKE (Google Kubernetes Engine)

```bash
# Create GKE cluster
gcloud container clusters create minikernel-cluster \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --zone us-central1-a

# Get credentials
gcloud container clusters get-credentials minikernel-cluster \
  --zone us-central1-a

# Install with Helm
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set persistence.data.storageClass=standard-rwo \
  --namespace minikernel \
  --create-namespace
```

---

## Container Orchestration

### Kubernetes

#### Basic Deployment

```yaml
# minikernel-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minikernel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: minikernel
  template:
    metadata:
      labels:
        app: minikernel
    spec:
      containers:
      - name: minikernel
        image: minikernel:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        env:
        - name: MINIKERNEL_MODE
          value: "text"
        - name: MINIKERNEL_LOG_LEVEL
          value: "INFO"
```

Apply:
```bash
kubectl apply -f minikernel-deployment.yaml
```

#### StatefulSet (for persistent state)

```yaml
# minikernel-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: minikernel
spec:
  serviceName: minikernel
  replicas: 3
  selector:
    matchLabels:
      app: minikernel
  template:
    metadata:
      labels:
        app: minikernel
    spec:
      containers:
      - name: minikernel
        image: minikernel:latest
        volumeMounts:
        - name: data
          mountPath: /opt/minikernel/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 1Gi
```

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c minikernel/deploy/docker/docker-compose.yml minikernel

# Scale service
docker service scale minikernel_minikernel=3

# View services
docker service ls
```

### Nomad

```hcl
# minikernel.nomad
job "minikernel" {
  datacenters = ["dc1"]
  type = "service"

  group "minikernel" {
    count = 3

    task "minikernel" {
      driver = "docker"

      config {
        image = "minikernel:latest"
        port_map {
          http = 8080
        }
      }

      resources {
        cpu    = 1000
        memory = 2048
      }

      env {
        MINIKERNEL_MODE = "text"
        MINIKERNEL_LOG_LEVEL = "INFO"
      }
    }
  }
}
```

Deploy:
```bash
nomad job run minikernel.nomad
```

---

## Edge Computing

### Raspberry Pi

```bash
# Install on Raspberry Pi OS
sudo bash minikernel/deploy/installers/install-linux.sh

# Configure for low memory
export MINIKERNEL_MODE=text
export MINIKERNEL_LOG_LEVEL=WARNING

# Start service
sudo systemctl start minikernel
```

### K3s (Lightweight Kubernetes)

```bash
# Install K3s on edge device
curl -sfL https://get.k3s.io | sh -

# Deploy MiniKernel
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set resources.limits.memory=1Gi \
  --set resources.requests.memory=256Mi \
  --set persistence.enabled=false
```

### Docker on Edge

```bash
# Run with resource limits for edge devices
docker run -d \
  --name minikernel \
  --memory=1g \
  --cpus=1 \
  --restart=unless-stopped \
  minikernel:latest --mode text
```

---

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy MiniKernel

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: |
          docker build -f minikernel/deploy/docker/Dockerfile \
            -t minikernel:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push minikernel:${{ github.sha }}
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/minikernel \
            minikernel=minikernel:${{ github.sha }}
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - build
  - deploy

build:
  stage: build
  script:
    - docker build -f minikernel/deploy/docker/Dockerfile -t minikernel:$CI_COMMIT_SHA .
    - docker push minikernel:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - helm upgrade --install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
        --set image.tag=$CI_COMMIT_SHA \
        --namespace minikernel
```

### Jenkins

```groovy
pipeline {
    agent any
    
    stages {
        stage('Build') {
            steps {
                sh 'docker build -f minikernel/deploy/docker/Dockerfile -t minikernel:${BUILD_NUMBER} .'
            }
        }
        
        stage('Test') {
            steps {
                sh 'docker run minikernel:${BUILD_NUMBER} pytest tests/'
            }
        }
        
        stage('Deploy') {
            steps {
                sh '''
                    helm upgrade --install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
                        --set image.tag=${BUILD_NUMBER} \
                        --namespace minikernel
                '''
            }
        }
    }
}
```

---

## Multi-Environment Setup

### Development, Staging, Production

**Directory structure:**
```
environments/
├── dev/
│   └── values.yaml
├── staging/
│   └── values.yaml
└── prod/
    └── values.yaml
```

**dev/values.yaml:**
```yaml
replicaCount: 1
resources:
  limits:
    memory: 1Gi
minikernel:
  logLevel: DEBUG
  confirmationMode: auto
persistence:
  enabled: false
```

**staging/values.yaml:**
```yaml
replicaCount: 2
resources:
  limits:
    memory: 2Gi
minikernel:
  logLevel: INFO
  confirmationMode: text
persistence:
  enabled: true
```

**prod/values.yaml:**
```yaml
replicaCount: 5
resources:
  limits:
    memory: 4Gi
minikernel:
  logLevel: WARNING
  confirmationMode: text
persistence:
  enabled: true
autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20
ingress:
  enabled: true
  hosts:
    - host: minikernel.example.com
```

**Deploy:**
```bash
# Development
helm install minikernel-dev ./minikernel/deploy/kubernetes/helm/minikernel \
  -f environments/dev/values.yaml \
  --namespace dev

# Staging
helm install minikernel-staging ./minikernel/deploy/kubernetes/helm/minikernel \
  -f environments/staging/values.yaml \
  --namespace staging

# Production
helm install minikernel-prod ./minikernel/deploy/kubernetes/helm/minikernel \
  -f environments/prod/values.yaml \
  --namespace production
```

---

## Monitoring & Observability

### Prometheus + Grafana

```yaml
# monitoring-values.yaml
serviceMonitor:
  enabled: true
  interval: 30s

dashboards:
  enabled: true
  label: grafana_dashboard
```

### ELK Stack

```yaml
# logging-values.yaml
extraContainers:
  - name: filebeat
    image: docker.elastic.co/beats/filebeat:8.0.0
    volumeMounts:
      - name: logs
        mountPath: /opt/minikernel/logs
```

---

## Best Practices

1. **Use specific image tags** in production (not `latest`)
2. **Set resource limits** to prevent resource exhaustion
3. **Enable persistence** for stateful deployments
4. **Use secrets** for sensitive configuration
5. **Implement health checks** (liveness/readiness probes)
6. **Enable autoscaling** for variable loads
7. **Use namespaces** for isolation
8. **Configure logging** and monitoring
9. **Regular backups** of persistent volumes
10. **Security scanning** of container images

---

## Troubleshooting

See main [DEPLOYMENT.md](../DEPLOYMENT.md#troubleshooting) for detailed troubleshooting guide.

---

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Cloud Provider Docs](../DEPLOYMENT.md#cloud-deployments)
