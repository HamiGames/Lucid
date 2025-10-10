# Lucid Project - Optimal File Tree Structure for Distroless Builds

## Project Overview
**Lucid** is a custom blockchain-integrated remote desktop access application with enhanced controllers and logging, targeting hybrid Windows 11 development → Raspberry Pi production deployment using distroless container builds.

## Current Analysis
Based on the existing project structure, the following modules have been identified:
- **GUI Modules**: Admin interface with bootstrap wizard, Node management with metrics dashboard, User interfaces with session management, Shared components with encryption and consent management, Build system with PyInstaller and signing, Comprehensive testing suite, Documentation and resources
- **Core Modules**: Networking (Tor/Onion), Security, Configuration, Telemetry
- **Blockchain Integration**: TRON (Shasta testnet + Mainnet), Payment systems
- **RDP Protocol**: Client, Server, Security, Recording, Audit Trail, Resource Monitoring, Hardware Integration, Configuration, Testing, Documentation, Build System
- **Infrastructure**: Docker containers, Compose configurations
- **Node Management**: Consensus, DHT/CRDT, Economy, Governance
- **User Management**: Authentication, Profile Management, Permissions, Role-based Access Control, Session Ownership, Activity Logging, Hardware Wallet Integration
- **User Content**: Client Components, GUI Components, Wallet Management, API Client, Configuration Management, Notifications, Backup, Security Management
- **Session Management**: Core, Encryption, Pipeline, Recording, Management Layer, Storage Management
- **Storage Management**: MongoDB Sharding, Collections Management, Consensus Collections, Database Adapter, Session Storage, Chunk Storage, Backup/Recovery, Data Persistence, Monitoring, Security, Utilities, Testing, Configuration
- **Database Services**: Comprehensive MongoDB Integration, Sharding Services, Collections Management, Consensus Collections, Database Adapters, Models, Utilities, Scripts, Configuration, Documentation
- **VM Management**: Orchestration, Scheduling, Monitoring, Configuration, Blockchain Integration, Lifecycle Management, Resource Management, Security, Networking, Storage, Performance Monitoring, Testing, Integration

## Optimal File Tree Structure

