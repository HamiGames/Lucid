# TRON Payment Cluster - Deployment Operations

## Deployment Architecture

### Container Orchestration
```yaml
# kubernetes/tron-payment-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tron-payment-service
  namespace: lucid-payment
  labels:
    app: tron-payment-service
    version: v1.0.0
    cluster: tron-payment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tron-payment-service
  template:
    metadata:
      labels:
        app: tron-payment-service
        version: v1.0.0
        cluster: tron-payment
    spec:
      serviceAccountName: tron-payment-service-account
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      containers:
      - name: tron-payment-service
        image: lucid/tron-payment-service:v1.0.0
        imagePullPolicy: Always
        ports:
        - containerPort: 8085
          name: http
          protocol: TCP
        env:
        - name: NODE_ENV
          value: "production"
        - name: PORT
          value: "8085"
        - name: MONGODB_URI
          valueFrom:
            secretKeyRef:
              name: tron-payment-secrets
              key: mongodb-uri
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: tron-payment-secrets
              key: redis-url
        - name: TRON_API_KEY
          valueFrom:
            secretKeyRef:
              name: tron-payment-secrets
              key: tron-api-key
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: tron-payment-secrets
              key: jwt-secret
        - name: ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: tron-payment-secrets
              key: encryption-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8085
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8085
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: var-tmp
          mountPath: /var/tmp
      volumes:
      - name: tmp
        emptyDir: {}
      - name: var-tmp
        emptyDir: {}
      nodeSelector:
        kubernetes.io/os: linux
      tolerations:
      - key: "lucid.io/tron-payment"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - tron-payment-service
              topologyKey: kubernetes.io/hostname
---
apiVersion: v1
kind: Service
metadata:
  name: tron-payment-service
  namespace: lucid-payment
  labels:
    app: tron-payment-service
spec:
  type: ClusterIP
  ports:
  - port: 8085
    targetPort: 8085
    protocol: TCP
    name: http
  selector:
    app: tron-payment-service
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tron-payment-service-account
  namespace: lucid-payment
automountServiceAccountToken: false
---
apiVersion: v1
kind: Secret
metadata:
  name: tron-payment-secrets
  namespace: lucid-payment
type: Opaque
data:
  mongodb-uri: <base64-encoded-mongodb-uri>
  redis-url: <base64-encoded-redis-url>
  tron-api-key: <base64-encoded-tron-api-key>
  jwt-secret: <base64-encoded-jwt-secret>
  encryption-key: <base64-encoded-encryption-key>
```

