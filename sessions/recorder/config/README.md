# Session Recorder Configuration

## Environment Variables Template

This directory contains the environment variables template for the session-recorder container.

### Usage

1. **Copy the template file to the environment configuration directory:**
   ```bash
   cp sessions/recorder/config/env.session-recorder.template configs/environment/.env.session-recorder
   ```

2. **Customize the values in `.env.session-recorder`:**
   - Replace `{MONGODB_PASSWORD}` and `{REDIS_PASSWORD}` placeholders with actual values from `.env.secrets`
   - Adjust recording settings (codec, bitrate, fps) based on your hardware capabilities
   - Configure chunk size and compression level based on network/storage constraints
   - Update service URLs if your service names differ

3. **The docker-compose file will automatically load this file:**
   The `docker-compose.application.yml` includes `.env.session-recorder` in the `env_file` list for the session-recorder service.

### Key Configuration Areas

- **Service Settings**: Host, port, and URL configuration
- **Recording Configuration**: Storage paths and video/audio settings
- **FFmpeg Configuration**: Codec selection and hardware acceleration (Pi 5 V4L2)
- **Chunk Configuration**: Size and compression settings for pipeline processing
- **Monitoring**: Window focus, keystroke, and resource monitoring settings
- **Integration Services**: URLs for dependent services (pipeline, storage, blockchain, etc.)
- **Security**: JWT secret key for service authentication

### Notes

- All service URLs must use Docker service names (not `localhost`) for proper networking
- Hardware acceleration (`LUCID_HARDWARE_ACCELERATION=true`) requires Pi 5 with V4L2 support
- Chunk size (default: 10MB) should be adjusted based on network bandwidth (recommended: 8-16MB)
- Monitor log paths should match volume mounts in docker-compose

