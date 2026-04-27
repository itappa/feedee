# -------------------------------------------------------------------
# Variables
# -------------------------------------------------------------------
COMPOSE            := docker compose
COMPOSE_STANDALONE := docker compose --env-file .env -f compose.standalone.yaml
COMPOSE_INFRA      := docker compose -f compose.infra.yaml
TIMESTAMP          := $(shell date +%Y%m%d_%H%M%S)
BACKUP_DIR         := backups

.PHONY: help \
        dev up down logs build test migrate shell worker \
        standalone-check-env standalone-up standalone-down standalone-logs standalone-build standalone-migrate standalone-shell \
        infra-up infra-up-build infra-down \
        backup backup-dev backup-prod restore-dev restore-prod list-backups \
        lint fmt clean superuser collectstatic \
        fe-install fe-dev fe-build

.DEFAULT_GOAL := help

# -------------------------------------------------------------------
# Help
# -------------------------------------------------------------------
help: ## Show this help
	@echo ""
	@echo "Usage: make <target>"
	@awk 'BEGIN {FS = ":.*?## "} \
	    /^#  [A-Z]/ { \
	        label = substr($$0, 4); \
	        printf "\n\033[1m%s\033[0m\n", label; next \
	    } \
	    /^[a-zA-Z_-]+:.*## / { \
	        printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 \
	    }' $(MAKEFILE_LIST)
	@echo ""

# ===================================================================
#  Development
# ===================================================================
dev: ## Start dev environment (foreground)
	$(COMPOSE) up --build

up: ## Start dev environment (background)
	$(COMPOSE) up --build -d

down: ## Stop dev environment
	$(COMPOSE) down

logs: ## Tail dev logs
	$(COMPOSE) logs -f

build: ## Build dev images
	$(COMPOSE) build

test: ## Run Django tests
	uv run python manage.py test apps.rssapp

migrate: ## Run Django migrations (local)
	uv run python manage.py migrate

shell: ## Open Django shell (local)
	uv run python manage.py shell

worker: ## Run RSS worker locally
	go run rss_worker/main.go

# ===================================================================
#  Production (standalone)
# ===================================================================
standalone-check-env:
	@if [ ! -f .env ]; then \
		echo "Missing .env. Run: cp .env.example .env"; \
		exit 1; \
	fi
	@for key in POSTGRES_PASSWORD WORKER_API_TOKEN; do \
		if ! grep -Eq "^$$key=.+" .env; then \
			echo "$$key is missing or empty in .env. See .env.example."; \
			exit 1; \
		fi; \
	done

standalone-up: standalone-check-env ## Start standalone production environment
	$(COMPOSE_STANDALONE) up --build -d --wait

standalone-down: ## Stop standalone production environment
	@POSTGRES_PASSWORD=$${POSTGRES_PASSWORD:-dummy} WORKER_API_TOKEN=$${WORKER_API_TOKEN:-dummy} $(COMPOSE_STANDALONE) down

standalone-logs: ## Tail standalone production logs
	@POSTGRES_PASSWORD=$${POSTGRES_PASSWORD:-dummy} WORKER_API_TOKEN=$${WORKER_API_TOKEN:-dummy} $(COMPOSE_STANDALONE) logs -f

standalone-build: standalone-check-env ## Build standalone production images
	$(COMPOSE_STANDALONE) build

standalone-migrate: standalone-check-env ## Run migrations in standalone production
	$(COMPOSE_STANDALONE) exec web python manage.py migrate --noinput

standalone-shell: standalone-check-env ## Open Django shell in standalone production
	$(COMPOSE_STANDALONE) exec web python manage.py shell

# ===================================================================
#  Production (shared infra)
# ===================================================================
infra-up: ## Start production environment connected to shared infra
	$(COMPOSE_INFRA) up -d --wait

infra-up-build: ## Build and start production environment connected to shared infra
	$(COMPOSE_INFRA) up -d --build --wait

infra-down: ## Stop shared-infra production environment
	$(COMPOSE_INFRA) down

# ===================================================================
#  Backup
# ===================================================================
backup-dev: ## Backup dev SQLite database
	@mkdir -p $(BACKUP_DIR)/dev
	cp db.sqlite3 $(BACKUP_DIR)/dev/db_$(TIMESTAMP).sqlite3
	@echo "✓ Dev backup: $(BACKUP_DIR)/dev/db_$(TIMESTAMP).sqlite3"

backup-prod: standalone-check-env ## Backup production PostgreSQL database
	@mkdir -p $(BACKUP_DIR)/prod
	$(COMPOSE_STANDALONE) exec -T db pg_dump \
		-U $${POSTGRES_USER:-feedee} \
		-d $${POSTGRES_DB:-feedee} \
		--clean --if-exists \
		| gzip > $(BACKUP_DIR)/prod/db_$(TIMESTAMP).sql.gz
	@echo "✓ Prod backup: $(BACKUP_DIR)/prod/db_$(TIMESTAMP).sql.gz"

backup: backup-dev ## Backup dev database (alias for backup-dev)

restore-dev: ## Restore dev SQLite (usage: make restore-dev FILE=backups/dev/db_xxx.sqlite3)
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore-dev FILE=backups/dev/db_xxx.sqlite3"; \
		echo "Available backups:"; ls -1t $(BACKUP_DIR)/dev/ 2>/dev/null || echo "  (none)"; \
		exit 1; \
	fi
	cp $(FILE) db.sqlite3
	@echo "✓ Restored from $(FILE)"

restore-prod: standalone-check-env ## Restore production PostgreSQL (usage: make restore-prod FILE=backups/prod/db_xxx.sql.gz)
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore-prod FILE=backups/prod/db_xxx.sql.gz"; \
		echo "Available backups:"; ls -1t $(BACKUP_DIR)/prod/ 2>/dev/null || echo "  (none)"; \
		exit 1; \
	fi
	gunzip -c $(FILE) | $(COMPOSE_STANDALONE) exec -T db psql \
		-U $${POSTGRES_USER:-feedee} \
		-d $${POSTGRES_DB:-feedee}
	@echo "✓ Restored from $(FILE)"

list-backups: ## List all backups
	@echo "=== Dev backups ==="
	@ls -1t $(BACKUP_DIR)/dev/ 2>/dev/null || echo "  (none)"
	@echo ""
	@echo "=== Prod backups ==="
	@ls -1t $(BACKUP_DIR)/prod/ 2>/dev/null || echo "  (none)"

# ===================================================================
#  Frontend (Vite + Tailwind)
# ===================================================================
fe-install: ## Install frontend dependencies
	npm install

fe-dev: ## Start Vite dev server (HMR)
	npm run dev

fe-build: ## Build frontend for production
	npm run build

# ===================================================================
#  Utilities
# ===================================================================
lint: ## Run linters (ruff)
	uv run ruff check .

fmt: ## Format code (ruff)
	uv run ruff format .

clean: ## Remove Python cache and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.py[co]' -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info

superuser: ## Create Django superuser (local)
	uv run python manage.py createsuperuser

collectstatic: ## Collect static files (local)
	uv run python manage.py collectstatic --noinput
