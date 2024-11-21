# RD-Sync

RD-Sync is a tool to synchronize torrents between multiple Real-Debrid accounts. It supports scheduled syncing using either interval-based or cron-based schedules.

## Features

- Sync torrents between Real-Debrid accounts
- Support for multiple sync jobs
- Flexible scheduling (interval or cron-based)
- Docker support
- Detailed logging
- Rate limiting to respect Real-Debrid API limits

## Quick Start with Docker

### 1. Create Configuration

Create a `config` directory and add a `config.yaml` file:

```bash
mkdir -p config logs
touch config/config.yaml
```

### 2. Configure Settings

Edit `config/config.yaml` with your Real-Debrid accounts and sync jobs:

```yaml
# API Settings (optional - using defaults)
api:
  base_url: "https://api.real-debrid.com/rest/1.0"
  rate_limit_per_minute: 250
  torrents_rate_limit_per_minute: 75
  timeout_secs: 60
  fetch_torrents_page_size: 2000
  disable_httpx_logging: true

# Logging Settings (optional - using defaults)
log:
  level: "INFO"
  filename: "rd-sync.log"
  jobs_dir: "jobs"

# Real-Debrid Accounts
accounts:
  account1:
    token: "YOUR_FIRST_RD_API_TOKEN"
    description: "Primary Account"
  account2:
    token: "YOUR_SECOND_RD_API_TOKEN"
    description: "Secondary Account"

# Sync Jobs
syncs:
  daily_sync:
    source: "account1"
    destination: "account2"
    schedule:
      type: "cron"
      value: "0 4 * * *"  # Runs at 4 AM daily
    enabled: true

  rapid_sync:
    source: "account2"
    destination: "account1"
    schedule:
      type: "interval"
      value: 3600  # Runs every hour (3600 seconds)
    enabled: true
```

### 3. Create Docker Compose File

Create a `docker-compose.yaml` file:

```yaml
services:
  rd-sync:
    image: ghcr.io/maulik9898/rd-sync:main
    container_name: rd-sync
    restart: unless-stopped
    volumes:
      - ./config:/config:ro  # Mount config directory
      - ./logs:/logs        # Mount logs directory
    environment:
      - TZ=UTC
      - CONFIG_PATH=/config/config.yaml

```

### 4. Deploy with Docker Compose

Start the service:

```bash
docker-compose up -d
```

View logs:

```bash
docker-compose logs -f
```

Stop the service:

```bash
docker-compose down
```

## Configuration Details

### Account Configuration

- `token`: Your Real-Debrid API token (required)
- `description`: Optional description for the account

### Sync Job Configuration

- `source`: Source account name (must match an account in the accounts section)
- `destination`: Destination account name (must match an account in the accounts section)
- `schedule`: Defines when the sync should run
  - `type`: Either "interval" or "cron"
  - `value`:
    - For interval: Number of seconds between runs
    - For cron: Standard cron expression (e.g., "0 4 * * *" for 4 AM daily)
- `enabled`: Boolean to enable/disable the sync job

## Environment Variables


- `TZ`: Timezone (default: UTC)


## Troubleshooting

1. Check container logs:
   ```bash
   docker-compose logs -f rd-sync
   ```

2. Verify config file permissions:
   ```bash
   ls -l config/config.yaml
   ```

## Support

For issues and feature requests, please create an issue on the GitHub repository.
