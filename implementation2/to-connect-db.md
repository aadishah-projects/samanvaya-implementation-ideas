## What was fixed

### 1. Root cause
- Your local Windows Postgres was listening on `localhost:5432`.
- The Docker Postgres container was running on host port `5433` (`0.0.0.0:5433->5432/tcp`).
- So `python seed_data.py` was trying to connect to the wrong Postgres instance and failing authentication.

### 2. What I changed

#### Docker
- Stopped and removed the old `samanvaya-db` container.
- Restarted it with:
  - `docker run --name samanvaya-db -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=samanvaya -p 5433:5432 -d postgres:15`
- This made the Docker Postgres available on `localhost:5433`.

#### seed_data.py
- Added environment-driven configuration:
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_HOST`
  - `DB_PORT`
- Used `os.getenv(..., default)` so defaults remain sane.
- Added a clearer `try/except` around `psycopg2.connect(...)` so connection failures now report the host, port, and user.
- Added `TRUNCATE TABLE sosys_payments, openimis_claims;` before inserting data so the script can be rerun without duplicate-key errors.

### 3. How you ran it successfully
- Set the port to the Docker-mapped port:
  - `powershell $env:DB_PORT = "5433"`
- Then ran:
  - `python seed_data.py`

### 4. Result
- The script connected successfully to Docker Postgres on `localhost:5433`
- It seeded:
  - `300` `openimis_claims`
  - `~250` `sosys_payments`

If you want, I can also turn the same env-driven connection pattern into a documented `README` note for this project.