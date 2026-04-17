import os
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
import fitz  # PyMuPDF

from app.services.ocr_service import process_image_and_ocr
from app.services.excel_service import export_to_excel

app = FastAPI(title="Zonal OCR MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
EXPORT_DIR = "app/exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

@app.get("/")
async def root():
    return FileResponse("app/static/index.html")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    ext = file.filename.split('.')[-1].lower()
    
    file_location = os.path.join(UPLOAD_DIR, f"{file_id}.{ext}")
    with open(file_location, "wb+") as file_object:
         file_object.write(file.file.read())
         
    image_path = file_location
    if ext == 'pdf':
        doc = fitz.open(file_location)
        page = doc.load_page(0)  # first page
        pix = page.get_pixmap(dpi=200) # Render at 200 DPI for better OCR
        image_path = os.path.join(UPLOAD_DIR, f"{file_id}.jpg")
        pix.save(image_path)
        doc.close()
            
    return {"file_id": file_id, "image_url": f"/images/{os.path.basename(image_path)}"}

@app.get("/images/{filename}")
async def get_image(filename: str):
    return FileResponse(os.path.join(UPLOAD_DIR, filename))

@app.post("/ocr")
async def extract_ocr(
    file_id: str = Form(...),
    regions: str = Form(...),
    natural_width: float = Form(...),
    natural_height: float = Form(...)
):
    try:
        regions_data = json.loads(regions)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "Invalid regions format"})

    base_path = os.path.join(UPLOAD_DIR, file_id)
    image_path = None
    for ext in ['.jpg', '.png', '.jpeg']:
        if os.path.exists(base_path + ext):
            image_path = base_path + ext
            break
            
    if not image_path:
        return JSONResponse(status_code=404, content={"error": "Image not found"})
        
    results = process_image_and_ocr(image_path, regions_data, natural_width, natural_height)
    return {"results": results}

@app.post("/download")
async def download_excel(data: str = Form(...)):
    try:
        parsed_data = json.loads(data)
    except Exception as e:
         return JSONResponse(status_code=400, content={"error": "Invalid data format"})
         
    excel_path = export_to_excel(parsed_data, EXPORT_DIR)
    return FileResponse(path=excel_path, filename="extracted_data.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