### Service Mesh Configuration
```yaml
# istio/tron-payment-virtual-service.yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: tron-payment-vs
  namespace: lucid-payment
spec:
  hosts:
  - tron-payment.lucid-blockchain.org
  gateways:
  - lucid-gateway
  http:
  - match:
    - uri:
        prefix: /api/v1/tron
    route:
    - destination:
        host: tron-payment-service
        port:
          number: 8085
    timeout: 30s
    retries:
      attempts: 3
      perTryTimeout: 10s
    fault:
      abort:
        percentage:
          value: 0.1
        httpStatus: 500
  - match:
    - uri:
        prefix: /api/v1/wallets
    route:
    - destination:
        host: tron-payment-service
        port:
          number: 8085
    timeout: 30s
    retries:
      attempts: 3
      perTryTimeout: 10s
  - match:
    - uri:
        prefix: /api/v1/usdt
    route:
    - destination:
        host: tron-payment-service
        port:
          number: 8085
    timeout: 60s
    retries:
      attempts: 3
      perTryTimeout: 20s
  - match:
    - uri:
        prefix: /api/v1/payouts
    route:
    - destination:
        host: tron-payment-service
        port:
          number: 8085
    timeout: 120s
    retries:
      attempts: 3
      perTryTimeout: 30s
  - match:
    - uri:
        prefix: /api/v1/staking
    route:
    - destination:
        host: tron-payment-service
        port:
          number: 8085
    timeout: 60s
    retries:
      attempts: 3
      perTryTimeout: 20s
  - match:
    - uri:
        prefix: /api/v1/payments
    route:
    - destination:
        host: tron-payment-service
        port:
          number: 8085
    timeout: 90s
    retries:
      attempts: 3
      perTryTimeout: 25s
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: tron-payment-dr
  namespace: lucid-payment
spec:
  host: tron-payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
        maxRetries: 3
    circuitBreaker:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
  - name: v1
    labels:
      version: v1.0.0
  - name: v2
    labels:
      version: v1.1.0
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/tron-payment-deploy.yml
name: TRON Payment Service CI/CD

on:
  push:
    branches: [main, develop]
    paths: ['src/tron-payment/**', 'tests/tron-payment/**']
  pull_request:
    branches: [main]
    paths: ['src/tron-payment/**', 'tests/tron-payment/**']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: lucid/tron-payment-service

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:6.0
        ports:
          - 27017:27017
        options: >-
          --health-cmd "mongosh --eval 'db.runCommand({ping: 1})'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci

    - name: Run linting
      run: npm run lint

    - name: Run type checking
      run: npm run type-check

    - name: Run unit tests
      run: npm run test:unit
      env:
        NODE_ENV: test
        MONGODB_URI: mongodb://localhost:27017/lucid_tron_payment_test
        REDIS_URL: redis://localhost:6379

    - name: Run integration tests
      run: npm run test:integration
      env:
        NODE_ENV: test
        MONGODB_URI: mongodb://localhost:27017/lucid_tron_payment_test
        REDIS_URL: redis://localhost:6379

    - name: Run E2E tests
      run: npm run test:e2e
      env:
        NODE_ENV: test
        MONGODB_URI: mongodb://localhost:27017/lucid_tron_payment_test
        REDIS_URL: redis://localhost:6379

    - name: Generate coverage report
      run: npm run test:coverage

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage/lcov.info
        flags: tron-payment
        name: tron-payment-coverage

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'

    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

    - name: Run npm audit
      run: npm audit --audit-level=high

  build:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'

    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./src/tron-payment/Dockerfile
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        platforms: linux/amd64,linux/arm64

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging

    steps:
    - uses: actions/checkout@v4

    - name: Configure kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.28.0'

    - name: Install Helm
      uses: azure/setup-helm@v3
      with:
        version: 'v3.12.0'

    - name: Deploy to staging
      run: |
        helm upgrade --install tron-payment-staging \
          ./helm/tron-payment \
          --namespace lucid-payment-staging \
          --create-namespace \
          --set image.repository=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }} \
          --set image.tag=develop \
          --set replicaCount=2 \
          --set resources.requests.memory=256Mi \
          --set resources.requests.cpu=125m \
          --set resources.limits.memory=512Mi \
          --set resources.limits.cpu=250m \
          --set ingress.host=tron-payment-staging.lucid-blockchain.org \
          --set ingress.tls.secretName=lucid-tls-staging

    - name: Run smoke tests
      run: |
        npm run test:smoke -- --baseUrl=https://tron-payment-staging.lucid-blockchain.org

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
    - uses: actions/checkout@v4

    - name: Configure kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.28.0'

    - name: Install Helm
      uses: azure/setup-helm@v3
      with:
        version: 'v3.12.0'

    - name: Deploy to production
      run: |
        helm upgrade --install tron-payment \
          ./helm/tron-payment \
          --namespace lucid-payment \
          --create-namespace \
          --set image.repository=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }} \
          --set image.tag=latest \
          --set replicaCount=3 \
          --set resources.requests.memory=512Mi \
          --set resources.requests.cpu=250m \
          --set resources.limits.memory=1Gi \
          --set resources.limits.cpu=500m \
          --set ingress.host=tron-payment.lucid-blockchain.org \
          --set ingress.tls.secretName=lucid-tls \
          --set autoscaling.enabled=true \
          --set autoscaling.minReplicas=3 \
          --set autoscaling.maxReplicas=10 \
          --set autoscaling.targetCPUUtilizationPercentage=70 \
          --set autoscaling.targetMemoryUtilizationPercentage=80

    - name: Run production smoke tests
      run: |
        npm run test:smoke -- --baseUrl=https://tron-payment.lucid-blockchain.org

    - name: Notify deployment success
      uses: 8398a7/action-slack@v3
      with:
        status: success
        channel: '#deployments'
        text: 'TRON Payment Service deployed to production successfully! 🚀'
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Helm Chart
```yaml
# helm/tron-payment/Chart.yaml
apiVersion: v2
name: tron-payment
description: TRON Payment Service for Lucid Blockchain
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - tron
  - payment
  - blockchain
  - lucid
