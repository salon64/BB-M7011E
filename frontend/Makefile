.PHONY: help install run docker-build docker-run docker-push k8s-deploy k8s-delete clean test lint

# Variables
IMAGE_NAME ?= barcode-buddy-frontend
IMAGE_TAG ?= latest
REGISTRY ?= your-registry
NAMESPACE ?= barcode-buddy

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python dependencies
	pip install -r requirements.txt

run: ## Run development server
	python app.py

run-prod: ## Run with Gunicorn
	gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app

docker-build: ## Build Docker image
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

docker-run: ## Run Docker container
	docker run -d \
		--name $(IMAGE_NAME) \
		-p 5000:5000 \
		--env-file .env \
		$(IMAGE_NAME):$(IMAGE_TAG)

docker-stop: ## Stop Docker container
	docker stop $(IMAGE_NAME) || true
	docker rm $(IMAGE_NAME) || true

docker-push: ## Push image to registry
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

docker-logs: ## View Docker container logs
	docker logs -f $(IMAGE_NAME)

compose-up: ## Start with docker-compose
	docker-compose up -d

compose-down: ## Stop docker-compose
	docker-compose down

compose-logs: ## View docker-compose logs
	docker-compose logs -f

k8s-secret: ## Generate Kubernetes secret
	@python -c "import secrets; print('Generated secret key:', secrets.token_hex(32))"
	@echo "Update k8s/secrets.yaml with the generated key"

k8s-deploy: ## Deploy to Kubernetes
	kubectl create namespace $(NAMESPACE) || true
	kubectl apply -f k8s/secrets.yaml -n $(NAMESPACE)
	kubectl apply -f k8s/configmap.yaml -n $(NAMESPACE)
	kubectl apply -f k8s/deployment.yaml -n $(NAMESPACE)
	kubectl apply -f k8s/ingress.yaml -n $(NAMESPACE)

k8s-delete: ## Delete from Kubernetes
	kubectl delete -f k8s/ -n $(NAMESPACE) || true

k8s-status: ## Check Kubernetes deployment status
	kubectl get all -n $(NAMESPACE)

k8s-logs: ## View Kubernetes logs
	kubectl logs -f -l app=barcode-buddy-frontend -n $(NAMESPACE)

k8s-describe: ## Describe Kubernetes pods
	kubectl describe pods -l app=barcode-buddy-frontend -n $(NAMESPACE)

k8s-restart: ## Restart Kubernetes deployment
	kubectl rollout restart deployment/barcode-buddy-frontend -n $(NAMESPACE)

k8s-port-forward: ## Port forward to local machine
	kubectl port-forward -n $(NAMESPACE) service/barcode-buddy-frontend 5000:80

clean: ## Clean up temporary files
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete || true
	find . -type f -name "*.pyo" -delete || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + || true

lint: ## Run linting
	@echo "Install flake8 first: pip install flake8"
	flake8 app.py --max-line-length=120 || true

format: ## Format code
	@echo "Install black first: pip install black"
	black app.py || true

test: ## Run tests (placeholder)
	@echo "No tests configured yet"

dev-setup: ## Setup development environment
	cp .env.example .env
	@echo "Edit .env file with your configuration"
	make install

full-deploy: docker-build docker-push k8s-deploy ## Build, push and deploy

health-check: ## Check if application is healthy
	@curl -f http://localhost:5000/health || echo "Health check failed"
