this file is a listing of the active port numbers in the /Lucid project.

##**Database & cache:**
27017: MongoDB
27018: MongoDB (RDP services)
6379: Redis
9200: Elasticsearch HTTP
9300: Elasticsearch transport
##**Core application (8080-8089):**
8080: API Gateway (HTTP)
8081: API Gateway (HTTPS) / RDP Server Manager
8082: Session Storage
8083: Admin Interface
8084: Blockchain Engine
8085: Session Anchoring
8086: Block Manager
8087: Data Chain / Session Pipeline / Session API
8088: Admin Interface (staging) / Service Mesh
8089: Auth Service
##**Application & RDP (8090-8099):****
8090: Session Recorder / RDP Server Manager
8091: Chunk Processor / TRON Client
8092: RDP Controller / Payout Router
8093: RDP Monitor / Wallet Manager
8094: USDT Manager
8095: Node Management
8096: TRX Staking
8097: Payment Gateway
8099: Node Management (staging)
##**Monitoring & extended (8100-8107):**
8100: Admin Interface (monitoring)
8101: TRON Client (monitoring)
8102: Payout Router (monitoring)
8103: Wallet Manager (monitoring)
8104: USDT Manager (monitoring)
8105: TRX Staking (monitoring)
8106: Payment Gateway (monitoring)
8107: Service Mesh (monitoring)
##**Service mesh (Consul):**
8500: Consul HTTP API
8501: Consul HTTPS API
8502: Consul gRPC API
8600: Consul DNS
##**Special ports:**
3389: XRDP Integration (RDP protocol)
8000: GUI base application