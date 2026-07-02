# MiniKernel Helm Chart

Official Helm chart for deploying MiniKernel on Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support (for persistent storage)

## Quick Start

### Add Helm Repository (if published)

```bash
helm repo add minikernel https://charts.minikernel.io
helm repo update
```

### Install from Local Chart

```bash
# From repository root
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel

# Or with custom values
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --values custom-values.yaml
```

## Configuration

### Basic Configuration

```bash
# Install with custom mode
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set minikernel.mode=text \
  --set minikernel.logLevel=INFO

# Install with resource limits
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set resources.requests.memory=512Mi \
  --set resources.limits.memory=2Gi
```

### Values File Examples

#### Development Configuration

Create `dev-values.yaml`:

```yaml
replicaCount: 1

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 256Mi

minikernel:
  mode: text
  logLevel: DEBUG
  confirmationMode: auto  # Auto-approve for testing

persistence:
  enabled: false  # Use emptyDir for dev

ingress:
  enabled: false
```

Install:
```bash
helm install minikernel-dev ./minikernel/deploy/kubernetes/helm/minikernel \
  -f dev-values.yaml
```

#### Production Configuration

Create `prod-values.yaml`:

```yaml
replicaCount: 3

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

minikernel:
  mode: text
  logLevel: INFO
  confirmationMode: text
  
  capabilities:
    fileRead: true
    fileWrite: false
    fileDelete: false
    processList: true
    processKill: false

persistence:
  enabled: true
  data:
    storageClass: "fast-ssd"
    size: 5Gi
  logs:
    storageClass: "standard"
    size: 2Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: minikernel.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: minikernel-tls
      hosts:
        - minikernel.example.com

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - minikernel
          topologyKey: kubernetes.io/hostname
```

Install:
```bash
helm install minikernel-prod ./minikernel/deploy/kubernetes/helm/minikernel \
  -f prod-values.yaml \
  --namespace minikernel \
  --create-namespace
```

#### GPU Configuration (with LLM)

Create `gpu-values.yaml`:

```yaml
replicaCount: 1

resources:
  limits:
    cpu: 4000m
    memory: 8Gi
    nvidia.com/gpu: 1
  requests:
    cpu: 2000m
    memory: 4Gi
    nvidia.com/gpu: 1

minikernel:
  mode: text
  logLevel: INFO
  
  llm:
    enabled: true
    model: "llama-3-8b-q4.gguf"
    contextSize: 4096
    threads: 8
    gpuLayers: 35

persistence:
  enabled: true
  models:
    size: 10Gi

nodeSelector:
  nvidia.com/gpu: "true"

tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

Install:
```bash
helm install minikernel-gpu ./minikernel/deploy/kubernetes/helm/minikernel \
  -f gpu-values.yaml
```

## Common Operations

### Upgrade

```bash
# Upgrade with new values
helm upgrade minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  -f prod-values.yaml

# Upgrade with new image
helm upgrade minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set image.tag=0.2.0
```

### Rollback

```bash
# List releases
helm history minikernel

# Rollback to previous version
helm rollback minikernel

# Rollback to specific revision
helm rollback minikernel 2
```

### Uninstall

```bash
# Uninstall release (keeps PVCs)
helm uninstall minikernel

# Uninstall and delete PVCs
helm uninstall minikernel
kubectl delete pvc -l app.kubernetes.io/instance=minikernel
```

### Get Status

```bash
# Check release status
helm status minikernel

# Get values
helm get values minikernel

# Get all info
helm get all minikernel
```

## Configuration Parameters

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `minikernel` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### MiniKernel Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `minikernel.mode` | Operation mode (text/voice) | `text` |
| `minikernel.logLevel` | Log level | `INFO` |
| `minikernel.confirmationMode` | Confirmation mode | `text` |
| `minikernel.llm.enabled` | Enable LLM inference | `false` |
| `minikernel.llm.model` | LLM model file | `llama-3-8b-q4.gguf` |

### Resource Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.limits.cpu` | CPU limit | `2000m` |
| `resources.limits.memory` | Memory limit | `2Gi` |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `512Mi` |

