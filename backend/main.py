import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.services import database, excel_loader
from backend.routes import chat

app = FastAPI(title="Procurement AI Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "https://*.onrender.com",  # Render production (for deployment)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")

EXCEL_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "attached_assets",
    "ERP_SAMPLE_DATASET_2026_1767598300570.xlsx"
)

@app.on_event("startup")
async def startup_event():
    database.init_database()
    
    if database.db_available:
        count = database.get_record_count()
        if count == 0:
            print("Database is empty, loading data from Excel file...")
            try:
                records = excel_loader.load_excel_data(EXCEL_FILE_PATH)
                print(f"Loaded {len(records)} records from Excel")
                database.insert_records(records)
                print(f"Successfully imported {len(records)} procurement records")
            except Exception as e:
                print(f"Error loading Excel data: {e}")
        else:
            print(f"Database already has {count} records")
    else:
        print("Skipping database data loading since database is not available")


CLIENT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client")
DIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist", "public")

if os.path.exists(DIST_PATH):
    if os.path.exists(os.path.join(DIST_PATH, "assets")):
        app.mount("/assets", StaticFiles(directory=os.path.join(DIST_PATH, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            return None
        file_path = os.path.join(DIST_PATH, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(DIST_PATH, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend not built. Run 'npm run build' first."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=5000, reload=True)

