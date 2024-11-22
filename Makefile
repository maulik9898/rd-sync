.PHONY: build-dev run-dev logs-dev stop-dev clean-dev

build-dev:
	docker compose -f docker-compose.dev.yml build

run-dev:
	docker compose -f docker-compose.dev.yml up -d

logs-dev:
	docker compose -f docker-compose.dev.yml logs -f --no-log-prefix

stop-dev:
	docker compose -f docker-compose.dev.yml down

clean-dev:
	docker compose -f docker-compose.dev.yml down -v
	docker rmi rd-sync:local

# Run all development commands in sequence
dev: build-dev run-dev logs-dev
