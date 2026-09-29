import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

def train_attrition_model():
    """
    Trains a Machine Learning model to predict employee attrition (whether someone will quit).
    This uses the IBM HR Analytics dataset and saves the trained 'brain' to a .pkl file
    so that the Streamlit app can use it instantly without having to retrain.
    """
    print("Loading the Kaggle dataset...")
    
    # Path to the downloaded dataset
    dataset_path = '/home/aarav/.cache/kagglehub/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset/versions/1/WA_Fn-UseC_-HR-Employee-Attrition.csv'
    
    # Ensure the file exists before trying to read it
    if not os.path.exists(dataset_path):
        print(f"Error: Could not find the dataset at {dataset_path}")
        print("Make sure you downloaded it via kagglehub!")
        return

    # Load the CSV spreadsheet into a Pandas DataFrame
    df = pd.read_csv(dataset_path)

    print("Preprocessing the data...")
    # The original dataset has 35 columns, but we are only keeping 5 key features
    # to make our app's User Interface clean and simple.
    features = ['Age', 'MonthlyIncome', 'JobSatisfaction', 'OverTime', 'YearsAtCompany']

    # Machine Learning models only understand numbers, so we must translate text columns.
    # We map 'Yes' to 1 and 'No' to 0 for both Attrition (our target) and OverTime.
    df['Attrition'] = df['Attrition'].map({'Yes': 1, 'No': 0})
    df['OverTime'] = df['OverTime'].map({'Yes': 1, 'No': 0})

    # Separate our inputs (X) and the answers we want to predict (y)
    X = df[features]
    y = df['Attrition']

    print("Training the Random Forest model...")
    # We use a Random Forest because it is robust, doesn't require complex scaling, 
    # and handles mixed data types well. We set random_state to ensure reproducibility.
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    print("Saving the 'brain' to attrition_model.pkl...")
    # joblib.dump freezes our trained model into a tiny file. 
    # The Streamlit app will load this file to make live predictions.
    joblib.dump(model, 'attrition_model.pkl')

    print("Done! The ML Model is ready to be used in the HR Dashboard.")

if __name__ == '__main__':
    train_attrition_model()
