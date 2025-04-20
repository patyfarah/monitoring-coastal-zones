import streamlit as st
import ee
import geemap.foliumap as geemap

# Path to your service account key JSON file
SERVICE_ACCOUNT = 'earth-engine-service-account@your-project.iam.gserviceaccount.com'
KEY_PATH = 'ee-project-457404-0ca271002802.json'

# Authenticate and initialize
credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, KEY_PATH)
ee.ServiceAccountCredentials()
ee.Initialize(credentials)

# Title
st.title("Earth Engine Web App")

# Dropdown
country_list = ['Lebanon', 'Jordan', 'Syria']
country = st.selectbox("Select a country", country_list)

# Map
Map = geemap.Map()

# Filter by country
countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
filtered = countries.filter(ee.Filter.eq('country_na', country))

# Add layer
Map.addLayer(filtered, {}, country)
Map.centerObject(filtered)

# Display map
Map.to_streamlit(height=600)
