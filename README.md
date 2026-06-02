# CEBD 1261 — Session 08 | Lab Code
## Cloud Deployment with GitHub Actions & Azure ACI

**Instructor:** Mohammed A. Shehab | Concordia University CCE | Spring 2026

---

## What This Project Does

This is the complete Session 08 solution — the Session 07 LLM Agent stack deployed to Azure using GitHub Actions CI/CD. Every `git push` to `main` automatically builds Docker images, pushes them to Docker Hub, and deploys all 5 containers to Azure Container Instances (ACI).

**Live URL after deployment:**
```
Chat UI : http://cebd1261-app.eastus.azurecontainer.io
API Docs: http://cebd1261-app.eastus.azurecontainer.io:8893/docs
```
testing 1-2
---

## Project Structure

```
Session_08_Sol_Online/
│
├── .github/
│   └── workflows/
│       └── deploy.yml          ← CI/CD pipeline (GitHub Actions)
│
├── agent/                      ← FastAPI LLM agent backend
│   ├── agents/
│   │   ├── orchestrator_agent.py
│   │   ├── mongo_agent.py
│   │   ├── elastic_agent.py
│   │   ├── base_agent.py
│   │   └── utils.py
│   ├── prompts/
│   │   ├── orchestrator.md
│   │   ├── mongo.md
│   │   ├── elastic.md
│   │   └── chat.md
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile              ← Standard single-stage build
│   └── Dockerfile.multistage  ← Optimized multi-stage build (see below)
│
├── seeder/                     ← Data generation — runs once on deploy
│   ├── data_producer/
│   │   ├── adapters/
│   │   │   └── faker_adapter.py
│   │   └── schemas/
│   │       ├── base.py
│   │       └── ecommerce.py
│   ├── seed.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── ui/                         ← Chat frontend (nginx + Vue.js)
│   ├── chat.html
│   ├── nginx.conf
│   └── Dockerfile
│
├── terraform/                  ← Take-home assignment (see terraform/README.md)
│   ├── main.tf
│   ├── outputs.tf
│   └── README.md
│
├── aci-group.yml               ← Azure Container Group definition (5 containers)
├── docker-compose.yml          ← Local development
├── .env                        ← Local environment variables (never commit)
└── .gitignore
```

---

## Folder Explanations

### `.github/workflows/deploy.yml`
The GitHub Actions pipeline. Triggered automatically on every push to `main`.

**Job 1 — build-and-push:**
- Logs into Docker Hub using secrets
- Builds 3 Docker images: `seeder`, `agent_api`, `chat_ui`
- Pushes all 3 to Docker Hub

**Job 2 — deploy** (runs after Job 1):
- Logs into Azure using a Service Principal
- Injects GitHub Secrets into `aci-group.yml` placeholders
- Deletes the old Container Group (ACI requires full recreate on update)
- Deploys the new Container Group from `aci-group.yml`
- Prints the public URL

---

### `agent/`
The FastAPI backend. Receives chat messages from the UI, routes them to the correct specialist agent, and returns a response.

| File | Purpose |
|---|---|
| `main.py` | FastAPI app — exposes `/chat`, `/health`, `/stats` endpoints |
| `agents/orchestrator_agent.py` | Classifies intent using OpenRouter LLM → routes to mongo or elastic agent |
| `agents/mongo_agent.py` | Handles structured queries against MongoDB |
| `agents/elastic_agent.py` | Handles full-text search against ElasticSearch |
| `agents/base_agent.py` | Shared base class for all agents |
| `prompts/*.md` | System prompts — instructions for each agent |
| `Dockerfile` | Standard single-stage build using `python:3.11-slim` |
| `Dockerfile.multistage` | Optimized build — see Docker Image Optimization section below |

**Runs on:** port `8893`
**API docs:** `http://localhost:8893/docs`

---

### `seeder/`
Generates 10,000 synthetic ecommerce orders and inserts them into both MongoDB and ElasticSearch. Runs **once** on deploy then exits.

| File | Purpose |
|---|---|
| `seed.py` | Main script — waits for services, checks existing counts, generates and inserts data |
| `data_producer/adapters/faker_adapter.py` | Uses the Faker library to generate realistic order records |
| `data_producer/schemas/ecommerce.py` | Defines the order schema — fields, types, value ranges |

**ACI startup note:** Docker Compose uses `depends_on` + `healthcheck` to hold the seeder until MongoDB and ElasticSearch are ready. ACI starts all containers simultaneously. `seed.py` includes a retry loop (`wait_for_services()`) that polls both services every 5 seconds for up to 3 minutes before seeding begins.

---

### `ui/`
The chat frontend — a single HTML file served by nginx.

| File | Purpose |
|---|---|
| `chat.html` | Vue.js chat interface — sends messages to `/api/chat`, renders responses and charts |
| `nginx.conf` | Reverse proxy config — proxies `/api/` requests to `agent_api` on `localhost:8893` |
| `Dockerfile` | Bakes `chat.html` and `nginx.conf` into an `nginx:alpine` image |