```
Lucid/
├── 📁 .github/                          # GitHub workflows and templates
│   ├── workflows/
│   │   ├── build-distroless.yml         # Multi-stage distroless builds
│   │   ├── test-integration.yml         # Integration testing
│   │   └── deploy-pi.yml               # Raspberry Pi deployment
│   └── ISSUE_TEMPLATE/
│
├── 📁 .devcontainer/                    # Development container configs
│   ├── devcontainer.json               # Main dev container
│   ├── docker-compose.dev.yml          # Development services
│   └── Dockerfile.dev                  # Development image
│
├── 📁 build/                           # Build artifacts and configurations
│   ├── distroless/                     # Distroless build configs
│   │   ├── base/                       # Base distroless images
│   │   ├── gui/                        # GUI service distroless
│   │   ├── blockchain/                 # Blockchain service distroless
│   │   ├── rdp/                        # RDP service distroless
│   │   └── node/                       # Node service distroless
│   ├── multi-stage/                    # Multi-stage Dockerfiles
│   │   ├── Dockerfile.gui              # GUI service build
│   │   ├── Dockerfile.blockchain       # Blockchain service build
│   │   ├── Dockerfile.rdp              # RDP service build
│   │   └── Dockerfile.node             # Node service build
│   └── scripts/                        # Build automation scripts
│       ├── build-distroless.ps1        # Windows build script
│       ├── build-distroless.sh         # Linux build script
│       └── optimize-layers.py          # Layer optimization
│
├── 📁 src/                             # Source code (main application)
│   ├── 📁 core/                        # Core application modules
│   │   ├── __init__.py
│   │   ├── config/                     # Configuration management
│   │   │   ├── __init__.py
│   │   │   ├── manager.py              # Config manager
│   │   │   ├── schemas.py              # Config schemas
│   │   │   └── validators.py           # Config validation
│   │   ├── networking/                 # Network layer
│   │   │   ├── __init__.py
│   │   │   ├── tor_client.py           # Tor/Onion client
│   │   │   ├── security.py             # Network security
│   │   │   └── endpoints.py            # Endpoint management
│   │   ├── security/                   # Security layer
│   │   │   ├── __init__.py
│   │   │   ├── crypto.py               # Cryptographic functions
│   │   │   ├── auth.py                 # Authentication
│   │   │   └── validators.py           # Security validators
│   │   ├── telemetry/                  # Telemetry and monitoring
│   │   │   ├── __init__.py
│   │   │   ├── manager.py              # Telemetry manager
│   │   │   ├── events.py               # Event tracking
│   │   │   └── metrics.py              # Metrics collection
│   │   └── widgets/                    # Shared UI components
│   │       ├── __init__.py
│   │       ├── status.py               # Status indicators
│   │       ├── progress.py             # Progress bars
│   │       └── log_viewer.py           # Log viewing components
│   │
│   ├── 📁 gui/                         # Graphical User Interface
│   │   ├── __init__.py
│   │   ├── main.py                     # Main GUI launcher with platform detection
│   │   ├── user_main.py                # User GUI entry point
│   │   ├── admin_main.py               # Admin GUI entry point
│   │   ├── node_main.py                # Node GUI entry point
│   │   ├── admin/                      # Admin interface
│   │   │   ├── __init__.py
│   │   │   ├── admin_gui.py            # Main admin GUI
│   │   │   ├── backup_restore.py       # Backup/restore functionality
│   │   │   ├── diagnostics.py          # Diagnostic tools
│   │   │   ├── key_management.py       # Key management
│   │   │   ├── payouts_manager.py      # Payouts management
│   │   │   └── bootstrap_wizard.py     # Initial setup and provisioning
│   │   ├── node/                       # Node management interface
│   │   │   ├── __init__.py
│   │   │   ├── node_gui.py             # Node management GUI
│   │   │   ├── status_monitor.py       # Status monitoring
│   │   │   ├── peer_manager.py         # Peer connection management
│   │   │   ├── metrics_dashboard.py    # WorkCredits and PoOT metrics
│   │   │   ├── wallet_monitor.py       # TRX energy and balance monitoring
│   │   │   ├── payout_batches.py       # Payout history and receipts
│   │   │   └── alerts_manager.py       # System alerts and notifications
│   │   ├── user/                       # User interface
│   │   │   ├── __init__.py
│   │   │   ├── user_gui.py             # User interface
│   │   │   └── session_manager.py      # Session management UI
│   │   ├── shared/                     # Shared GUI components
│   │   │   ├── __init__.py
│   │   │   ├── themes.py               # Theme management
│   │   │   ├── components.py           # Reusable components
│   │   │   ├── connection_params.py    # Core parameters module (from SPEC-2)
│   │   │   ├── consent_manager.py      # Terms of Connection and consent receipts
│   │   │   ├── qr_scanner.py           # QR code scanning functionality
│   │   │   ├── file_pickers.py         # Secure file selection dialogs
│   │   │   ├── notifications.py        # Toast notifications and alerts
│   │   │   └── encryption.py           # Local encryption utilities
│   │   ├── config/                     # GUI configuration
│   │   │   ├── __init__.py
│   │   │   ├── default_settings.py     # Default configuration values
│   │   │   ├── torrc_templates/        # Tor configuration templates
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.torrc        # Client Tor configuration template
│   │   │   │   └── relay.torrc         # Relay Tor configuration template
│   │   │   └── themes/                 # UI theme definitions
│   │   │       ├── __init__.py
│   │   │       ├── dark_theme.py       # Dark theme configuration
│   │   │       ├── light_theme.py      # Light theme configuration
│   │   │       └── custom_theme.py     # Custom theme configuration
│   │   ├── resources/                  # GUI resources
│   │   │   ├── __init__.py
│   │   │   ├── icons/                  # Application icons and images
│   │   │   │   ├── __init__.py
│   │   │   │   ├── app_icon.ico        # Main application icon
│   │   │   │   ├── admin_icon.ico      # Admin interface icon
│   │   │   │   ├── node_icon.ico       # Node interface icon
│   │   │   │   ├── user_icon.ico       # User interface icon
│   │   │   │   └── status_icons/       # Status indicator icons
│   │   │   │       ├── __init__.py
│   │   │   │       ├── connected.ico   # Connected status icon
│   │   │   │       ├── disconnected.ico # Disconnected status icon
│   │   │   │       ├── warning.ico     # Warning status icon
│   │   │   │       └── error.ico       # Error status icon
│   │   │   ├── fonts/                  # Custom fonts if needed
│   │   │   │   ├── __init__.py
│   │   │   │   ├── roboto/             # Roboto font family
│   │   │   │   └── monospace/          # Monospace font family
│   │   │   └── terms/                  # Terms of Connection documents
│   │   │       ├── __init__.py
│   │   │       ├── terms_of_service.md # Terms of Service document
│   │   │       ├── privacy_policy.md   # Privacy Policy document
│   │   │       └── consent_agreement.md # Consent Agreement document
│   │   ├── build/                      # GUI build configuration
│   │   │   ├── __init__.py
│   │   │   ├── pyinstaller_specs/      # PyInstaller specification files
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.spec           # Main application spec
│   │   │   │   ├── admin.spec          # Admin GUI spec
│   │   │   │   ├── node.spec           # Node GUI spec
│   │   │   │   └── user.spec           # User GUI spec
│   │   │   ├── tor_vendor.py           # Tor binary fetching and verification
│   │   │   ├── signing_scripts/        # Code signing utilities
│   │   │   │   ├── __init__.py
│   │   │   │   ├── sign_windows.py     # Windows code signing
│   │   │   │   ├── sign_linux.py       # Linux code signing
│   │   │   │   └── verify_signature.py # Signature verification
│   │   │   └── installer_scripts/      # Installer creation scripts
│   │   │       ├── __init__.py
│   │   │       ├── create_installer.py # Installer creation
│   │   │       ├── msi_creator.py      # MSI installer for Windows
│   │   │       └── deb_creator.py      # DEB package for Linux
│   │   ├── tests/                      # GUI tests
│   │   │   ├── __init__.py
│   │   │   ├── test_core/              # Core functionality tests
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_main.py        # Main launcher tests
│   │   │   │   ├── test_config.py      # Configuration tests
│   │   │   │   └── test_shared.py      # Shared component tests
│   │   │   ├── test_user/              # User GUI tests
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_user_gui.py    # User GUI tests
│   │   │   │   └── test_session_manager.py # Session manager tests
│   │   │   ├── test_admin/             # Admin GUI tests
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_admin_gui.py   # Admin GUI tests
│   │   │   │   ├── test_backup_restore.py # Backup/restore tests
│   │   │   │   ├── test_diagnostics.py # Diagnostic tests
│   │   │   │   ├── test_key_management.py # Key management tests
│   │   │   │   ├── test_payouts_manager.py # Payouts manager tests
│   │   │   │   └── test_bootstrap_wizard.py # Bootstrap wizard tests
│   │   │   ├── test_node/              # Node GUI tests
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_node_gui.py    # Node GUI tests
│   │   │   │   ├── test_status_monitor.py # Status monitor tests
│   │   │   │   ├── test_peer_manager.py # Peer manager tests
│   │   │   │   ├── test_metrics_dashboard.py # Metrics dashboard tests
│   │   │   │   ├── test_wallet_monitor.py # Wallet monitor tests
│   │   │   │   ├── test_payout_batches.py # Payout batches tests
│   │   │   │   └── test_alerts_manager.py # Alerts manager tests
│   │   │   └── integration/            # End-to-end integration tests
│   │   │       ├── __init__.py
│   │   │       ├── test_gui_flow.py    # Complete GUI flow tests
│   │   │       ├── test_user_journey.py # User journey tests
│   │   │       └── test_admin_workflow.py # Admin workflow tests
│   │   ├── docs/                       # GUI documentation
│   │   │   ├── __init__.py
│   │   │   ├── README.md               # GUI documentation
│   │   │   ├── user_guide.md           # User GUI usage guide
│   │   │   ├── admin_guide.md          # Admin GUI usage guide
│   │   │   ├── node_guide.md           # Node GUI usage guide
│   │   │   └── development.md          # Development guidelines
│   │   └── requirements/               # GUI requirements
│   │       ├── __init__.py
│   │       ├── base.txt                # Core dependencies
│   │       ├── user.txt                # User GUI specific dependencies
│   │       ├── admin.txt               # Admin GUI specific dependencies
│   │       ├── node.txt                # Node GUI specific dependencies
│   │       └── build.txt               # Build-specific dependencies
│   │
│   ├── 📁 blockchain/                  # Blockchain integration
│   │   ├── __init__.py
│   │   ├── core/                       # Core blockchain functionality
│   │   │   ├── __init__.py
│   │   │   ├── tron_client.py          # TRON blockchain client
│   │   │   ├── wallet_manager.py       # Wallet management
│   │   │   └── transaction_handler.py  # Transaction processing
│   │   ├── api/                        # Blockchain API
│   │   │   ├── __init__.py
│   │   │   ├── routes/                 # API routes
│   │   │   ├── schemas/                # API schemas
│   │   │   └── services/               # API services
│   │   ├── governance/                 # Governance mechanisms
│   │   │   ├── __init__.py
│   │   │   ├── voting.py               # Voting system
│   │   │   └── consensus.py            # Consensus mechanisms
│   │   └── payment_systems/            # Payment processing
│   │       ├── __init__.py
│   │       ├── tron_payments.py        # TRON payment processing
│   │       └── payment_validator.py    # Payment validation
│   │
│   ├── 📁 rdp/                         # Remote Desktop Protocol
│   │   ├── __init__.py
│   │   ├── client/                     # RDP client implementation
│   │   │   ├── __init__.py
│   │   │   ├── connection_manager.py   # Connection management (existing)
│   │   │   ├── rdp_client.py           # RDP client implementation (existing)
│   │   │   ├── connection.py           # Connection management
│   │   │   └── protocol_handler.py     # Protocol handling
│   │   ├── server/                     # RDP server implementation
│   │   │   ├── __init__.py
│   │   │   ├── rdp_server_manager.py   # RDP server manager (existing)
│   │   │   ├── session_controller.py   # Session controller (existing)
│   │   │   ├── xrdp_integration.py     # xrdp server integration (existing)
│   │   │   ├── session_manager.py      # Session management
│   │   │   └── access_control.py       # Access control
│   │   ├── protocol/                   # Protocol implementation
│   │   │   ├── __init__.py
│   │   │   ├── rdp_session.py          # RDP session protocol (existing)
│   │   │   ├── packets.py              # Packet handling
│   │   │   └── encryption.py           # Protocol encryption
│   │   ├── security/                   # RDP security
│   │   │   ├── __init__.py
│   │   │   ├── access_controller.py    # Access controller (existing)
│   │   │   ├── session_validator.py    # Session validator (existing)
│   │   │   ├── trust_controller.py     # Trust controller (existing)
│   │   │   ├── authentication.py       # Authentication
│   │   │   └── encryption.py           # Data encryption
│   │   ├── recorder/                   # Session recording
│   │   │   ├── __init__.py
│   │   │   ├── rdp_host.py             # RDP hosting service (existing)
│   │   │   ├── wayland_integration.py  # Wayland integration (existing)
│   │   │   ├── clipboard_handler.py    # Clipboard handler (existing)
│   │   │   ├── file_transfer_handler.py # File transfer handler (existing)
│   │   │   ├── audit_trail.py          # Session audit logging
│   │   │   ├── keystroke_monitor.py    # Keystroke metadata capture
│   │   │   ├── window_focus_monitor.py # Window focus tracking
│   │   │   ├── resource_monitor.py     # Resource access tracking
│   │   │   ├── audio_handler.py        # Audio redirection controls
│   │   │   ├── printer_handler.py      # Printer redirection controls
│   │   │   ├── usb_handler.py          # USB redirection controls
│   │   │   ├── smart_card_handler.py   # Smart card support
│   │   │   ├── capture.py              # Screen capture
│   │   │   └── storage.py              # Recording storage
│   │   ├── config/                     # RDP configuration
│   │   │   ├── __init__.py
│   │   │   ├── rdp_config.py           # RDP configuration management
│   │   │   ├── xrdp_config.py          # xrdp configuration templates
│   │   │   └── wayland_config.py       # Wayland configuration templates
│   │   ├── tests/                      # RDP testing
│   │   │   ├── __init__.py             # Test package initialization
│   │   │   ├── test_client/            # Client tests directory
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_connection.py
│   │   │   │   └── test_protocol_handler.py
│   │   │   ├── test_server/            # Server tests directory
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_session_manager.py
│   │   │   │   └── test_access_control.py
│   │   │   ├── test_protocol/          # Protocol tests directory
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_packets.py
│   │   │   │   └── test_encryption.py
│   │   │   ├── test_security/          # Security tests directory
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_authentication.py
│   │   │   │   └── test_encryption.py
│   │   │   ├── test_recorder/          # Recorder tests directory
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_capture.py
│   │   │   │   ├── test_audit_trail.py
│   │   │   │   ├── test_keystroke_monitor.py
│   │   │   │   ├── test_window_focus_monitor.py
│   │   │   │   └── test_resource_monitor.py
│   │   │   └── integration/            # Integration tests directory
│   │   │       ├── __init__.py
│   │   │       ├── test_rdp_flow.py
│   │   │       └── test_session_lifecycle.py
│   │   ├── docs/                       # RDP documentation
│   │   │   ├── __init__.py
│   │   │   ├── README.md               # RDP system documentation
│   │   │   ├── client_guide.md         # Client usage guide
│   │   │   ├── server_guide.md         # Server setup guide
│   │   │   ├── security_guide.md       # Security configuration guide
│   │   │   └── troubleshooting.md      # Troubleshooting guide
│   │   ├── build/                      # RDP build configuration
│   │   │   ├── __init__.py             # Build package initialization
│   │   │   ├── docker/                 # Docker build configurations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── Dockerfile.rdp.distroless
│   │   │   │   └── Dockerfile.rdp.multi-stage
│   │   │   ├── scripts/                # Build automation scripts
│   │   │   │   ├── __init__.py
│   │   │   │   ├── build_rdp.py
│   │   │   │   └── optimize_rdp.py
│   │   │   ├── configs/                # Build configuration files
│   │   │   │   ├── __init__.py
│   │   │   │   ├── build_config.yaml
│   │   │   │   └── deployment_config.yaml
│   │   │   ├── ffmpeg_integration.py   # FFmpeg hardware acceleration integration
│   │   │   ├── v4l2_encoder.py         # V4L2 hardware encoder for Pi 5
│   │   │   ├── compression_pipeline.py # Zstd compression pipeline
│   │   │   └── encryption_pipeline.py  # XChaCha20-Poly1305 encryption pipeline
│   │   └── utils/                      # RDP utilities
│   │       ├── __init__.py             # Utilities package initialization
│   │       ├── network_utils.py        # Network utility functions
│   │       ├── display_utils.py        # Display management utilities
│   │       ├── session_utils.py        # Session utility functions
│   │       └── security_utils.py       # Security utility functions
│   │
│   ├── 📁 node/                        # Node management
│   │   ├── __init__.py
│   │   ├── consensus/                  # Consensus mechanisms
│   │   │   ├── __init__.py
│   │   │   ├── algorithm.py            # Consensus algorithm
│   │   │   └── validation.py           # Block validation
│   │   ├── dht_crdt/                   # Distributed Hash Table & CRDT
│   │   │   ├── __init__.py
│   │   │   ├── dht.py                  # DHT implementation
│   │   │   └── crdt.py                 # CRDT implementation
│   │   ├── economy/                    # Economic mechanisms
│   │   │   ├── __init__.py
│   │   │   ├── rewards.py              # Reward system
│   │   │   └── staking.py              # Staking mechanisms
│   │   ├── governance/                 # Node governance
│   │   │   ├── __init__.py
│   │   │   ├── voting.py               # Voting mechanisms
│   │   │   └── proposals.py            # Proposal system
│   │   ├── pools/                      # Connection pools
│   │   │   ├── __init__.py
│   │   │   ├── connection_pool.py      # Connection pooling
│   │   │   └── resource_manager.py     # Resource management
│   │   ├── registration/               # Node registration
│   │   │   ├── __init__.py
│   │   │   ├── registry.py             # Node registry
│   │   │   └── discovery.py            # Node discovery
│   │   ├── shards/                     # Sharding mechanisms
│   │   │   ├── __init__.py
│   │   │   ├── shard_manager.py        # Shard management
│   │   │   └── data_distribution.py    # Data distribution
│   │   ├── sync/                       # Synchronization
│   │   │   ├── __init__.py
│   │   │   ├── state_sync.py           # State synchronization
│   │   │   └── data_sync.py            # Data synchronization
│   │   ├── tor/                        # Tor integration
│   │   │   ├── __init__.py
│   │   │   ├── onion_service.py        # Onion service management
│   │   │   └── routing.py              # Tor routing
│   │   ├── validation/                 # Validation mechanisms
│   │   │   ├── __init__.py
│   │   │   ├── block_validator.py      # Block validation
│   │   │   └── transaction_validator.py # Transaction validation
│   │   └── worker/                     # Worker processes
│   │       ├── __init__.py
│   │       ├── task_processor.py       # Task processing
│   │       └── job_scheduler.py        # Job scheduling
│   │
│   ├── 📁 user/                        # User management
│   │   ├── __init__.py
│   │   ├── authentication.py           # User authentication handlers
│   │   ├── profile_manager.py          # User profile management
│   │   ├── permissions.py              # Permission management system
│   │   ├── role_manager.py             # Role-based access control
│   │   ├── session_ownership.py        # Session ownership verification
│   │   ├── activity_logger.py          # User activity tracking
│   │   ├── audit_trail.py              # User audit trail management
│   │   ├── session_tracker.py          # User session tracking
│   │   ├── hardware_wallet.py          # Hardware wallet integration
│   │   └── wallet_verification.py      # Wallet verification system
│   │
│   ├── 📁 user_content/                # User content and interfaces
│   │   ├── __init__.py
│   │   ├── api_client.py               # API client for user operations
│   │   ├── config_manager.py           # User configuration management
│   │   ├── notifications.py            # Notification system
│   │   ├── backup_manager.py           # User data backup
│   │   ├── security_manager.py         # User security management
│   │   ├── client/                     # Client components
│   │   │   ├── __init__.py
│   │   │   ├── session_manager.py      # Client session management
│   │   │   ├── connection_manager.py   # Connection management
│   │   │   ├── policy_enforcer.py      # Client policy enforcement
│   │   │   ├── trust_controller.py     # Trust controller integration
│   │   │   └── security_validator.py   # Security validation
│   │   ├── gui/                        # User GUI components
│   │   │   ├── __init__.py
│   │   │   ├── main_window.py          # Main GUI window
│   │   │   ├── session_dialog.py       # Session connection dialog
│   │   │   ├── settings_dialog.py      # Settings configuration dialog
│   │   │   ├── status_widgets.py       # Status display widgets
│   │   │   ├── proof_viewer.py         # Session proof viewer
│   │   │   └── wallet_interface.py     # Wallet interface components
│   │   └── wallet/                     # User wallet management
│   │       ├── __init__.py
│   │       ├── transaction_manager.py  # Transaction management
│   │       ├── balance_monitor.py      # Balance monitoring
│   │       ├── payment_processor.py    # Payment processing
│   │       └── history_manager.py      # Transaction history
│   │
│   ├── 📁 sessions/                    # Session management
│   │   ├── __init__.py
│   │   ├── management/                 # Session management
│   │   │   ├── __init__.py
│   │   │   ├── session_manager.py      # Session management
│   │   │   └── storage_manager.py      # Storage management
│   │   ├── core/                       # Core session functionality
│   │   │   ├── __init__.py
│   │   │   ├── session_manager.py      # Session management
│   │   │   └── lifecycle.py            # Session lifecycle
│   │   ├── encryption/                 # Session encryption
│   │   │   ├── __init__.py
│   │   │   ├── key_exchange.py         # Key exchange
│   │   │   └── data_encryption.py      # Data encryption
│   │   ├── integration/                # Integration layer
│   │   │   ├── __init__.py
│   │   │   ├── blockchain_integration.py # Blockchain integration
│   │   │   └── rdp_integration.py      # RDP integration
│   │   ├── pipeline/                   # Processing pipeline
│   │   │   ├── __init__.py
│   │   │   ├── data_processor.py       # Data processing
│   │   │   └── event_handler.py        # Event handling
│   │   ├── processor/                  # Session processors
│   │   │   ├── __init__.py
│   │   │   ├── stream_processor.py     # Stream processing
│   │   │   └── command_processor.py    # Command processing
│   │   ├── recorder/                   # Session recording
│   │   │   ├── __init__.py
│   │   │   ├── session_recorder.py     # Session recording
│   │   │   └── playback.py             # Session playback
│   │   └── security/                   # Session security
│   │       ├── __init__.py
│   │       ├── access_control.py       # Access control
│   │       └── audit_logger.py         # Audit logging
│   │
│   ├── 📁 storage/                     # Storage management
│   │   ├── __init__.py
│   │   ├── mongo_sharding.py           # Chunks sharding on {session_id, idx}
│   │   ├── collections_manager.py      # sessions/chunks/payouts schemas management
│   │   ├── consensus_collections.py    # task_proofs/work_tally/leader_schedule collections
│   │   ├── database_adapter.py         # Database connection and adapter layer
│   │   ├── session_storage.py          # Session-specific storage operations
│   │   ├── chunk_storage.py            # Chunk storage and retrieval management
│   │   ├── backup_manager.py           # Database backup management
│   │   ├── encryption_manager.py       # Storage encryption management
│   │   ├── restore_manager.py          # Database restore operations
│   │   ├── backup_scheduler.py         # Automated backup scheduling
│   │   ├── persistence_manager.py      # Data persistence layer
│   │   ├── volume_manager.py           # Volume management and mounting
│   │   ├── data_migration.py           # Data migration utilities
│   │   ├── schema_manager.py           # Database schema management
│   │   ├── health_monitor.py           # Storage health monitoring
│   │   ├── performance_monitor.py      # Storage performance metrics
│   │   ├── capacity_monitor.py         # Storage capacity monitoring
│   │   ├── encryption_service.py       # Storage-level encryption
│   │   ├── access_control.py           # Storage access control
│   │   ├── audit_logger.py             # Storage audit logging
│   │   ├── cleanup_manager.py          # Storage cleanup utilities
│   │   ├── compression_manager.py      # Data compression management
│   │   ├── deduplication_manager.py    # Data deduplication
│   │   ├── cache_manager.py            # Storage caching layer
│   │   ├── test_mongo_service.py       # MongoDB service tests
│   │   ├── test_storage_operations.py  # Storage operation tests
│   │   ├── test_backup_restore.py      # Backup/restore tests
│   │   ├── config.py                   # Storage configuration management
│   │   └── constants.py                # Storage constants and enums
│   │
│   ├── 📁 database/                    # Database services
│   │   ├── __init__.py
│   │   ├── mongo_sharding.py           # Chunks sharding on {session_id, idx}
│   │   ├── collections_manager.py      # sessions/chunks/payouts schemas
│   │   ├── consensus_collections.py    # task_proofs/work_tally/leader_schedule
│   │   ├── services/                   # Database services
│   │   │   ├── __init__.py
│   │   │   ├── sharding/               # MongoDB sharding services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py             # MongoDB sharding service
│   │   │   │   ├── requirements-sharding.txt # Sharding service dependencies
│   │   │   │   ├── shard_manager.py    # Shard management
│   │   │   │   └── balancer.py         # Shard balancing
│   │   │   ├── collections/            # Collections management
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py             # Collections management service
│   │   │   │   ├── requirements-collections.txt # Collections service dependencies
│   │   │   │   ├── schema_manager.py   # Schema management
│   │   │   │   ├── validation.py       # Data validation
│   │   │   │   └── index_manager.py    # Index management
│   │   │   ├── consensus/              # Consensus collections
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py             # Consensus collections service
│   │   │   │   ├── requirements-consensus.txt # Consensus service dependencies
│   │   │   │   ├── task_proofs.py      # Task proofs management
│   │   │   │   ├── work_tally.py       # Work tally management
│   │   │   │   └── leader_schedule.py  # Leader schedule management
│   │   │   ├── backup/                 # Backup services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── backup_manager.py   # Backup management
│   │   │   │   └── restore_manager.py  # Restore management
│   │   │   ├── migration/              # Migration services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py             # Migration service implementation
│   │   │   │   ├── requirements-migration.txt # Migration service dependencies
│   │   │   │   ├── migration_manager.py # Migration management
│   │   │   │   ├── schema_migrator.py  # Schema migration
│   │   │   │   └── data_migrator.py    # Data migration
│   │   │   ├── restore/                # Restore services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py             # Restore service
│   │   │   │   ├── requirements-restore.txt # Restore service dependencies
│   │   │   │   └── restore_manager.py  # Restore management
│   │   │   ├── performance/            # Performance services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py             # Performance monitoring service
│   │   │   │   ├── requirements-performance.txt # Performance service dependencies
│   │   │   │   ├── query_optimizer.py  # Query optimization
│   │   │   │   └── index_optimizer.py  # Index optimization
│   │   │   └── monitoring/             # Monitoring services
│   │   │       ├── __init__.py
│   │   │       ├── health_checker.py   # Health monitoring
│   │   │       └── performance_monitor.py # Performance monitoring
│   │   ├── adapters/                   # Database adapters
│   │   │   ├── __init__.py
│   │   │   ├── session_adapter.py      # Session data adapter
│   │   │   ├── chunk_adapter.py        # Chunk data adapter
│   │   │   ├── payout_adapter.py       # Payout data adapter
│   │   │   ├── consensus_adapter.py    # Consensus data adapter
│   │   │   └── authentication_adapter.py # Authentication data adapter
│   │   ├── models/                     # Database models
│   │   │   ├── __init__.py
│   │   │   ├── session_model.py        # Session data model
│   │   │   ├── chunk_model.py          # Chunk data model
│   │   │   ├── payout_model.py         # Payout data model
│   │   │   ├── consensus_model.py      # Consensus data model
│   │   │   ├── authentication_model.py # Authentication data model
│   │   │   └── work_proof_model.py     # Work proof data model
│   │   ├── utils/                      # Database utilities
│   │   │   ├── __init__.py
│   │   │   ├── connection_manager.py   # Database connection management
│   │   │   ├── query_builder.py        # Query building utilities
│   │   │   ├── aggregation_pipeline.py # Aggregation pipeline utilities
│   │   │   ├── data_transformer.py     # Data transformation utilities
│   │   │   └── validation_utils.py     # Validation utilities
│   │   ├── scripts/                    # Database scripts
│   │   │   ├── __init__.py
│   │   │   ├── setup_mongo_sharding.sh # Configure sharding for chunks
│   │   │   ├── mongo_backup.sh         # S3-compatible encrypted backups
│   │   │   ├── mongo_restore.sh        # Disaster recovery
│   │   │   ├── mongo_replica_setup.sh  # Replica set setup
│   │   │   ├── mongo_health_check.sh   # MongoDB health checks
│   │   │   ├── mongo_cleanup.sh        # Database cleanup scripts
│   │   │   └── mongo_optimization.sh   # Database optimization scripts
│   │   ├── config/                     # Database configuration
│   │   │   ├── __init__.py
│   │   │   ├── database_config.py      # Database configuration
│   │   │   ├── sharding_config.py      # Sharding configuration
│   │   │   ├── collections_config.py   # Collections configuration
│   │   │   ├── consensus_config.py     # Consensus configuration
│   │   │   └── backup_config.py        # Backup configuration
│   │   ├── docs/                       # Database documentation
│   │   │   ├── __init__.py
│   │   │   ├── README.md               # Database documentation
│   │   │   ├── API.md                  # Database API documentation
│   │   │   ├── SCHEMA.md               # Database schema documentation
│   │   │   ├── SHARDING.md             # Sharding documentation
│   │   │   ├── BACKUP.md               # Backup procedures documentation
│   │   │   ├── MIGRATION.md            # Migration procedures documentation
│   │   │   ├── TESTING.md              # Database testing procedures
│   │   │   └── PERFORMANCE.md          # Performance testing documentation
│   │   ├── .env.database               # Database environment variables
│   │   ├── docker-compose.database.yml # Database Docker Compose
│   │   └── Dockerfile.database         # Database Dockerfile
│   │
│   ├── 📁 api/                         # API layer
│   │   ├── __init__.py
│   │   ├── routes/                     # API routes
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                 # Authentication routes
│   │   │   ├── blockchain.py           # Blockchain routes
│   │   │   ├── rdp.py                  # RDP routes
│   │   │   └── admin.py                # Admin routes
│   │   ├── schemas/                    # API schemas
│   │   │   ├── __init__.py
│   │   │   ├── requests.py             # Request schemas
│   │   │   └── responses.py            # Response schemas
│   │   ├── middleware/                 # API middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                 # Authentication middleware
│   │   │   ├── cors.py                 # CORS middleware
│   │   │   └── logging.py              # Logging middleware
│   │   └── services/                   # API services
│   │       ├── __init__.py
│   │       ├── blockchain_service.py   # Blockchain service
│   │       ├── rdp_service.py          # RDP service
│   │       └── admin_service.py        # Admin service
│   │
│   ├── 📁 vm/                          # Virtual Machine management
│   │   ├── __init__.py
│   │   ├── vm_orchestrator.py          # Main VM orchestration service
│   │   ├── vm_scheduler.py             # VM scheduling and lifecycle management
│   │   ├── vm_monitor.py               # VM health monitoring and metrics
│   │   ├── vm_config_manager.py        # VM configuration management
│   │   ├── vm_network_manager.py       # VM network configuration and management
│   │   ├── blockchain_vm_client.py     # Blockchain VM integration client
│   │   ├── contract_executor.py        # Smart contract execution in VM
│   │   ├── abi_manager.py              # ABI services for anchors/payout routers
│   │   ├── gas_budget_manager.py       # Gas/energy budgeting metrics
│   │   ├── tvm_executor.py             # TRON Virtual Machine (TVM) execution
│   │   ├── evm_executor.py             # Ethereum Virtual Machine (EVM) compatibility
│   │   ├── vm_provisioner.py           # VM provisioning and setup
│   │   ├── vm_destroyer.py             # VM cleanup and destruction
│   │   ├── vm_backup_manager.py        # VM backup and snapshot management
│   │   ├── vm_restore_manager.py       # VM restore from snapshots
│   │   ├── vm_migration_manager.py     # VM migration between hosts
│   │   ├── resource_manager.py         # VM resource allocation and monitoring
│   │   ├── capacity_manager.py         # VM capacity planning and scaling
│   │   ├── load_balancer.py            # VM load balancing
│   │   ├── auto_scaler.py              # VM auto-scaling based on demand
│   │   ├── vm_security_manager.py      # VM security policies and enforcement
│   │   ├── vm_isolation_manager.py     # VM isolation and sandboxing
│   │   ├── vm_access_control.py        # VM access control and permissions
│   │   ├── vm_audit_logger.py          # VM audit logging and compliance
│   │   ├── vm_network_config.py        # VM network configuration
│   │   ├── vm_dns_manager.py           # VM DNS management
│   │   ├── vm_firewall_manager.py      # VM firewall rules
│   │   ├── vm_port_manager.py          # VM port management and forwarding
│   │   ├── vm_storage_manager.py       # VM storage management
│   │   ├── vm_volume_manager.py        # VM volume management
│   │   ├── vm_snapshot_manager.py      # VM snapshot management
│   │   ├── vm_disk_manager.py          # VM disk management
│   │   ├── vm_metrics_collector.py     # VM metrics collection
│   │   ├── vm_health_checker.py        # VM health checks
│   │   ├── vm_performance_monitor.py   # VM performance monitoring
│   │   ├── vm_alert_manager.py         # VM alerting system
│   │   ├── vm_utils.py                 # VM utility functions
│   │   ├── vm_validator.py             # VM configuration validation
│   │   ├── vm_serializer.py            # VM data serialization
│   │   ├── vm_template_manager.py      # VM template management
│   │   ├── test_vm_manager.py          # VM manager tests
│   │   ├── test_vm_orchestrator.py     # VM orchestrator tests
│   │   ├── test_blockchain_vm.py       # Blockchain VM integration tests
│   │   ├── test_vm_lifecycle.py        # VM lifecycle tests
│   │   ├── docker_integration.py       # Docker container integration
│   │   ├── kubernetes_integration.py   # Kubernetes integration
│   │   ├── api_integration.py          # API integration for VM operations
│   │   ├── database_integration.py     # Database integration for VM metadata
│   │   ├── config.py                   # VM configuration constants
│   │   ├── constants.py                # VM constants and enums
│   │   ├── exceptions.py               # VM-specific exceptions
│   │   └── types.py                    # VM type definitions
│   │
│   └── 📁 common/                      # Common utilities
│       ├── __init__.py
│       ├── governance/                 # Common governance
│       │   ├── __init__.py
│       │   ├── policies.py             # Governance policies
│       │   └── compliance.py           # Compliance checks
│       ├── security/                   # Common security
│       │   ├── __init__.py
│       │   ├── crypto_utils.py         # Cryptographic utilities
│       │   └── security_utils.py       # Security utilities
│       ├── server_tools/               # Server utilities
│       │   ├── __init__.py
│       │   ├── system_monitor.py       # System monitoring
│       │   └── resource_manager.py     # Resource management
│       └── tor/                        # Common Tor utilities
│           ├── __init__.py
│           ├── tor_utils.py            # Tor utilities
│           └── onion_utils.py          # Onion utilities
│
├── 📁 infrastructure/                  # Infrastructure as Code
│   ├── docker/                         # Docker configurations
│   │   ├── compose/                    # Docker Compose files
│   │   │   ├── docker-compose.yml      # Main compose file
│   │   │   ├── docker-compose.dev.yml  # Development compose
│   │   │   ├── docker-compose.prod.yml # Production compose
│   │   │   └── docker-compose.pi.yml   # Raspberry Pi compose
│   │   ├── distroless/                 # Distroless configurations
│   │   │   ├── base/                   # Base distroless images
│   │   │   ├── gui/                    # GUI service distroless
│   │   │   ├── blockchain/             # Blockchain service distroless
│   │   │   ├── rdp/                    # RDP service distroless
│   │   │   └── node/                   # Node service distroless
│   │   └── multi-stage/                # Multi-stage builds
│   │       ├── Dockerfile.gui          # GUI service
│   │       ├── Dockerfile.blockchain   # Blockchain service
│   │       ├── Dockerfile.rdp          # RDP service
│   │       └── Dockerfile.node         # Node service
│   ├── kubernetes/                     # Kubernetes configurations
│   │   ├── namespaces/                 # Namespace definitions
│   │   ├── deployments/                # Deployment configurations
│   │   ├── services/                   # Service definitions
│   │   └── configmaps/                 # Configuration maps
│   └── terraform/                      # Terraform configurations
│       ├── modules/                    # Terraform modules
│       ├── environments/               # Environment-specific configs
│       └── variables/                  # Variable definitions
│
├── 📁 scripts/                         # Automation scripts
│   ├── build/                          # Build scripts
│   │   ├── distroless/                 # Distroless build scripts
│   │   │   ├── build-base.ps1          # Base image build
│   │   │   ├── build-services.ps1      # Service builds
│   │   │   └── optimize-images.ps1     # Image optimization
│   │   ├── components/                 # Component builds
│   │   │   ├── build-gui.ps1           # GUI build
│   │   │   ├── build-blockchain.ps1    # Blockchain build
│   │   │   └── build-rdp.ps1           # RDP build
│   │   └── utils/                      # Build utilities
│   │       ├── dependency-checker.py   # Dependency checking
│   │       └── layer-optimizer.py      # Layer optimization
│   ├── deployment/                     # Deployment scripts
│   │   ├── pi/                         # Raspberry Pi deployment
│   │   │   ├── deploy-to-pi.ps1        # Pi deployment script
│   │   │   ├── setup-pi.sh             # Pi setup script
│   │   │   └── health-check.sh         # Health checking
│   │   ├── devcontainer/               # Dev container scripts
│   │   │   ├── setup-devcontainer.ps1  # Dev container setup
│   │   │   └── sync-code.ps1           # Code synchronization
│   │   └── utils/                      # Deployment utilities
│   │       ├── ssh-helper.ps1          # SSH utilities
│   │       └── rsync-helper.ps1        # Rsync utilities
│   ├── testing/                        # Testing scripts
│   │   ├── unit/                       # Unit testing
│   │   │   ├── run-unit-tests.ps1      # Unit test runner
│   │   │   └── coverage-report.ps1     # Coverage reporting
│   │   ├── integration/                # Integration testing
│   │   │   ├── run-integration-tests.ps1 # Integration test runner
│   │   │   └── test-environment.ps1    # Test environment setup
│   │   └── utils/                      # Testing utilities
│   │       ├── test-data-generator.py  # Test data generation
│   │       └── mock-services.py        # Mock services
│   ├── maintenance/                    # Maintenance scripts
│   │   ├── cleanup/                    # Cleanup scripts
│   │   │   ├── cleanup-containers.ps1  # Container cleanup
│   │   │   └── cleanup-images.ps1      # Image cleanup
│   │   ├── optimization/               # Optimization scripts
│   │   │   ├── optimize-database.ps1   # Database optimization
│   │   │   └── optimize-storage.ps1    # Storage optimization
│   │   └── recovery/                   # Recovery scripts
│   │       ├── backup-recovery.ps1     # Backup recovery
│   │       └── disaster-recovery.ps1   # Disaster recovery
│   ├── network/                        # Network scripts
│   │   ├── diagnostics/                # Network diagnostics
│   │   │   ├── network-test.ps1        # Network testing
│   │   │   └── connectivity-check.ps1  # Connectivity checking
│   │   ├── security/                   # Network security
│   │   │   ├── firewall-setup.ps1      # Firewall configuration
│   │   │   └── ssl-setup.ps1           # SSL configuration
│   │   └── setup/                      # Network setup
│   │       ├── tor-setup.ps1           # Tor setup
│   │       └── onion-setup.ps1         # Onion service setup
│   └── compliance/                     # Compliance scripts
│       ├── distroless/                 # Distroless compliance
│       │   ├── security-scan.ps1       # Security scanning
│       │   └── vulnerability-check.ps1 # Vulnerability checking
│       └── general/                    # General compliance
│           ├── license-check.ps1       # License checking
│           └── audit-trail.ps1         # Audit trail generation
│
├── 📁 tests/                           # Test suites
│   ├── unit/                           # Unit tests
│   │   ├── core/                       # Core module tests
│   │   ├── gui/                        # GUI tests
│   │   ├── blockchain/                 # Blockchain tests
│   │   ├── rdp/                        # RDP tests
│   │   ├── node/                       # Node tests
│   │   ├── sessions/                   # Session tests
│   │   └── api/                        # API tests
│   ├── integration/                    # Integration tests
│   │   ├── end-to-end/                 # End-to-end tests
│   │   ├── api-integration/            # API integration tests
│   │   └── blockchain-integration/     # Blockchain integration tests
│   ├── performance/                    # Performance tests
│   │   ├── load-testing/               # Load testing
│   │   ├── stress-testing/             # Stress testing
│   │   └── benchmark/                  # Benchmarking
│   └── utils/                          # Test utilities
│       ├── fixtures/                   # Test fixtures
│       ├── mocks/                      # Mock objects
│       └── helpers/                    # Test helpers
│
├── 📁 configs/                         # Configuration files
│   ├── environment/                    # Environment configurations
│   │   ├── development/                # Development configs
│   │   ├── staging/                    # Staging configs
│   │   ├── production/                 # Production configs
│   │   └── pi/                         # Raspberry Pi configs
│   ├── docker/                         # Docker configurations
│   │   ├── distroless/                 # Distroless configs
│   │   └── multi-stage/                # Multi-stage configs
│   └── services/                       # Service configurations
│       ├── blockchain/                 # Blockchain service configs
│       ├── rdp/                        # RDP service configs
│       └── node/                       # Node service configs
│
├── 📁 docs/                            # Documentation
│   ├── api/                            # API documentation
│   │   ├── swagger/                    # Swagger/OpenAPI docs
│   │   ├── postman/                    # Postman collections
│   │   ├── session_api.md              # Session API documentation
│   │   ├── recording_api.md            # Recording API documentation
│   │   └── storage_api.md              # Storage API documentation
│   ├── architecture/                   # Architecture documentation
│   │   ├── system-design.md            # System design
│   │   ├── data-flow.md                # Data flow diagrams
│   │   └── security-model.md           # Security model
│   ├── deployment/                     # Deployment documentation
│   │   ├── distroless-builds.md        # Distroless build guide
│   │   ├── pi-deployment.md            # Raspberry Pi deployment
│   │   ├── docker-compose.md           # Docker Compose guide
│   │   ├── session_deployment.md       # Session deployment guide
│   │   ├── recording_deployment.md     # Recording deployment guide
│   │   └── storage_deployment.md       # Storage deployment guide
│   ├── development/                    # Development documentation
│   │   ├── setup-guide.md              # Development setup
│   │   ├── coding-standards.md         # Coding standards
│   │   └── testing-guide.md            # Testing guide
│   ├── implementation/                 # Implementation guides
│   │   ├── session_implementation.md   # Session implementation guide
│   │   ├── recording_implementation.md # Recording implementation guide
│   │   └── storage_implementation.md   # Storage implementation guide
│   ├── specs/                          # Specifications
│   │   ├── session_specification.md    # Detailed session specifications
│   │   ├── recording_specification.md  # Recording specifications
│   │   ├── storage_specification.md    # Storage specifications
│   │   └── encryption_specification.md # Encryption specifications
│   ├── testing/                        # Testing documentation
│   │   ├── session_testing.md          # Session testing procedures
│   │   ├── recording_testing.md        # Recording testing procedures
│   │   └── storage_testing.md          # Storage testing procedures
│   └── user/                           # User documentation
│       ├── user-guide.md               # User guide
│       ├── admin-guide.md              # Admin guide
│       └── troubleshooting.md          # Troubleshooting guide
│
├── 📁 tools/                           # Development tools
│   ├── build/                          # Build tools
│   │   ├── dependency-manager.py       # Dependency management
│   │   ├── version-bumper.py           # Version bumping
│   │   └── release-manager.py          # Release management
│   ├── ops/                            # Operations tools
│   │   ├── backup/                     # Backup tools
│   │   │   ├── backup-manager.py       # Backup management
│   │   │   └── restore-manager.py      # Restore management
│   │   ├── monitoring/                 # Monitoring tools
│   │   │   ├── health-checker.py       # Health monitoring
│   │   │   └── performance-monitor.py  # Performance monitoring
│   │   └── ota/                        # Over-the-air updates
│   │       ├── update-manager.py       # Update management
│   │       └── rollback-manager.py     # Rollback management
│   └── dev/                            # Development tools
│       ├── code-generator.py           # Code generation
│       ├── template-manager.py         # Template management
│       └── migration-helper.py         # Migration assistance
│
├── 📁 storage/                         # Persistent storage
│   ├── data/                           # Application data
│   │   ├── blockchain/                 # Blockchain data
│   │   ├── sessions/                   # Session data
│   │   └── logs/                       # Log files
│   ├── backups/                        # Backup storage
│   │   ├── database/                   # Database backups
│   │   ├── configs/                    # Configuration backups
│   │   └── user-data/                  # User data backups
│   └── cache/                          # Cache storage
│       ├── docker/                     # Docker cache
│       ├── build/                      # Build cache
│       └── temp/                       # Temporary files
│
├── 📁 reports/                         # Reports and analytics
│   ├── build/                          # Build reports
│   │   ├── logs/                       # Build logs
│   │   └── progress/                   # Build progress
│   ├── testing/                        # Test reports
│   │   ├── coverage/                   # Coverage reports
│   │   └── results/                    # Test results
│   └── monitoring/                     # Monitoring reports
│       ├── performance/                # Performance reports
│       └── security/                   # Security reports
│
├── 📁 .env.example                     # Environment variables template
├── 📁 .gitignore                       # Git ignore rules
├── 📁 .dockerignore                    # Docker ignore rules
├── 📁 docker-compose.yml               # Main Docker Compose file
├── 📁 docker-compose.dev.yml           # Development Docker Compose
├── 📁 docker-compose.pi.yml            # Raspberry Pi Docker Compose
├── 📁 pyproject.toml                   # Python project configuration
├── 📁 requirements.txt                 # Python dependencies
├── 📁 requirements-dev.txt             # Development dependencies
├── 📁 requirements-pi.txt              # Raspberry Pi dependencies
├── 📁 README.md                        # Project README
├── 📁 LICENSE                          # Project license
└── 📁 CHANGELOG.md                     # Change log
```

