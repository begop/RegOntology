.DEFAULT_GOAL := help

ENV_FILE ?= .env.local
DEV_SCRIPT := pwsh -NoProfile -File ./scripts/dev.ps1 -EnvFile $(ENV_FILE)

.PHONY: help bootstrap up down restart build test status logs config health

help:
	@echo "RegOntology local commands"
	@echo "  make bootstrap  Create .env.local, build, start, and wait for health"
	@echo "  make up         Build and start the stack"
	@echo "  make down       Stop containers without deleting data volumes"
	@echo "  make test       Build backend/frontend test targets"
	@echo "  make logs       Show the latest container logs"
	@echo "  make config     Validate the Compose configuration"

bootstrap:
	$(DEV_SCRIPT) -Command bootstrap

up:
	$(DEV_SCRIPT) -Command up

down:
	$(DEV_SCRIPT) -Command down

restart:
	$(DEV_SCRIPT) -Command restart

build:
	$(DEV_SCRIPT) -Command build

test:
	$(DEV_SCRIPT) -Command test

status:
	$(DEV_SCRIPT) -Command status

logs:
	$(DEV_SCRIPT) -Command logs

config:
	$(DEV_SCRIPT) -Command config

health:
	$(DEV_SCRIPT) -Command health
