import joblib 
import pandas as pd
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field

app = FastAPI()

model =joblib.load("house_model.joblib")
features = joblib.load("house_features.joblib")

class HouseFeatures(BaseModel):
    MedInc : float = Field( gt= 0 , descripation ="Media Income of Neighbourhood")
    HouseAge: float = Field(gt= 0 , description = "Average age of the house in the block")
    AveRooms: float = Field(gt=0 , description = "Average number of the room per house")
    AveBedrms: float = Field(gt=0 , description = " Average number of bedroom per house")
    Population: float = Field(gt=0 , descripation = "Total population of the block")
    Ave0ccup: float = Field (gt=0 , descripation = "Average number of people living in the house")
    Latitude : float = Field (ge=32, le = 42 , description = "latitude")
    Longitude: float = Field (ge=-125 , le=-114, description= "Longitude")


# home 

@app.get("/")
def home():
    return {
        "message":"California houses prediction api",
        "Status":"running",
        "Endpoint":"send POST request to /predict"
    }

@app.get("/health")
def health():
    return {
        "Status":"running",
        "model":"RandomForestRegressor",
        "features":features,
        "avg_error": "$32,773"
    }

#predication
@app.post("/predict")
def predict(house: HouseFeatures):
    try:
        input_data = pd.DataFrame([{
            "MedInc":house.MedInc,
            "HouseAge":house.HouseAge,
            "AveRooms":house.AveRooms,
            "AveBedrms": house.AveBedrms,
            "Population":house.Population,
            "AveOccup":house.Ave0ccup,
            "Latitude":house.Latitude,
            "Longitude": house.Longitude
        }])

        predicted = model.predict(input_data)[0]
        price_usd = predicted * 100000

        return{
            "predicted_price":f"${price_usd:,.0f}",
            "predicted_price_short":f"${predicted:.2f} hundred thousands",
            "fidence_range":f"${price_usd - 32773:,.0f} to ${price_usd + 32773:,.0f}"
        }
    except Exception as e:
        raise HTTPException(
            status_code= 500,
            detail =f"prediction failed: {str(e)}"
        )