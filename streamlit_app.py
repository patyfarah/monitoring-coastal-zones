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
        start_year_val = st.number_input("Start", value=2024, key="start_year")
    with year_col2:
        end_year_val = st.number_input("End", value=2024, key="end_year")

    start_date = f"{int(start_year_val)}-01-01"
    end_date = f"{int(end_year_val)}-12-31"

    buffer_km = st.number_input("Coastal Buffer (km)", min_value=0, max_value=100, value=10)

    # Filter country geometry
    countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    filtered = countries.filter(ee.Filter.eq('country_na', country))
    region_geom = filtered.geometry()
    buffered = region_geom.buffer(-buffer_km * 1000)
    outer_band =region_geom.difference(buffered)
    
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
    ndvi_mean = ndvi.mean().clip(outer_band)
    lst_mean = lst.mean().clip(outer_band)

   # Define region of interest
    region = filtered.geometry()
    
    # Export function and button
    def export_ndvi_to_drive():
        task = ee.batch.Export.image.toDrive(
            image=ndvi_mean,
            description=f'{country}_NDVI_{start_date}_{end_date}',
            folder='earthengine',
            fileNamePrefix=f'{country}_NDVI_{start_date}_{end_date}',
            region=region_geom.bounds().getInfo()['coordinates'],
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
      
    Map = geemap.Map(zoom=6, draw_ctrl=False)
    
    # Vis Param
    lstVis = {
      'min': 13000.0,
      'max': 16500.0,
      'palette': [
        '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
        '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
        '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
        'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
        'ff0000', 'de0101', 'c21301', 'a71001', '911003'
      ],
    }

    ndviVis = {
      'min': 0,
      'max': 9000,
      'palette': [
        'ffffff', 'ce7e45', 'df923d', 'f1b555', 'fcd163', '99b718', '74a901',
        '66a000', '529400', '3e8601', '207401', '056201', '004c00', '023b01',
        '012e01', '011d01', '011301'
      ],
    }
    
    # Add layers
    Map.addLayer(ndvi_mean, ndviVis, 'Mean NDVI',shown=False)
    Map.addLayer(lst_mean, lstVis, 'Mean LST',shown=False)
    Map.addLayer(filtered.style(**{
    "color": "black",
    "fillColor": "00000000",  # Transparent fill
    "width": 2
    }), {}, f"{country} Border")

    Map.centerObject(filtered)
    Map.to_streamlit(height=500)

    st.markdown('</div>', unsafe_allow_html=True)
