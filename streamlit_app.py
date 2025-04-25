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
        start_year_val = st.number_input("Start", value=2002, key="start_year")
    with year_col2:
        end_year_val = st.number_input("End", value=2022, key="end_year")

    start_date = f"{int(start_year_val)}-01-01"
    end_date = f"{int(end_year_val)}-12-31"

    buffer_km = st.number_input("Coastal Buffer (km)", min_value=0, max_value=100, value=10)

    # Filter country geometry
    countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    filtered = countries.filter(ee.Filter.eq('country_na', country))
    
    ndvi_product = st.selectbox("NDVI Product", options=["MOD13A1"])
    lst_product = st.selectbox("LST Product", options=["MOD11A1"])

    ndvi_collections = {
        "MOD13A1": ee.ImageCollection("MODIS/061/MOD13A1").select("NDVI")
    }

    ndvi = (
        ndvi_collections[ndvi_product]
        .filterBounds(filtered)
        .filterDate(start_date, end_date)
    )

    lst_collections = {
        "MOD11A1": ee.ImageCollection("MODIS/061/MOD11A1").select("LST_Day_1km")
    }

    lst = (
        lst_collections[lst_product]
        .filterBounds(filtered)
        .filterDate(start_date, end_date)
    )
    ndvi_mean = ndvi.mean().clip(filtered)
    lst_mean = lst.mean().clip(filtered)

   # Define region of interest
    region = ndvi_mean.geometry()
    
    # Export function and button
    def export_ndvi_to_drive():
        task = ee.batch.Export.image.toDrive(
            image=ndvi_mean,
            description=f'{country}_NDVI_{start_date}_{end_date}',
            folder='earthengine',
            fileNamePrefix=f'{country}_NDVI_{start_date}_{end_date}',
            region= region,
            scale=250,
            fileFormat='GeoTIFF'
        )
        task.start()
        status = task.status()
        print(status)
        if status['state'] == 'READY':
            st.success("Export task started! Check Google Earth Engine tasks.")
        else:
            st.error(f"Export failed to start. Reason: {status}")
       
    
    if st.button("Export to Drive"):
        export_ndvi_to_drive()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Right Panel
with col2:
    st.subheader("Good Environmental Status")
    st.markdown('<div class="right-column">', unsafe_allow_html=True)

    Map = geemap.Map(center=[33.89, 35.5], zoom=6, draw_ctrl=False, data_ctrl=False, toolbar_ctrl=False)

    # Add layers
    Map.addLayer(ndvi_mean, {'min': 0, 'max': 9000, 'palette': ['white', 'green']}, 'Mean NDVI',shown=False)
    Map.addLayer(lst_mean, {'min': 0, 'max': 9000, 'palette': ['white', 'red']}, 'Mean LST',shown=False)
    
    Map.addLayer(filtered.style(**{
    "color": "black",
    "fillColor": "00000000",  # Transparent fill
    "width": 2
    }), {}, f"{country} Border")
    Map.centerObject(filtered)

    Map.to_streamlit(height=500)

    st.markdown('</div>', unsafe_allow_html=True)

