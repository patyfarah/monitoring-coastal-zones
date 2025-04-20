import streamlit as st
import ee
import json
import geemap.foliumap as geemap
from google.oauth2 import service_account


# Load service account info from Streamlit secrets
service_account_info = dict(st.secrets["earthengine"])

# Create Google credentials object from service account info
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# Initialize Earth Engine with these credentials
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
