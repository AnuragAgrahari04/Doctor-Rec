import os
import joblib
import pandas as pd
import googlemaps
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Load environment variables (your API key)
load_dotenv()

app = Flask(__name__)

# --- 1. Load All Resources on Startup ---

# Load Google Maps Client
try:
    API_KEY = os.getenv("GOOGLE_API_KEY")
    gmaps = googlemaps.Client(key=API_KEY)
except Exception as e:
    print(f"Error initializing Google Maps Client: {e}")
    gmaps = None

# Load ML Model
try:
    model = joblib.load('model/disease_predictor_model.pkl')
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

# Load Symptom List
try:
    data = pd.read_csv('Training.csv')
    all_cols = data.columns.tolist()
    symptoms = [col for col in all_cols if col != 'prognosis' and not col.startswith('Unnamed:')]
except Exception as e:
    print(f"Error loading symptoms from Training.csv: {e}")
    symptoms = []

# Define Disease-to-Specialist Map
specialty_map = {
    'Fungal infection': 'Dermatologist', 'Allergy': 'Allergist', 'GERD': 'Gastroenterologist',
    'Acne': 'Dermatologist', 'Pneumonia': 'Pulmonologist', 'Jaundice': 'Gastroenterologist',
    'Migraine': 'Neurologist', 'Hypertension ': 'Cardiologist', 'Heart attack': 'Cardiologist',
    'Paralysis (brain hemorrhage)': 'Neurologist', 'Chicken pox': 'Dermatologist',
    'Malaria': 'General Practitioner', 'Dengue': 'General Practitioner', 'Typhoid': 'General Practitioner'
    # ... add all 41 diseases here
}


# --- 2. Define App Routes ---

@app.route('/')
def index():
    """Renders the main homepage and passes the symptom list to the HTML."""
    if not symptoms:
        return "Error: Could not load symptoms. Please check server logs.", 500
    # Pass the list of symptoms to the index.html template
    return render_template('index.html', symptoms=symptoms)


@app.route('/predict', methods=['POST'])
def predict():
    """API endpoint to handle symptom data and return a prediction + doctor list."""
    if not model or not gmaps:
        return jsonify({"error": "Backend server is not configured correctly."}), 500

    try:
        data = request.json
        user_symptoms = data.get('symptoms', [])
        user_location = data.get('location', '')

        if not user_symptoms or not user_location:
            return jsonify({"error": "Missing symptoms or location."}), 400

        # --- 1. Make Disease Prediction ---
        model_input = {symptom: 0 for symptom in symptoms}
        for symptom in user_symptoms:
            if symptom in model_input:
                model_input[symptom] = 1

        input_df = pd.DataFrame([model_input])
        prediction = model.predict(input_df)[0]
        specialist = specialty_map.get(prediction, 'General Practitioner')

        # --- 2. Find Doctors (Text Search) ---
        query = f"{specialist} in {user_location}"
        places_result = gmaps.places(query=query, type='doctor')
        doctors_list = places_result.get('results', [])[:5]

        # --- 3. Get Rich Details for Each Doctor ---
        doctors_details = []
        for doctor in doctors_list:
            place_id = doctor['place_id']
            fields = ['name', 'formatted_address', 'international_phone_number',
                      'website', 'rating', 'opening_hours', 'geometry']

            place_details = gmaps.place(place_id=place_id, fields=fields)
            details = place_details.get('result', {})

            # Get opening hours
            open_now_status = "Status unknown"
            if 'opening_hours' in details:
                open_now = details['opening_hours'].get('open_now', False)
                open_now_status = "🟢 Open now" if open_now else "🔴 Closed"

            doctors_details.append({
                "name": details.get('name', 'N/A'),
                "address": details.get('formatted_address', 'Address not available'),
                "phone": details.get('international_phone_number', 'Phone not available'),
                "website": details.get('website'),
                "rating": details.get('rating', 'N/A'),
                "open_now_status": open_now_status,
                "gmaps_url": f"https://www.google.com/maps/search/?api=1&query={details.get('name', '').replace(' ', '+')}&query_place_id={place_id}",
                "location": details.get('geometry', {}).get('location', {})  # Contains 'lat' and 'lng'
            })

        # --- 4. Return Everything as JSON ---
        return jsonify({
            "predicted_disease": prediction,
            "specialist": specialist,
            "doctors": doctors_details
        })

    except Exception as e:
        print(f"An error occurred during prediction: {e}")
        return jsonify({"error": str(e)}), 500


# --- 3. Run the App ---
if __name__ == '__main__':
    app.run(debug=True)