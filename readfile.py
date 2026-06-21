import os, logging, io
import joblib, requests, pandas as pd
from io import BytesIO
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="House Prices Predictor")

# Model paths / env
MODEL_PATH = "house_model.joblib"
FEATURES_PATH = "house_features.joblib"
MODEL_URL = os.getenv("MODEL_URL")

# Load model and features
try:
    if MODEL_URL:
        logger.info("Downloading model from %s", MODEL_URL)
        r = requests.get(MODEL_URL, timeout=30)
        r.raise_for_status()
        model = joblib.load(BytesIO(r.content))
    elif os.path.exists(MODEL_PATH):
        logger.info("Loading model from %s", MODEL_PATH)
        model = joblib.load(MODEL_PATH)
    else:
        logger.warning("No model found; set MODEL_URL or include %s", MODEL_PATH)
        model = None
except Exception:
    logger.exception("Model load failed")
    model = None

features = joblib.load(FEATURES_PATH) if os.path.exists(FEATURES_PATH) else []

# Pydantic schema
class HouseFeatures(BaseModel):
    MedInc: float = Field(gt=0)
    HouseAge: float = Field(gt=0)
    AveRooms: float = Field(gt=0)
    AveBedrms: float = Field(gt=0)
    Population: float = Field(gt=0)
    AveOccup: float = Field(gt=0)
    Latitude: float = Field(ge=32, le=42)
    Longitude: float = Field(ge=-125, le=-114)

# Routes
@app.get("/")
def home():
    return {
        "message": "California houses prediction API",
        "status": "running",
        "endpoint": "send POST request to /predict"
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "features": features
    }

@app.post("/predict")
def predict(house: HouseFeatures):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        input_data = pd.DataFrame([house.dict()])
        predicted = model.predict(input_data)[0]
        price_usd = predicted * 100000
        return {
            "predicted_price": f"${price_usd:,.0f}",
            "predicted_price_short": f"${predicted:.2f} hundred thousands",
            "confidence_range": f"${price_usd - 32773:,.0f} to ${price_usd + 32773:,.0f}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict-file")
async def predict_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file only")
    contents = await file.read()
    try:
        s = contents.decode("utf-8")
    except Exception:
        s = contents.decode("latin-1")
    df = pd.read_csv(io.StringIO(s))

    required_columns = [
        "MedInc","HouseAge","AveRooms","AveBedrms",
        "Population","AveOccup","Latitude","Longitude"
    ]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")
    if len(df) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file has no data rows")

    try:
        predictions = model.predict(df[required_columns])
        price_usd = predictions * 100000
        df["predicted_price_usd"] = [f"${x:,.0f}" for x in price_usd]
        output = df.to_csv(index=False)
        return StreamingResponse(
            io.StringIO(output),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=predictions.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
