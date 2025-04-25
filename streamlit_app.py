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

# Create two columns: left for filters, right for map
col1, col2 = st.columns([1, 3])

# Filters on the left
with col1:
    st.subheader("Parameters")
    st.markdown('<div class="left-column">', unsafe_allow_html=True)
    # Country selector
    country = st.selectbox(
        "Select Country",
        ["Morocco", "Algeria", "Tunisia", "Libya", "Arab Republic of Egypt", "Syrian Arab Republic", "Lebanon", "Yemen", "Mauritania"]
    )

    # Year range inputs
    start_year = st.number_input("Start Year",value=1984)
    end_year = st.number_input("End Year",value=2025)

    # Coastal buffer input
    buffer_km = st.number_input("Coastal Buffer (km)", min_value=0, max_value=100, value=10)

    # Satellite product selector
    NDVI_product = st.selectbox(
        "Satellite Product",
        ["NDVI MOD13A1"]
    )
    LST_product = st.selectbox(
    ["LST MOD11A1"]
    )
    st.markdown('</div>', unsafe_allow_html=True)
    

# Map on the right
with col2:
    
    st.subheader("Good Environmental Status")
    st.markdown('<div class="right-column">', unsafe_allow_html=True)
    Map = geemap.Map(center=[33.89, 35.5], zoom=6,draw_ctrl=False, data_ctrl=False, toolbar_ctrl=False)

    # Filter by country
    countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    filtered = countries.filter(ee.Filter.eq('country_na', country))

    # Add layer
    Map.addLayer(filtered, {}, country)
    Map.centerObject(filtered)

    # Display map
    Map.to_streamlit(height=400)
    st.markdown('</div>', unsafe_allow_html=True)
        