home: https://lucid-blockchain.org
sources:
  - https://github.com/HamiGames/Lucid
maintainers:
  - name: Lucid Development Team
    email: dev@lucid-blockchain.org
```

```yaml
# helm/tron-payment/values.yaml
replicaCount: 3

image:
  repository: lucid/tron-payment-service
  pullPolicy: IfNotPresent
  tag: "latest"

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations: {}

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL

service:
  type: ClusterIP
  port: 8085
  targetPort: 8085

ingress:
  enabled: true
  className: "istio"
  annotations:
    kubernetes.io/ingress.class: istio
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: tron-payment.lucid-blockchain.org
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: lucid-tls
      hosts:
        - tron-payment.lucid-blockchain.org

resources:
  limits:
    cpu: 500m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

nodeSelector: {}

tolerations: []

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - tron-payment-service
        topologyKey: kubernetes.io/hostname

env:
  NODE_ENV: production
  PORT: "8085"

secrets:
  create: true
  mongodb-uri: ""
  redis-url: ""
  tron-api-key: ""
  jwt-secret: ""
  encryption-key: ""

persistence:
  enabled: false

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    scrapeTimeout: 10s
    path: /metrics
```

## Monitoring & Observability

### Prometheus Configuration
```yaml
# monitoring/prometheus-tron-payment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-tron-payment-config
  namespace: lucid-monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    rule_files:
      - "tron-payment-rules.yml"

    scrape_configs:
    - job_name: 'tron-payment-service'
      static_configs:
      - targets: ['tron-payment-service:8085']
      metrics_path: '/metrics'
      scrape_interval: 30s
      scrape_timeout: 10s
      honor_labels: true

    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - alertmanager:9093

  tron-payment-rules.yml: |
    groups:
    - name: tron-payment-alerts
      rules:
      - alert: TronPaymentServiceDown
        expr: up{job="tron-payment-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "TRON Payment Service is down"
          description: "TRON Payment Service has been down for more than 1 minute"

      - alert: TronPaymentHighErrorRate
        expr: rate(http_requests_total{job="tron-payment-service",status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in TRON Payment Service"
          description: "Error rate is {{ $value }} errors per second"

      - alert: TronPaymentHighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="tron-payment-service"}[5m])) > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High response time in TRON Payment Service"
          description: "95th percentile response time is {{ $value }} seconds"

      - alert: TronPaymentHighMemoryUsage
        expr: container_memory_usage_bytes{container="tron-payment-service"} / container_spec_memory_limit_bytes{container="tron-payment-service"} > 0.8
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage in TRON Payment Service"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      - alert: TronPaymentHighCPUUsage
        expr: rate(container_cpu_usage_seconds_total{container="tron-payment-service"}[5m]) > 0.8
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage in TRON Payment Service"
          description: "CPU usage is {{ $value | humanizePercentage }}"

      - alert: TronNetworkUnavailable
        expr: tron_network_status{status="down"} == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "TRON Network is unavailable"
          description: "TRON Network status is down"

      - alert: TronPaymentRateLimitExceeded
        expr: rate(tron_payment_rate_limit_exceeded_total[5m]) > 0.1
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Rate limit exceeded in TRON Payment Service"
          description: "Rate limit exceeded {{ $value }} times per second"
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "id": null,
    "title": "TRON Payment Service Dashboard",
    "tags": ["tron", "payment", "lucid"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(http_requests_total{job=\"tron-payment-service\"}[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps"
          }
        }
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket{job=\"tron-payment-service\"}[5m]))",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job=\"tron-payment-service\"}[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job=\"tron-payment-service\"}[5m]))",
            "legendFormat": "99th percentile"
          }
        ],
        "yAxes": [
          {
            "unit": "s"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{job=\"tron-payment-service\",status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          },
          {
            "expr": "rate(http_requests_total{job=\"tron-payment-service\",status=~\"4..\"}[5m])",
            "legendFormat": "4xx errors"
          }
        ],
        "yAxes": [
          {
            "unit": "reqps"
          }
        ]
      },
      {
        "id": 4,
        "title": "TRON Network Status",
        "type": "stat",
        "targets": [
          {
            "expr": "tron_network_status",
            "legendFormat": "{{status}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "mappings": [
              {
                "type": "value",
                "value": "1",
                "text": "Healthy"
              },
              {
                "type": "value",
                "value": "0",
                "text": "Down"
              }
            ],
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {
                  "color": "red",
                  "value": 0
                },
                {
                  "color": "green",
                  "value": 1
                }
              ]
            }
          }
        }
      },
      {
        "id": 5,
        "title": "USDT Transfer Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tron_usdt_transfers_total[5m])",
            "legendFormat": "USDT transfers/sec"
          }
        ],
        "yAxes": [
          {
            "unit": "reqps"
          }
        ]
      },
      {
        "id": 6,
        "title": "Payout Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tron_payouts_processed_total[5m])",
            "legendFormat": "Payouts/sec"
          }
        ],
        "yAxes": [
          {
            "unit": "reqps"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

## Backup & Recovery

### Database Backup
```bash
#!/bin/bash
# scripts/backup-tron-payment-db.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/backups/tron-payment"
MONGODB_URI="${MONGODB_URI:-mongodb://localhost:27017/lucid_tron_payment}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-lucid-backups}"
S3_PREFIX="${S3_PREFIX:-tron-payment/}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Generate backup filename
BACKUP_FILE="tron-payment-backup-$(date +%Y%m%d_%H%M%S).tar.gz"

echo "Starting TRON Payment database backup..."

# Create MongoDB dump
mongodump \
  --uri="${MONGODB_URI}" \
  --out="${BACKUP_DIR}/dump" \
  --gzip

# Create tar archive
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" -C "${BACKUP_DIR}" dump/

# Upload to S3
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${S3_BUCKET}/${S3_PREFIX}${BACKUP_FILE}"

# Clean up local backup
rm -rf "${BACKUP_DIR}/dump"
rm -f "${BACKUP_DIR}/${BACKUP_FILE}"

# Clean up old backups from S3
aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}" | \
  awk '$1 < "'$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)'" {print $4}' | \
  xargs -I {} aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}{}"

echo "Backup completed: ${BACKUP_FILE}"
```

### Recovery Script
```bash
#!/bin/bash
# scripts/restore-tron-payment-db.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/backups/tron-payment"
MONGODB_URI="${MONGODB_URI:-mongodb://localhost:27017/lucid_tron_payment}"
S3_BUCKET="${S3_BUCKET:-lucid-backups}"
S3_PREFIX="${S3_PREFIX:-tron-payment/}"

# Check if backup file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup-file>"
    echo "Available backups:"
    aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}" | awk '{print $4}'
    exit 1
fi

BACKUP_FILE="$1"

echo "Starting TRON Payment database restore from ${BACKUP_FILE}..."

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Download backup from S3
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}${BACKUP_FILE}" "${BACKUP_DIR}/"

# Extract backup
tar -xzf "${BACKUP_DIR}/${BACKUP_FILE}" -C "${BACKUP_DIR}"

# Restore MongoDB dump
mongorestore \
  --uri="${MONGODB_URI}" \
  --dir="${BACKUP_DIR}/dump/lucid_tron_payment" \
  --drop

# Clean up
rm -rf "${BACKUP_DIR}/dump"
rm -f "${BACKUP_DIR}/${BACKUP_FILE}"

echo "Restore completed successfully"
```

## Disaster Recovery

### DR Plan
```yaml
# disaster-recovery/dr-plan.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tron-payment-dr-plan
  namespace: lucid-payment
data:
  dr-plan.md: |
    # TRON Payment Service Disaster Recovery Plan

    ## Recovery Time Objectives (RTO)
    - Critical services: 15 minutes
    - Standard services: 30 minutes
    - Non-critical services: 2 hours

    ## Recovery Point Objectives (RPO)
    - Database: 5 minutes
    - Configuration: 1 hour
    - Logs: 24 hours

    ## Recovery Procedures

    ### 1. Service Failure
    1. Check service health endpoints
    2. Review logs for errors
    3. Restart service if necessary
    4. Scale up replicas if needed
    5. Notify team via Slack

    ### 2. Database Failure
    1. Check MongoDB cluster status
    2. Failover to secondary if available
    3. Restore from latest backup if needed
    4. Verify data integrity
    5. Update connection strings

    ### 3. Network Failure
    1. Check network connectivity
    2. Verify DNS resolution
    3. Check load balancer status
    4. Failover to backup region if needed
    5. Update routing tables

    ### 4. Complete Region Failure
    1. Activate disaster recovery site
    2. Restore from latest backup
    3. Update DNS records
    4. Verify all services
    5. Notify stakeholders

    ## Contact Information
    - Primary: dev@lucid-blockchain.org
    - Emergency: +1-XXX-XXX-XXXX
    - Slack: #incident-response
```

### Multi-Region Deployment
```yaml
# kubernetes/tron-payment-multiregion.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: tron-payment-us-east
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/HamiGames/Lucid
    targetRevision: HEAD
    path: kubernetes/tron-payment
  destination:
    server: https://kubernetes.us-east-1.amazonaws.com
    namespace: lucid-payment
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: tron-payment-eu-west
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/HamiGames/Lucid
    targetRevision: HEAD
    path: kubernetes/tron-payment
  destination:
    server: https://kubernetes.eu-west-1.amazonaws.com
    namespace: lucid-payment
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

## Operational Procedures

### Health Checks
```typescript
// src/health/health.controller.ts
import { Controller, Get } from '@nestjs/common';
import { HealthCheck, HealthCheckService, HealthCheckResult } from '@nestjs/terminus';
import { TronNetworkHealthIndicator } from './tron-network.health';
import { DatabaseHealthIndicator } from './database.health';
import { RedisHealthIndicator } from './redis.health';

@Controller('health')
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private tronNetwork: TronNetworkHealthIndicator,
    private database: DatabaseHealthIndicator,
    private redis: RedisHealthIndicator,
  ) {}

  @Get()
  @HealthCheck()
  check(): Promise<HealthCheckResult> {
    return this.health.check([
      () => this.database.isHealthy('database'),
      () => this.redis.isHealthy('redis'),
      () => this.tronNetwork.isHealthy('tron-network'),
    ]);
  }

  @Get('ready')
  @HealthCheck()
  ready(): Promise<HealthCheckResult> {
    return this.health.check([
      () => this.database.isHealthy('database'),
      () => this.redis.isHealthy('redis'),
    ]);
  }

  @Get('live')
  @HealthCheck()
  live(): Promise<HealthCheckResult> {
    return this.health.check([]);
  }
}
```

### Maintenance Procedures
```bash
#!/bin/bash
# scripts/maintenance-procedures.sh

