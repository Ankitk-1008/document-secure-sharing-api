# Document Management & Secure File Sharing System

FastAPI + SQLAlchemy 2 + MySQL (configured because the project owner requested MySQL) + Alembic + JWT + Argon2 + RBAC + Pytest + Docker Compose.

> The task brief mentions PostgreSQL, but the local project request says MySQL. This implementation uses MySQL. To switch to PostgreSQL, change `DATABASE_URL` and install/configure the PostgreSQL driver.

## Included
- Registration, login, Argon2 password hashing, JWT bearer tokens, `/auth/me`
- Roles: `admin`, `manager`, `user`, `viewer`; default public registration role is `user`
- Single/multiple upload, extension and size checks, basic file-signature checks for PDF/PNG/JPEG, UUID stored names
- Document listing with pagination, filtering, sorting, metadata, downloads and ownership-aware deletion
- Sharing/revoking shares and download permission checks
- Audit logs, structured DB exception response, login rate limiting, upload background notification placeholder
- SQLAlchemy models, Alembic environment, Pytest tests, Dockerfile and Compose with MySQL + Redis
- Redis service is included in Compose for extension; caching is not enabled in the API code yet.

## Security notes
- Never commit `.env`; it is ignored by Git.
- Do not put real passwords, JWT secrets, or production credentials in source control.
- This starter stores uploaded files on local disk. For production, consider object storage, malware scanning, stricter MIME/content validation, HTTPS, and a distributed rate limiter.
- The login limiter is in-memory and resets when the process restarts; use Redis-backed limiting for multi-worker deployments.
- Do not expose an Admin registration endpoint. Assign elevated roles through a trusted administrative process/database operation.

## Run in VS Code (Windows PowerShell)
1. Install Python 3.12+, MySQL 8+, and Git.
2. Create the database:
   ```sql
   CREATE DATABASE document_sharing_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Open this folder in VS Code terminal:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```
4. Edit `.env`: set your local MySQL password in `DATABASE_URL`, and replace `JWT_SECRET_KEY` with a long random secret. Do not paste secrets into GitHub.
5. Create initial schema (quick local development):
   ```powershell
   python -c "from app.db.session import Base, engine; import app.models; Base.metadata.create_all(engine)"
   ```
   For migration-managed schema, initialize Alembic revision once:
   ```powershell
   alembic revision --autogenerate -m "initial schema"
   alembic upgrade head
   ```
   Review generated migration before applying it.
6. Start:
   ```powershell
   uvicorn app.main:app --reload
   ```
7. Open http://127.0.0.1:8000/docs

## API walkthrough
- `POST /api/v1/auth/register` JSON: `{"full_name":"Ankit Demo","email":"ankit@example.com","password":"StrongPass123!"}`
- `POST /api/v1/auth/login` form fields: `username=ankit@example.com`, `password=StrongPass123!`
- Click **Authorize** in Swagger and paste the access token (or use `Bearer <token>` depending on Swagger prompt).
- `GET /api/v1/auth/me`
- `POST /api/v1/documents/upload` multipart form field `file`
- `POST /api/v1/documents/upload-multiple` multipart form field `files`
- `GET /api/v1/documents?skip=0&limit=20&q=report&sort=newest`
- `GET /api/v1/documents/{id}`, `GET /api/v1/documents/{id}/download`, `DELETE /api/v1/documents/{id}`
- `POST /api/v1/sharing/{document_id}` JSON: `{"email":"other@example.com","can_download":false}`
- `DELETE /api/v1/sharing/{document_id}/{target_user_id}`
- `GET /api/v1/users` (Admin/Manager only)

## Testing
```powershell
pytest -q
```

## Docker
Set `.env` variables including `MYSQL_ROOT_PASSWORD` and a `DATABASE_URL` pointing to the compose service `mysql`, e.g. `mysql+pymysql://root:${MYSQL_ROOT_PASSWORD}@mysql:3306/document_sharing_db`. Compose variable interpolation inside `.env` values may not work as expected; replace it with the literal password locally. Then:
```powershell
docker compose up --build
```
For Compose, the API service uses the same `.env`; use hostname `mysql` in `DATABASE_URL`. For local non-Docker execution use `127.0.0.1`.

## GitHub final link
This ZIP is ready to extract and push to your own GitHub repository. I cannot publish a repository or generate a real GitHub URL without access to your GitHub account. After creating an empty repository on GitHub:
```powershell
git init
git add .
git commit -m "Build secure document management API"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/document-secure-sharing-api.git
git push -u origin main
```
Replace `YOUR_USERNAME` with your GitHub username. Never add `.env` to Git.