**Why a Dockerfile for the UI?**
In Session 07 (local), `chat.html` was mounted as a volume. ACI Container Groups do not support host volume mounts — files must be baked into the image at build time.

**Runs on:** port `80` (public)

---

### `terraform/`
Take-home assignment — see `terraform/README.md` for full instructions.

Demonstrates Infrastructure as Code by replacing the manual `az` CLI setup commands with declarative Terraform files.

| File | Purpose |
|---|---|
| `main.tf` | Declares the Resource Group, Service Principal, and role assignment |
| `outputs.tf` | Prints the values needed for GitHub Secrets after `terraform apply` |

| Manual CLI command | Terraform resource |
|---|---|
| `az group create` | `azurerm_resource_group` |
| `az ad sp create-for-rbac` | `azuread_application` + `azuread_service_principal` |
| `az role assignment create` | `azurerm_role_assignment` |

---

### `aci-group.yml`
Defines all 5 containers as a single Azure Container Instance Group. Deployed by GitHub Actions with `az container create --file aci-group.yml`.

**Key concepts:**
- All 5 containers share **one public IP address** and communicate via `localhost`
- This is different from local Docker Compose where containers use **service names** (e.g. `mongodb`, `elasticsearch`)
- `__PLACEHOLDERS__` are replaced by GitHub Actions at deploy time using `sed` — secrets never appear in the file

| Container | Image | Port | Purpose |
|---|---|---|---|
| `mongodb` | `mongo:latest` | 27017 | Document store |
| `elasticsearch` | `docker.elastic.co/elasticsearch/elasticsearch:8.13.0` | 9200 | Full-text search |
| `seeder` | Docker Hub | — | Data generation (runs once) |
| `agent-api` | Docker Hub | 8893 | FastAPI backend |
| `chat-ui` | Docker Hub | 80 | nginx frontend |

---

### `docker-compose.yml`
For local development only — not used in Azure deployment.

Key differences from `aci-group.yml`:

| | docker-compose.yml | aci-group.yml |
|---|---|---|
| Networking | Bridge network — containers use service names | Shared localhost — containers use `localhost` |
| MongoDB URI | `mongodb://...@mongodb:27017/...` | `mongodb://localhost:27017/...` |
| ES URL | `http://elasticsearch:9200` | `http://localhost:9200` |
| Startup order | `depends_on` + `healthcheck` | Retry loop in `seed.py` |
| Volume mounts | Supported | Not supported — files baked into images |

---

## Docker Image Optimization

### Removing unused dependencies (seeder)
`seeder/requirements.txt` originally included `pandas`, `pyarrow`, and `numpy` — leftover from Sessions 4-5 (HDFS Parquet pipeline). These packages are **not used** in Session 08. Removing them reduces the seeder image size by ~250 MB.

### Multi-stage build (agent)
`agent/Dockerfile.multistage` demonstrates a multi-stage build:

**Stage 1 (builder):** installs all dependencies — heavy, includes build tools and pip cache.
**Stage 2 (runtime):** clean `python:3.11-slim` with only the installed packages copied from Stage 1. No pip, no build artifacts.

To test:
```bash
cd agent
docker build -f Dockerfile.multistage -t agent-api-multistage:test .
docker images | grep agent-api    # compare sizes
```

To use in docker-compose.yml, replace the `build:` block:
```yaml
agent_api:
  # Option 1 — Standard build
  # build: ./agent

  # Option 2 — Multi-stage (optimized)
  build:
    context: ./agent
    dockerfile: Dockerfile.multistage
```

---

## Running Locally

```bash
# 1. Copy .env and add your OpenRouter API key
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Watch the seeder (wait until it prints Done)
docker-compose logs -f seeder

# 4. Open the chat UI
# http://localhost:8080

# 5. API docs
# http://localhost:8893/docs
```

---

## Deploying to Azure

See the lab guide (`Session_08_Lab_Guide.docx`) for full step-by-step instructions.

**Quick summary:**
1. Create a personal Azure account at azure.microsoft.com/free ($200 credit)
2. Run the one-time Azure setup (Resource Group + Service Principal)
3. Create a Docker Hub account and access token
4. Add 5 GitHub Secrets to your repository
5. Push to `main` — GitHub Actions deploys automatically

---

## GitHub Secrets Required

| Secret | Purpose |
|---|---|
| `AZURE_CREDENTIALS` | Service Principal JSON — authenticates GitHub Actions to Azure |
| `RESOURCE_GROUP` | Azure Resource Group name |
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `OPENROUTER_API_KEY` | LLM API key for the agent |

---

## Important Notes

- **Never commit `.env`** — it contains your API key. It is listed in `.gitignore`.
- **Never commit `terraform/*.tfstate`** — it contains sensitive credentials.
- **Delete Azure resources after class** to avoid charges: `az group delete --name cebd1261-rg --yes --no-wait`
- The `seeder` container always shows `Terminated` state in ACI — this is correct. It runs once then exits.
