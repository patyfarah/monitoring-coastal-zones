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

# Custom CSS for two-column layout with colored backgrounds
st.markdown("""
    <style>
    .container {
        display: flex;
        gap: 2%;
    }
    .left-column {
        flex: 1;
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
    }
    .right-column {
        flex: 3;
        background-color: #e8f5e9;
        padding: 20px;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("GES-Coastal Monitor")

# Create two columns: left for filters, right for map
col1, col2 = st.columns([1, 3])

# Open custom container
st.markdown('<div class="container">', unsafe_allow_html=True)

# Filters on the left
with col1:
    with st.container():
        st.markdown('<div class="left-column">', unsafe_allow_html=True)
        st.subheader("Parameters")
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
        satellite_product = st.selectbox(
            "Satellite Product",
            ["Landsat 8", "Sentinel-2", "MODIS NDVI", "PlanetScope"]
        )
        st.markdown('</div>', unsafe_allow_html=True)
    

# Map on the right
with col2:
    with st.container():
        st.markdown('<div class="right-column">', unsafe_allow_html=True)
        st.subheader("Good Environmental Status")
        Map = geemap.Map(data_ctrl=False, toolbar_ctrl=False, draw_ctrl=False)
    
        # Filter by country
        countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
        filtered = countries.filter(ee.Filter.eq('country_na', country))
    
        # Add layer
        Map.addLayer(filtered, {}, country)
        Map.centerObject(filtered)
    
        # Display map
        Map.to_streamlit(height=400)
        st.markdown('</div>', unsafe_allow_html=True)
        
# Close main container
st.markdown('</div>', unsafe_allow_html=True)
