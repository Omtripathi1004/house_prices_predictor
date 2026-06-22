import os
import io
import logging
from io import BytesIO
from contextlib import asynccontextmanager

import joblib
import pandas as pd
import requests

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = "house_model.joblib"
FEATURES_PATH = "house_features.joblib"
MODEL_URL = os.getenv("MODEL_URL")

print(os.path.getsize("house_model.joblib") / 1024 / 1024)
model = None
features = []

REQUIRED_COLUMNS = [
    "MedInc",
    "HouseAge",
    "AveRooms",
    "AveBedrms",
    "Population",
    "AveOccup",
    "Latitude",
    "Longitude"
]


def load_model():
    global model, features

    try:
        if MODEL_URL:
            logger.info(f"Downloading model from {MODEL_URL}")

            response = requests.get(
                MODEL_URL,
                timeout=(10, 60)
            )
            response.raise_for_status()

            model = joblib.load(
                BytesIO(response.content)
            )

            logger.info("Model downloaded successfully")

        elif os.path.exists(MODEL_PATH):
            logger.info(f"Loading model from {MODEL_PATH}")

            model = joblib.load(MODEL_PATH)

            logger.info("Model loaded successfully")

        else:
            logger.warning("No model file found")

    except Exception as e:
        logger.exception(f"Model loading failed: {e}")

    try:
        if os.path.exists(FEATURES_PATH):
            features = joblib.load(FEATURES_PATH)

    except Exception as e:
        logger.warning(f"Features loading failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(
    title="House Price Predictor API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HouseFeatures(BaseModel):
    MedInc: float = Field(gt=0)
    HouseAge: float = Field(gt=0)
    AveRooms: float = Field(gt=0)
    AveBedrms: float = Field(gt=0)
    Population: float = Field(gt=0)
    AveOccup: float = Field(gt=0)
    Latitude: float = Field(ge=32, le=42)
    Longitude: float = Field(ge=-125, le=-114)


@app.get("/")
def home():
    return {
        "message": "House Price Prediction API",
        "status": "running"
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
        raise HTTPException(
            status_code=503,
            detail="Model not loaded"
        )

    try:
        try:
            data = house.model_dump()
        except AttributeError:
            data = house.dict()

        df = pd.DataFrame([data])

        prediction = float(
            model.predict(df[REQUIRED_COLUMNS])[0]
        )

        price_usd = prediction * 100000

        return {
            "predicted_price": round(price_usd, 2),
            "formatted_price": f"${price_usd:,.0f}",
            "confidence_range": {
                "lower": round(price_usd - 32773, 2),
                "upper": round(price_usd + 32773, 2)
            }
        }

    except Exception as e:
        logger.exception("Prediction error")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/predict-file")
async def predict_file(
    file: UploadFile = File(...)
):

    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded"
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file"
        )

    try:
        content = await file.read()

        try:
            csv_text = content.decode("utf-8")
        except UnicodeDecodeError:
            csv_text = content.decode("latin-1")

        df = pd.read_csv(
            io.StringIO(csv_text)
        )

        missing = [
            col for col in REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {missing}"
            )

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV contains no rows"
            )

        predictions = model.predict(
            df[REQUIRED_COLUMNS]
        )

        df["predicted_price_usd"] = [
            round(pred * 100000, 2)
            for pred in predictions
        ]

        output_csv = df.to_csv(index=False)

        return StreamingResponse(
            BytesIO(output_csv.encode("utf-8")),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                "attachment; filename=predictions.csv"
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("CSV prediction error")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )