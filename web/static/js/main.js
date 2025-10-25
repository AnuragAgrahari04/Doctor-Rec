// Wait for the entire page to load before running our script
document.addEventListener('DOMContentLoaded', () => {

    // Get references to all the HTML elements we need
    const predictBtn = document.getElementById('predict-btn');
    const symptomsSelect = document.getElementById('symptoms-select');
    const locationInput = document.getElementById('location-input');
    const resultsContainer = document.getElementById('results-content');
    const loader = document.getElementById('loader');
    const initialMessage = document.getElementById('initial-message');

    // Listen for a click on the "Find a Doctor" button
    predictBtn.addEventListener('click', () => {

        // 1. Get the user's inputs
        // Get all selected options from the dropdown
        const selectedSymptoms = Array.from(symptomsSelect.selectedOptions).map(option => option.value);
        const location = locationInput.value;

        // 2. Validate the inputs
        if (selectedSymptoms.length === 0) {
            alert('Please select at least one symptom.');
            return;
        }
        if (!location) {
            alert('Please enter your location.');
            return;
        }

        // 3. Prepare the UI for loading
        loader.classList.remove('hidden'); // Show the spinner
        initialMessage.classList.add('hidden'); // Hide the welcome message
        resultsContainer.innerHTML = ''; // Clear old results

        // 4. Send the data to our Flask backend (/predict)
        fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symptoms: selectedSymptoms,
                location: location
            })
        })
        .then(response => {
            if (!response.ok) {
                // Handle server errors (like 500)
                throw new Error('Network response was not ok.');
            }
            return response.json();
        })
        .then(data => {
            // 5. We have the data! Hide the loader
            loader.classList.add('hidden');

            // Check if the server sent an error message
            if (data.error) {
                throw new Error(data.error);
            }

            // 6. Build the results HTML
            displayResults(data);
        })
        .catch(error => {
            // 7. Handle any errors
            loader.classList.add('hidden');
            resultsContainer.innerHTML = `<p style="color: red;">An error occurred: ${error.message}</p>`;
        });
    });

    /**
     * Takes the JSON data from the server and builds HTML to display it
     * @param {object} data - The data from our /predict endpoint
     */
    function displayResults(data) {
        // Start with the prediction summary
        let html = `
            <div class="prediction-summary">
                <h3>Predicted Condition: ${data.predicted_disease}</h3>
                <p>Recommended Specialist: <strong>${data.specialist}</strong></p>
            </div>
            <h4>Top 5 ${data.specialist}s near you:</h4>
        `;

        // Check if any doctors were found
        if (data.doctors.length === 0) {
            html += '<p>No doctors found matching your criteria. Try a broader location.</p>';
        } else {
            // Loop through each doctor and create a "card"
            data.doctors.forEach(doctor => {
                html += `
                    <div class="doctor-card">
                        <h4>${doctor.name}</h4>
                        <p><strong>${doctor.rating}</strong> ⭐ | ${doctor.open_now_status}</p>
                        <p>📍 <strong>Address:</strong> ${doctor.address}</p>
                        <p>📞 <strong>Phone:</strong> ${doctor.phone}</p>
                        <div class="btn-group">
                            <a href="${doctor.website || '#'}" class="btn btn-secondary ${!doctor.website ? 'disabled' : ''}" target="_blank" rel="noopener noreferrer">
                                Visit Website 🌐
                            </a>
                            <a href="${doctor.gmaps_url}" class="btn btn-primary" target="_blank" rel="noopener noreferrer">
                                View on Map 🗺️
                            </a>
                        </div>
                    </div>
                `;
            });
        }

        // Set the final HTML to our container
        resultsContainer.innerHTML = html;
    }
});