set -euo pipefail

# Configuration
NAMESPACE="lucid-payment"
SERVICE_NAME="tron-payment-service"
REPLICA_COUNT=3

echo "Starting TRON Payment Service maintenance procedures..."

# 1. Pre-maintenance checks
echo "1. Running pre-maintenance checks..."
kubectl get pods -n ${NAMESPACE} -l app=${SERVICE_NAME}
kubectl get services -n ${NAMESPACE} -l app=${SERVICE_NAME}
kubectl get ingress -n ${NAMESPACE}

# 2. Scale down service
echo "2. Scaling down service..."
kubectl scale deployment ${SERVICE_NAME} --replicas=0 -n ${NAMESPACE}

# 3. Wait for pods to terminate
echo "3. Waiting for pods to terminate..."
kubectl wait --for=delete pod -l app=${SERVICE_NAME} -n ${NAMESPACE} --timeout=300s

# 4. Perform maintenance tasks
echo "4. Performing maintenance tasks..."
# Add specific maintenance tasks here

# 5. Scale up service
echo "5. Scaling up service..."
kubectl scale deployment ${SERVICE_NAME} --replicas=${REPLICA_COUNT} -n ${NAMESPACE}

# 6. Wait for pods to be ready
echo "6. Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=${SERVICE_NAME} -n ${NAMESPACE} --timeout=300s

# 7. Post-maintenance checks
echo "7. Running post-maintenance checks..."
kubectl get pods -n ${NAMESPACE} -l app=${SERVICE_NAME}
kubectl get services -n ${NAMESPACE} -l app=${SERVICE_NAME}

# 8. Health check
echo "8. Running health check..."
kubectl exec -n ${NAMESPACE} deployment/${SERVICE_NAME} -- curl -f http://localhost:8085/health

echo "Maintenance procedures completed successfully!"
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
