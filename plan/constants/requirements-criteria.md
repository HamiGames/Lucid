# this file is a list of the versions of the libraries required for all the requirements text files in the /Lucid project.

##**Lib refs:**
'''
fastapi>=0.111,<1.0
uvicorn[standard]>=0.30
pydantic>=2.5,<3.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0

# HTTP clients
httpx>=0.26.0
aiohttp==3.9.1

# Database drivers (Mongo)
motor==3.3.2
pymongo>=4.6.1

# Caches
redis>=5.0.1
aioredis==2.0.1

# Auth/security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
cryptography>=42.0.0
pycryptodome==3.19.0
bcrypt>=4.1,<5

# Async tooling
asyncio-mqtt==0.16.1

# Logging/metrics
structlog==24.1.0
prometheus-client==0.19.0

# Validation and misc
email-validator>=2.1,<3
phonenumbers==8.13.25

# Optional (when used)
uvloop==0.19.0
httptools==0.6.1
gunicorn==22.0.0
requests[socks]
'''