## GUI Architecture Overview

### Comprehensive GUI Structure
The GUI system is designed as a modular, multi-interface application with the following key components:

#### Entry Points and Launchers
- **main.py**: Platform-aware launcher with automatic interface detection
- **user_main.py**: User interface entry point with session management
- **admin_main.py**: Administrative interface with full system control
- **node_main.py**: Node worker interface for distributed operations

#### Interface Modules
- **Admin Interface**: Bootstrap wizard, backup/restore, diagnostics, key management, payouts
- **Node Interface**: Metrics dashboard, wallet monitoring, payout batches, alerts management
- **User Interface**: Session management and user-specific operations
- **Shared Components**: Connection parameters, consent management, QR scanning, file pickers, notifications, encryption

#### Configuration and Resources
- **Configuration**: Default settings, Tor templates, theme definitions
- **Resources**: Icons, fonts, terms of service documents
- **Build System**: PyInstaller specs, Tor vendor management, code signing, installer creation

#### Testing and Documentation
- **Testing**: Comprehensive test suite for core, user, admin, node, and integration testing
- **Documentation**: User guides, admin guides, node guides, development guidelines

### Key Features
1. **Modular Design**: Each interface can be built and deployed independently
2. **Shared Components**: Common functionality centralized for consistency
3. **Security Integration**: Local encryption, consent management, secure file operations
4. **Build Automation**: Complete build pipeline with signing and installer creation
5. **Comprehensive Testing**: Full test coverage across all GUI components
6. **Resource Management**: Centralized icons, fonts, and documentation

