import streamlit as st
import ee
import geemap.foliumap as geemap

# Load credentials from Streamlit secrets
credentials_dict = st.secrets["earthengine"]

# Convert dict to JSON string and parse it
service_account_info = json.loads(json.dumps(credentials_dict))

# Authenticate and initialize Earth Engine
credentials = ee.ServiceAccountCredentials(
    service_account_info['client_email'], service_account_info)
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
