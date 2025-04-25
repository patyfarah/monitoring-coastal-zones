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

    # Year range on same line
    st.markdown("**Year Range**")
    year_col1, year_col2 = st.columns(2)
    with year_col1:
        start_year = st.number_input("Start", value=1984, key="start_year")
    with year_col2:
        end_year = st.number_input("End", value=2025, key="end_year")

    # Coastal buffer input
    buffer_km = st.number_input("Coastal Buffer (km)", min_value=0, max_value=100, value=10)

    # Unified Satellite product selector
    st.markdown("**Satellite Product**")
    ndvi_product = st.selectbox(
        label="",  # No label inside the selectbox
        options=["NDVI MOD13A1"]
    )
    lst_product = st.selectbox(
    label="",  # No label inside the selectbox
    options=["LST MOD11A1"]
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

        # Example image to export (replace with your actual NDVI/LST computation)
    image = ee.Image("MODIS/006/MOD13A1").select("NDVI").first()

    # Set export region (you can refine it to the country bounds)
    region = filtered.geometry()

    # Export to Google Drive
    if st.button("Export to Drive"):
        task = ee.batch.Export.image.toDrive(
            image=image,
            description='GES_Export_Image',
            folder='EarthEngineExports',
            fileNamePrefix='GES_Result',
            region=region,
            scale=500,
            maxPixels=1e13
        )
        task.start()
        st.success("Export task started! Check your Google Drive shortly.")

    st.markdown('</div>', unsafe_allow_html=True)
        
