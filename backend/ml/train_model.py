import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

data = pd.read_csv("dataset.csv")

X = data.drop("risk", axis=1)
y = data["risk"]

model = RandomForestClassifier(n_estimators=100)

model.fit(X, y)

joblib.dump(model, "threat_model.pkl")

print("Model trained successfully")