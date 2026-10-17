# GreenROI Frontend (React + Vite)

This frontend connects to the existing FastAPI backend on `http://127.0.0.1:8000` using a Vite development proxy. It calls these existing routes:

- `GET /health`
- `GET /knowledge-base`
- `POST /predict`

## Install and run

1. Place the `frontend` folder in the root of your `AI_BUILDER_CUP` project.
2. Start your existing backend in a separate terminal from the project root:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
   ```

3. Open another terminal and run:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

4. Open the local URL Vite prints, usually `http://localhost:5173`.

## Notes

- The prediction form sends the nine input fields currently expected by the backend example.
- The result shows the model's raw output. Confirm the training target and units before interpreting it as energy consumption.
- The UI does not yet calculate ROI or retrieve individual interventions; those are the next integration step after prediction works.
- The Vite proxy avoids requiring CORS configuration for local development.
