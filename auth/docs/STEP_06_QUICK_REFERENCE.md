# Step 6: Authentication Container Build - Quick Reference

## Quick Start

### Build Container
```bash
# From project root
cd Lucid
docker build -f auth/Dockerfile -t lucid-auth-service:latest auth/
```

### Run Container
```bash
docker run -d \
  --name lucid-auth-service \
  --network lucid-network \
  -p 8089:8089 \
  -e JWT_SECRET_KEY="your-secret-key-here" \
  -e MONGODB_URI="mongodb://mongodb:27017/lucid_auth" \
  -e REDIS_URI="redis://redis:6379/1" \
  lucid-auth-service:latest
```

### Validate
```bash
# Health check
curl http://localhost:8089/health

# Service info
curl http://localhost:8089/meta/info
```

---

## Files Created

| File | Purpose | Size |
|------|---------|------|
| `infrastructure/containers/auth/Dockerfile.auth-service` | Infrastructure Dockerfile | ~200 lines |
| `infrastructure/containers/auth/.dockerignore` | Build optimization | ~180 lines |
| `auth/Dockerfile` | Enhanced primary Dockerfile | ~150 lines |
| `auth/.dockerignore` | Build optimization | ~110 lines |
| `auth/STEP_06_COMPLETION_SUMMARY.md` | Full documentation | ~800 lines |
| `auth/STEP_06_QUICK_REFERENCE.md` | This file | ~100 lines |

---

## Key Configuration

**Service**: lucid-auth-service  
**Port**: 8089  
**Base Image**: gcr.io/distroless/python3-debian12:latest  
**Network**: lucid-network  
**Health Endpoint**: /health  

---

## Required Environment Variables

```bash
JWT_SECRET_KEY=<32+ character secret>
MONGODB_URI=mongodb://mongodb:27017/lucid_auth
REDIS_URI=redis://redis:6379/1
```

---

## Docker Compose

```bash
cd auth/
docker-compose up -d auth-service
```

---

## Troubleshooting

### Container won't start
```bash
docker logs lucid-auth-service
```

### Health check fails
```bash
curl -v http://localhost:8089/health
```

### Check dependencies
```bash
docker exec lucid-auth-service python -c "import fastapi, uvicorn, jwt, motor"
```

---

## Next Steps

1. Run Step 7: Foundation Integration Testing
2. Test auth service with database
3. Verify JWT token generation
4. Test hardware wallet integration (if available)

---

## References

- Full documentation: `STEP_06_COMPLETION_SUMMARY.md`
- Build guide: `../../plan/API_plans/00-master-architecture/13-BUILD_REQUIREMENTS_GUIDE.md`
- Cluster guide: `../../plan/API_plans/00-master-architecture/10-CLUSTER_09_AUTHENTICATION_BUILD_GUIDE.md`

