import streamlit as st
import ee
import json
import geemap.foliumap as geemap
from google.oauth2 import service_account

# Load service account info from Streamlit secrets
service_account_info = dict(st.secrets["earthengine"])

SCOPES = ['https://www.googleapis.com/auth/earthengine']

# Create Google credentials object
credentials = service_account.Credentials.from_service_account_info(
    service_account_info, scopes=SCOPES)

# Initialize Earth Engine
ee.Initialize(credentials)

# Title
st.title("GES-Coastal Monitor")

# Create layout
col1, col2 = st.columns([1, 3])

# Left Panel
with col1:
    st.subheader("Parameters")
    st.markdown('<div class="left-column">', unsafe_allow_html=True)

    country = st.selectbox(
        "Select Country",
        ["Morocco", "Algeria", "Tunisia", "Libya", "Arab Republic of Egypt", "Syrian Arab Republic", "Lebanon", "Yemen", "Mauritania"]
    )

    st.markdown("**Year Range**")
    year_col1, year_col2 = st.columns(2)
    with year_col1:
        start_year_val = st.number_input("Start", value=1984, key="start_year")
    with year_col2:
        end_year_val = st.number_input("End", value=2025, key="end_year")

    start_date = f"{int(start_year_val)}-01-01"
    end_date = f"{int(end_year_val)}-12-31"

    buffer_km = st.number_input("Coastal Buffer (km)", min_value=0, max_value=100, value=10)

    ndvi_product = st.selectbox("Satellite Product", options=["MOD13A1"])
    lst_product = st.selectbox("", options=["MOD11A1"])

    st.markdown('</div>', unsafe_allow_html=True)

# Right Panel
with col2:
    st.subheader("Good Environmental Status")
    st.markdown('<div class="right-column">', unsafe_allow_html=True)

    Map = geemap.Map(center=[33.89, 35.5], zoom=6, draw_ctrl=False, data_ctrl=False, toolbar_ctrl=False)

    # Filter country geometry
    countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    filtered = countries.filter(ee.Filter.eq('country_na', country))

    ndvi_collections = {
        "MOD13A1": ee.ImageCollection("MODIS/061/MOD13A1").select("NDVI")
    }

    ndvi = (
        ndvi_collections[ndvi_product]
        .filterBounds(filtered)
        .filterDate(start_date, end_date)
    )

    ndvi_mean = ndvi.mean().clip(filtered)

    # Add layers
    Map.addLayer(ndvi_mean, {'min': 0, 'max': 9000, 'palette': ['white', 'green']}, 'Mean NDVI')
    Map.addLayer(filtered, {}, country)
    Map.centerObject(filtered)

    Map.to_streamlit(height=400)

    st.markdown('</div>', unsafe_allow_html=True)

# Export function and button
def export_ndvi_to_drive():
    task = ee.batch.Export.image.toDrive(
        image=ndvi_mean,
        description=f'{country}_NDVI_{start_date}_{end_date}',
        folder='EarthEngine',
        fileNamePrefix=f'{country}_NDVI_{start_date}_{end_date}',
        region=filtered.geometry().bounds().getInfo()['coordinates'],
        scale=250,
        maxPixels=1e13
    )
    task.start()
    st.success(f"Export task started for {country} NDVI ({start_date} to {end_date})")

if st.button("Export NDVI to Google Drive"):
    export_ndvi_to_drive()
