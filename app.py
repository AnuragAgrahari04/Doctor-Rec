import streamlit as st
import joblib
import pandas as pd
import time
import googlemaps

# --- 1. Page Configuration (MUST be the first command) ---
st.set_page_config(
    page_title="Intelligent Doctor Recommender",
    page_icon="🩺",
    layout="wide"
)

# --- 2. Initialize Google Maps Client ---
try:
    gmaps = googlemaps.Client(key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error(f"Could not initialize Google Maps: {e}. Check your API key in .streamlit/secrets.toml.")
    gmaps = None


# --- 3. Caching the Model and Data ---
@st.cache_resource
def load_model():
    """Loads the saved machine learning model."""
    try:
        model = joblib.load('model/disease_predictor_model.pkl')
        return model
    except FileNotFoundError:
        st.error("Error: Model file not found. Make sure 'disease_predictor_model.pkl' is in the 'model' folder.")
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the model: {e}")
        return None


@st.cache_data
def get_symptoms_list():
    """Loads the list of symptoms from the Training.csv file."""
    try:
        data = pd.read_csv('Training.csv')
        all_cols = data.columns.tolist()
        symptoms = [col for col in all_cols if col != 'prognosis' and not col.startswith('Unnamed:')]
        return symptoms
    except FileNotFoundError:
        st.error("Error: 'Training.csv' not found. Make sure it's in the main project folder.")
        return []
    except Exception as e:
        st.error(f"An error occurred while loading symptoms: {e}")
        return []


# --- 4. Load the resources ---
model = load_model()
symptoms = get_symptoms_list()

# --- 5. Sidebar ---
with st.sidebar:
    st.title("About")
    st.info(
        "This app uses a Machine Learning model to predict a "
        "potential condition based on your symptoms. It then "
        "recommends specialized doctors near you using the "
        "Google Places API."
    )
    st.divider()
    st.title("ℹ️ Disclaimer")
    st.warning(
        "This tool is for informational purposes only and is not a "
        "substitute for professional medical advice. Always consult "
        "a qualified healthcare provider."
    )

# --- 6. Main Page UI ---
st.title("Intelligent Doctor Recommender 🩺")
st.markdown("Welcome! Please select your symptoms and enter your location to get a list of recommended specialists.")
st.divider()

if model and symptoms and gmaps:
    # --- 7. Two-Column Layout ---
    col1, col2 = st.columns([1, 1.2])

    # --- Column 1: Inputs ---
    with col1:
        st.subheader("🧑‍⚕️ Your Information")

        user_symptoms = st.multiselect(
            label="What symptoms are you experiencing?",
            options=symptoms,
            placeholder="Type and select your symptoms"
        )

        user_location = st.text_input(
            label="Enter your City or Zip Code:",
            placeholder="e.g., 'New Delhi' or '221002'"
        )

        find_doctor_button = st.button("Find a Doctor", type="primary", use_container_width=True)

    # --- Column 2: Outputs (This is the scrollable results area) ---
    with col2:
        st.subheader("✨ Recommendations")

        with st.container(height=800):
            if find_doctor_button:
                if not user_symptoms:
                    st.warning("Please select at least one symptom.")
                elif not user_location:
                    st.warning("Please enter your location.")
                else:
                    # --- THIS IS THE CORRECTED LOGIC ---

                    # Initialize variables to hold results
                    prediction = None
                    specialist = None
                    doctors_list = []
                    map_data_list = []

                    # --- Step 1: Run processing inside st.status ---
                    with st.status("Finding recommendations...", expanded=True) as status:
                        try:
                            st.write("Analyzing your symptoms...")
                            time.sleep(1)

                            model_input = {symptom: 0 for symptom in symptoms}
                            for symptom in user_symptoms:
                                if symptom in model_input:
                                    model_input[symptom] = 1
                            input_df = pd.DataFrame([model_input])
                            prediction = model.predict(input_df)[0]

                            st.write("Identifying the right specialist...")
                            time.sleep(0.5)

                            specialty_map = {
                                'Fungal infection': 'Dermatologist', 'Allergy': 'Allergist',
                                'GERD': 'Gastroenterologist',
                                'Acne': 'Dermatologist', 'Pneumonia': 'Pulmonologist', 'Jaundice': 'Gastroenterologist',
                                'Migraine': 'Neurologist', 'Hypertension ': 'Cardiologist',
                                'Heart attack': 'Cardiologist',
                                'Paralysis (brain hemorrhage)': 'Neurologist', 'Chicken pox': 'Dermatologist',
                                'Malaria': 'General Practitioner', 'Dengue': 'General Practitioner',
                                'Typhoid': 'General Practitioner'
                            }
                            specialist = specialty_map.get(prediction, 'General Practitioner')

                            st.write(f"Searching for {specialist}s near {user_location}...")

                            # --- Google Places API Call ---
                            query = f"{specialist} in {user_location}"
                            places_result = gmaps.places(query=query, type='doctor')
                            doctors_list = places_result.get('results', [])[:5]

                            # Get details for each doctor
                            for doctor in doctors_list:
                                place_id = doctor['place_id']
                                fields = ['name', 'formatted_address', 'international_phone_number',
                                          'website', 'rating', 'opening_hours', 'geometry']
                                place_details = gmaps.place(place_id=place_id, fields=fields)
                                details = place_details.get('result', {})

                                # Store details in a structured way
                                doctor['details'] = details

                                if 'geometry' in details:
                                    location = details['geometry']['location']
                                    map_data_list.append({'name': details.get('name', 'N/A'), 'lat': location['lat'],
                                                          'lon': location['lng']})

                            status.update(label="Analysis Complete!", state="complete", expanded=False)

                        except Exception as e:
                            status.update(label="Error processing request", state="error")
                            st.error(f"An error occurred: {e}")

                    # --- Step 2: Display results OUTSIDE st.status ---
                    if prediction and specialist:
                        st.success(f"**Predicted Condition:** {prediction}")
                        st.balloons()
                        st.markdown(f"### Recommended Specialist: **{specialist}**")
                        st.divider()
                        st.subheader(f"Top 5 {specialist}s near you:")

                        if not doctors_list:
                            st.warning("No doctors found matching your criteria. Try a broader location.")
                        else:
                            # Loop and display doctor cards
                            for doctor in doctors_list:
                                details = doctor.get('details', {})
                                place_id = doctor['place_id']  # Use original place_id
                                name = details.get('name', 'N/A')
                                address = details.get('formatted_address', 'Address not available')
                                phone = details.get('international_phone_number', 'Phone not available')
                                website = details.get('website', None)
                                rating = details.get('rating', 'N/A')

                                open_now = "Status unknown"
                                if 'opening_hours' in details:
                                    open_now = "🟢 Open now" if details['opening_hours'].get('open_now',
                                                                                            False) else "🔴 Closed"

                                with st.container(border=True):
                                    st.markdown(f"#### {name}")
                                    st.write(f"**{rating}** ⭐ | {open_now}")
                                    st.write(f"📍 **Address:** {address}")
                                    st.write(f"📞 **Phone:** {phone}")

                                    col_btn1, col_btn2 = st.columns(2)
                                    with col_btn1:
                                        if website:
                                            st.link_button("Visit Website 🌐", url=website, use_container_width=True)
                                        else:
                                            st.button("Website N/A", disabled=True, use_container_width=True,
                                                      key=f"web_na_{place_id}")
                                    with col_btn2:
                                        gmaps_url = f"http://googleusercontent.com/maps/google.com/4{name.replace(' ', '+')}&query_place_id={place_id}"
                                        st.link_button("View on Map 🗺️", url=gmaps_url, use_container_width=True)
                                st.write("")

                            if map_data_list:
                                st.divider()
                                st.subheader("Doctor Locations:")
                                map_df = pd.DataFrame(map_data_list)
                                st.map(map_df, latitude='lat', longitude='lon', size=10, zoom=12)

            else:
                st.info("Your results will appear here.")

elif not (model and symptoms):
    st.error("Application could not be started. Please check model/data file paths.")
else:
    st.error("Google Maps Client could not be initialized. Please check your API key in .streamlit/secrets.toml")