### Persistence Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `persistence.enabled` | Enable persistence | `true` |
| `persistence.data.size` | Data volume size | `1Gi` |
| `persistence.logs.size` | Logs volume size | `500Mi` |
| `persistence.models.size` | Models volume size | `5Gi` |

### Autoscaling Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable HPA | `false` |
| `autoscaling.minReplicas` | Minimum replicas | `1` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU % | `80` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts[0].host` | Hostname | `minikernel.example.com` |

## Examples

### AWS EKS Deployment

```bash
# Install with AWS-specific storage class
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set persistence.data.storageClass=gp3 \
  --set persistence.logs.storageClass=gp3 \
  --namespace minikernel \
  --create-namespace
```

### Azure AKS Deployment

```bash
# Install with Azure-specific storage class
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set persistence.data.storageClass=managed-premium \
  --set persistence.logs.storageClass=managed-standard \
  --namespace minikernel \
  --create-namespace
```

### Google GKE Deployment

```bash
# Install with GKE-specific storage class
helm install minikernel ./minikernel/deploy/kubernetes/helm/minikernel \
  --set persistence.data.storageClass=standard-rwo \
  --set persistence.logs.storageClass=standard-rwo \
  --namespace minikernel \
  --create-namespace
```

### Multi-Tenant Setup

Deploy multiple isolated instances:

```bash
# Tenant 1
helm install minikernel-tenant1 ./minikernel/deploy/kubernetes/helm/minikernel \
  --namespace tenant1 \
  --create-namespace

# Tenant 2
helm install minikernel-tenant2 ./minikernel/deploy/kubernetes/helm/minikernel \
  --namespace tenant2 \
  --create-namespace
```

## Monitoring

### Prometheus Integration

Add ServiceMonitor for Prometheus Operator:

```yaml
# prometheus-values.yaml
serviceMonitor:
  enabled: true
  interval: 30s
  scrapeTimeout: 10s
```

### Logging

View logs:
```bash
# Get pod name
kubectl get pods -l app.kubernetes.io/name=minikernel

# View logs
kubectl logs -f minikernel-xxxx

# View logs from all replicas
kubectl logs -l app.kubernetes.io/name=minikernel --all-containers=true -f
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod minikernel-xxxx

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Check logs
kubectl logs minikernel-xxxx
```

### PVC Issues

```bash
# Check PVC status
kubectl get pvc

# Describe PVC
kubectl describe pvc minikernel-data

# Check if PV is bound
kubectl get pv
```

### Resource Issues

```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods

# Describe node
kubectl describe node <node-name>
```

## Advanced Configuration

### Custom Init Containers

Add to values:
```yaml
initContainers:
  - name: download-model
    image: busybox
    command: ['sh', '-c', 'wget -O /models/model.gguf https://example.com/model.gguf']
    volumeMounts:
      - name: models
        mountPath: /models
```

### Sidecar Containers

Add to values:
```yaml
extraContainers:
  - name: log-forwarder
    image: fluent/fluent-bit
    # ... fluent-bit config
```

### Custom Environment Variables

```yaml
env:
  - name: CUSTOM_VAR
    value: "custom_value"
  - name: SECRET_VAR
    valueFrom:
      secretKeyRef:
        name: my-secret
        key: password
```

## Security Best Practices

1. **Use Non-Root User** (enabled by default)
2. **Enable Network Policies**
3. **Use Pod Security Standards**
4. **Enable RBAC**
5. **Use Secrets for Sensitive Data**
6. **Enable TLS/HTTPS**
7. **Regular Security Updates**

## Support

- **Documentation**: [../DEPLOYMENT.md](../DEPLOYMENT.md)
- **Issues**: GitHub Issues
- **Community**: Discord (coming soon)

## License

MIT License - see [LICENSE](../../../../LICENSE)
