# Generic Project Notes

This file is a reusable project template. It captures the main patterns you can copy into another codebase without tying the instructions to a specific app, service name, or folder layout.

## 1. Seeding and data bootstrap

Use a dedicated seed entrypoint for database bootstrap instead of mixing seed logic into application startup.

Recommended structure:

- one orchestration script that runs the seed sequence in order
- one file per collection or domain object
- helper scripts kept separate from the primary seed flow

Generic seed flow:

1. Connect to the required database(s).
2. Run seed files in dependency order.
3. Make each seed idempotent so re-runs do not duplicate data.
4. Close connections and exit cleanly when done.

Good seed file patterns:

- seed users or accounts first
- seed dependent profiles or linked records second
- seed content records after identities exist
- seed relationships or connections after both sides exist
- seed any secondary database last if it depends on the primary data

Helper scripts should stay separate from the main seed flow. They are useful for:

- one-off admin creation
- manual event or content insertion
- verification-code insertion
- fixing or repairing legacy records
- sample data extraction or reuse

Important seeding rules:

- use deterministic data where possible
- check for existing records before inserting
- keep the seed command explicit and easy to run
- make the flow safe to rerun in local development

## 2. Docker architecture

Use a split runtime model with app containers plus supporting services.

Typical layout:

- backend service container
- frontend service container
- database container(s)
- cache or queue container(s)
- optional reverse proxy container

Recommended container behavior:

- backend image should install dependencies and start the server
- frontend image should build static assets in a builder stage and serve them from a small runtime image
- databases and caches should stay in separate containers
- the proxy should handle frontend delivery, API routing, and WebSocket forwarding if needed

General Docker guidance:

- prefer multi-stage builds for frontend apps
- prefer small runtime images for the final container
- keep runtime config in environment variables
- expose only the ports that must be reachable from outside the container network

## 3. Compose layout

Use a base Compose file for the runtime topology and a separate override file for development convenience.

Base Compose file should define:

- core services
- environment wiring
- service dependencies
- shared volumes
- container health checks when useful

Override Compose file should define:

- bind mounts for live editing
- host port mappings for local access
- hot reload commands
- local-only volumes for development data
- alternate environment values for local use

This split keeps production-like configuration separate from developer-only behavior.

## 4. Frontend modes

Support two ways to run the frontend:

- as a Dockerized static app for production-style runs
- as a separate npm-based dev server for rapid iteration

That gives you flexibility when working on a new project:

- use Docker when you want a deployable artifact
- use the package manager when you want fast local feedback

Generic frontend pattern:

- development command launches the local dev server
- build command generates static output
- production container serves the build output through a web server or proxy

## 5. Reverse proxy routing

Use a reverse proxy to separate browser traffic from service traffic.

Common routing rules:

- `/api/` forwards to the backend
- WebSocket paths forward to the backend with upgrade headers
- `/` serves the frontend shell and static assets

Additional proxy recommendations:

- add cache headers for static assets
- disable caching for files that must refresh on deploy
- keep WebSocket timeouts explicit
- avoid exposing internal service ports directly unless needed

## 6. Local development workflow

The cleanest developer workflow is usually:

1. Start infrastructure and backend services with Compose.
2. Run the frontend separately if you want a faster dev loop.
3. Seed the database once after startup if the app needs sample data.
4. Use hot reload instead of rebuilding everything on every change.

Generic local commands to standardize in another project:

- `docker compose up` for shared services
- `npm ci` in the frontend folder for local frontend work
- a dedicated seed command for database bootstrap
- a down or cleanup command to stop the environment cleanly

## 7. CI/CD layout

Keep CI split by responsibility rather than using one large workflow.

Suggested workflow split:

- frontend workflow for lint, tests, build, and image validation
- backend workflow for lint, tests, build, and image validation
- deployment workflow for release, restart, and health verification

Common CI steps:

- checkout code
- set the Node version used by the project
- install dependencies with `npm ci`
- run lint
- run tests
- run build
- build Docker images with Buildx and caching

Common deploy steps:

- trigger only from the release branch or main branch
- authenticate to the target host or platform
- fetch the latest code or artifact
- rebuild the runtime stack
- verify health endpoints after deployment

## 8. Generic deployment template

If you want a reusable deployment checklist, use this shape:

1. Define the runtime services and their dependencies.
2. Add a development override for mounts, ports, and hot reload.
3. Build the frontend as a static production artifact if applicable.
4. Place the frontend behind a reverse proxy.
5. Keep database and cache services isolated from app containers.
6. Split CI into separate frontend, backend, and deploy workflows.
7. Gate release with lint, test, build, and health checks.

## 9. What to reuse in another project

The reusable ideas are:

- seed logic organized into an ordered pipeline
- idempotent seed files
- app containers separated from databases and caches
- base Compose plus dev override
- frontend that can run either as a container or as a direct dev server
- reverse proxy routing for API and WebSocket traffic
- separate CI workflows for app parts and deployment
- deploy validation through health checks

Use this document as a pattern library. Replace the specific service names, ports, scripts, and file paths with the equivalents from the new project.