## Distroless Build Strategy

### Multi-Stage Build Approach
1. **Base Stage**: Common dependencies and utilities
2. **Build Stage**: Application compilation and packaging
3. **Runtime Stage**: Minimal distroless runtime environment

### Service-Specific Distroless Images
- **GUI Service**: Tkinter-based admin, user, and node interfaces with comprehensive shared components, build system, and testing framework
- **User Management Service**: Authentication, profile management, permissions, role-based access control, session ownership, activity logging, and hardware wallet integration
- **User Content Service**: Client components, GUI components, wallet management, API client, configuration management, notifications, backup, and security management
- **Session Management Service**: Core session functionality, encryption, pipeline processing, recording, management layer, and storage management
- **Storage Service**: MongoDB sharding, collections management, consensus collections, database adapter, session storage, chunk storage, backup/recovery, data persistence, monitoring, security, utilities, and testing
- **Database Service**: Comprehensive MongoDB integration, sharding services, collections management, consensus collections, database adapters, models, utilities, scripts, configuration, and documentation
- **VM Management Service**: Orchestration, scheduling, monitoring, configuration, blockchain integration, lifecycle management, resource management, security, networking, storage, performance monitoring, testing, and integration
- **Blockchain Service**: TRON integration and payment processing
- **RDP Service**: Remote desktop protocol implementation with comprehensive audit trail, resource monitoring, hardware acceleration, and security controls
- **Node Service**: Distributed node management and consensus

