import streamlit as st
import ee
import json
import geemap.foliumap as geemap
from google.oauth2 import service_account


# Load service account info from Streamlit secrets
service_account_info = dict(st.secrets["earthengine"])

SCOPES = ['https://www.googleapis.com/auth/earthengine']

# Create Google credentials object from service account info with the required scopes
credentials = service_account.Credentials.from_service_account_info(
    service_account_info, scopes=SCOPES)


# Initialize Earth Engine with these credentials
ee.Initialize(credentials)


# Title
st.title("GES-Coastal Monitor")

# Dropdown


# Create two columns: left for filters, right for map
col1, col2 = st.columns([1, 3])

# Filters on the left
with col1:
    st.subheader("Parameters")
    country_list = ['Lebanon', 'Jordan', 'Syria']
    country = st.selectbox("Select a country", country_list)
    landcover = st.multiselect("Land Cover", ["Forest", "Urban", "Water", "Agriculture"])
    year = st.slider("Year", 2000, 2025, 2020)

# Map on the right
with col2:
    st.subheader("Good Environmental Status")
    Map = geemap.Map()

    # Filter by country
    countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    filtered = countries.filter(ee.Filter.eq('country_na', country))

    # Add layer
    Map.addLayer(filtered, {}, country)
    Map.centerObject(filtered)

    # Display map
    Map.to_streamlit(height=600)
