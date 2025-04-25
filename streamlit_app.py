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

    # --- Define date range ---
    start_year = f"{start_year}-01-01"
    end_year = f"{end_year}-12-31"

    # Coastal buffer input
    buffer_km = st.number_input("Coastal Buffer (km)", min_value=0, max_value=100, value=10)

    # Unified Satellite product selector
    st.markdown("**Satellite Product**")
    ndvi_product = st.selectbox(
        label="",  # No label inside the selectbox
        options=["MOD13A1"]
    )
    lst_product = st.selectbox(
    label="",  # No label inside the selectbox
    options=["MOD11A1"]
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

    # --- Load NDVI image collection based on selected product ---
    ndvi_collections = {
        "MOD13A1": ee.ImageCollection("MODIS/061/MOD13A1").select("NDVI")
    }

    ndvi = ndvi_collections[ndvi_product]
    .filterBounds(country)
    .filterDate(start_date, end_date)

    ndvi_mean = ndvi.mean().clip(country)
    
    # Add layer
    Map.addLayer(ndvi.mean().clip(country), {'min': 0, 'max': 9000, 'palette': ['white', 'green']}, 'Mean NDVI')
    Map.addLayer(filtered, {}, country)
    Map.centerObject(filtered)

    # Display map
    Map.to_streamlit(height=400)

   # --- Export function ---
def export_ndvi_to_drive(_):
    task = ee.batch.Export.image.toDrive(
        image=ndvi_mean,
        description=f'{country_name}_NDVI_{start_year}_{end_year}',
        folder='EarthEngine',
        fileNamePrefix=f'{country_name}_NDVI_{start_year}_{end_year}',
        region=country,
        scale=250,  # adjust according to product resolution
        maxPixels=1e13
    )
    task.start()
    print(f"Export task started for {country_name} NDVI ({start_year}-{end_year}) to Google Drive.")

    # --- Export button ---
    export_button = widgets.Button(description="Export NDVI to Drive")
    export_button.on_click(export_ndvi_to_drive)
    display(export_button)

    st.markdown('</div>', unsafe_allow_html=True)
        
