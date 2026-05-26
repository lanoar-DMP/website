.PHONY: up down logs db-reset psql build

up:      ## Start all services in detached mode
	docker compose up -d

down:    ## Stop and remove all containers
	docker compose down

logs:    ## Tail logs from all services
	docker compose logs -f

db-reset: ## Destroy volumes and recreate all containers
	docker compose down -v && docker compose up -d

psql:    ## Open a psql shell inside the db-core container
	docker compose exec db-core psql -U holyterminal -d holyterminal

build:   ## Build (or rebuild) all service images
	docker compose build