### Build Optimization
- **Layer Caching**: Optimized layer ordering for maximum cache hits
- **Multi-Architecture**: ARM64 support for Raspberry Pi deployment
- **Security Scanning**: Automated vulnerability scanning
- **Size Optimization**: Minimal attack surface and image size

## Deployment Strategy

### Development Environment
- **Windows 11**: Primary development platform
- **Docker Desktop**: Container runtime
- **VS Code**: Development environment with dev containers

### Production Environment
- **Raspberry Pi**: Target deployment platform
- **SSH Deployment**: Automated deployment via SSH
- **Health Monitoring**: Continuous health checks and monitoring

### CI/CD Pipeline
- **GitHub Actions**: Automated builds and testing
- **Multi-Stage Builds**: Optimized distroless image creation
- **Automated Deployment**: Push-to-deploy for Raspberry Pi

## Key Benefits of This Structure

1. **Modularity**: Clear separation of concerns with dedicated modules
2. **Scalability**: Easy to add new services and components
3. **Maintainability**: Well-organized code structure for easy maintenance
4. **Security**: Distroless builds minimize attack surface
5. **Performance**: Optimized builds and deployment strategies
6. **Cross-Platform**: Support for Windows development and Pi production
7. **Automation**: Comprehensive build and deployment automation
8. **Documentation**: Extensive documentation for all components
9. **Testing**: Comprehensive test coverage at all levels
10. **Compliance**: Built-in compliance and security scanning

## Migration Strategy

### Phase 1: Core Restructuring
- Reorganize existing modules into new structure
- Update import paths and dependencies
- Implement new build system

### Phase 2: Distroless Implementation
- Create distroless base images
- Implement multi-stage builds
- Optimize layer caching

### Phase 3: Deployment Automation
- Implement CI/CD pipeline
- Create deployment scripts
- Set up monitoring and health checks

### Phase 4: Testing and Validation
- Comprehensive testing suite
- Performance benchmarking
- Security validation

This structure provides a solid foundation for the Lucid project's continued development and deployment, with particular emphasis on distroless builds for enhanced security and minimal resource usage on Raspberry Pi deployments.
