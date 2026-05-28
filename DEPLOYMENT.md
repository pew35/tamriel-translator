# Deploy and Package

## Cloud Backend on Render

1. Push this repository to GitHub.
2. In Render, create a new Blueprint from the repository.
3. Render will read `render.yaml` and create `tamriel-translator-api`.
4. Set `OPENAI_API_KEY` in the Render service environment variables.
5. Deploy the service.
6. Open the Render URL and confirm it returns:

```json
{"status":"ok","service":"Tamriel Translator API"}
```

The backend creates the SQLite glossary database on startup and imports
`backend/glossary_data/*.csv` when the database is empty.

## Build the Windows Desktop App

Set the cloud backend URL before building:

```powershell
$env:VITE_API_BASE_URL="https://your-render-service.onrender.com"
npm run dist
```

If your Render service URL is exactly
`https://tamriel-translator-api.onrender.com`, you can run `npm run dist`
without setting `VITE_API_BASE_URL`.

The downloadable files are written to:

```text
frontend/release/
```

Share the installer or portable `.exe` from that folder.
