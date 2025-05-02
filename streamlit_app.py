#-------------------------------------------------------
# Libraries
#-------------------------------------------------------
import streamlit as st
import ee
import geemap.foliumap as geemap
from google.oauth2 import service_account
import gc
#--------------------------------------------------------
# Initialization
#-------------------------------------------------------
# Load service account info from Streamlit secrets
service_account_info = dict(st.secrets["earthengine"])

SCOPES = ['https://www.googleapis.com/auth/earthengine']

# Create Google credentials object
credentials = service_account.Credentials.from_service_account_info(
    service_account_info, scopes=SCOPES)

# Initialize Earth Engine
ee.Initialize(credentials)

#--------------------------------------------------------------
# Variables and Definitions
#--------------------------------------------------------------
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

# Visualization parameters for NDVI and LST
vis_params = {
    'min': 0,
    'max': 100,
    'palette': [
      "#000080",  # 0–10: Water / Built-up (Navy Blue)
      "#654321",  # 10–20: Barren / Dry Soil (Dark Brown)
      "#A0522D",  # 20–30: Sparse Vegetation (Sienna Brown)
      "#DAA520",  # 30–40: Dry Grass (Goldenrod)
      "#ADFF2F",  # 40–50: Transition Zone (Green Yellow)
      "#7CFC00",  # 50–60: Light Vegetation (Lawn Green)
      "#32CD32",  # 60–70: Moderate Vegetation (Lime Green)
      "#228B22",  # 70–80: Healthy Vegetation (Forest Green)
      "#006400",  # 80–90: Dense Vegetation (Dark Green)
      "#004B23"   # 90–100: Very Lush Vegetation (Deep Forest Green)
  ]
}

lst_params = {
    'min': 0,
    'max': 100,
    'palette': [
    "#0000FF",  # 0–10: Deep Blue (Very Cold)
    "#3399FF",  # 10–20: Sky Blue (Cold)
    "#66CCFF",  # 20–30: Light Blue
    "#66FF66",  # 30–40: Light Green
    "#CCFF66",  # 40–50: Yellow Green
    "#FFFF00",  # 50–60: Yellow (Moderate)
    "#FFCC00",  # 60–70: Orange Yellow (Warm)
    "#FF9900",  # 70–80: Orange (Hot)
    "#FF3300",  # 80–90: Red Orange (Very Hot)
    "#990000"   # 90–100: Dark Red (Extreme Heat)
    ]
}

ges_params  = {
    'min': 0,
    'max': 100,
    'palette': [
    "#800000",  # Very Low - Severe Stress
    "#FF4500",  # Low - Stressed
    "#FFD700",  # Moderate - Transitional
    "#9ACD32",  # High - Healthy
    "#228B22"   # Very High - Very Healthy
    ],
    'labels': ['1:Degraded' , '2: Vulnerable', '3: Moderate', '4: Stable', '5:Healthy']
}

def mask_lst(image):
    qc = image.select('QC_Day')
    good_mask = qc.lte(1)  # QC_Day <= 1 indicates good quality

    lst_celsius = image.select('LST_Day_1km') \
                       .updateMask(good_mask) \
                       .multiply(0.02) \
                       .subtract(273.15) \
                       .copyProperties(image, ['system:time_start'])

    return lst_celsius


def mask_ndvi(image):
    qa = image.select('SummaryQA')
    good = qa.lte(1)  
    ndvi = image.select('NDVI').multiply(0.0001)
    return ndvi.updateMask(good)

def get_image_collection(collection_dict, product, region, start_date, end_date, mask_func):
    collection = (
        collection_dict[product]
        .filterBounds(region)
        .filterDate(start_date, end_date)
    )
    
    collection = collection.map(mask_func)
    return collection



#---------------------------------------------------------------
# Streamlit Structure
#--------------------------------------------------------------
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
        start_year_val = st.number_input("Start", value=2022, key="start_year")
    with year_col2:
        end_year_val = st.number_input("End", value=2022, key="end_year")

    start_date = f"{int(start_year_val)}-01-01"
    end_date = f"{int(end_year_val)}-12-31"

    buffer_km = st.number_input("Coastal Buffer (km)", min_value=1, max_value=100, value=10)

    # Filter country geometry
    countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    filtered = countries.filter(ee.Filter.eq('country_na', country))
    region_geom = filtered.geometry()
    buffered = region_geom.buffer(-buffer_km * 1000)
    outer_band =region_geom.difference(buffered)

   
    ndvi_product = st.selectbox("NDVI Product", options=["MOD13A1"])
    lst_product = st.selectbox("LST Product", options=["MOD11A1"])
    
   # Define region of interest
    region = filtered.geometry()  
    
    NDVI_PRODUCTS = {"MOD13A1": ee.ImageCollection("MODIS/061/MOD13A1")}
    LST_PRODUCTS = {"MOD11A1": ee.ImageCollection("MODIS/061/MOD11A1")}
    
    ndvi = get_image_collection(
        NDVI_PRODUCTS, ndvi_product, region, start_date, end_date, mask_ndvi
    )
    
    lst = get_image_collection(
        LST_PRODUCTS, lst_product, region, start_date, end_date, mask_lst
    )
    
    
    # Mean data
    ndvi_mean = ndvi.mean().clip(outer_band) 
    lst_mean = lst.mean().clip(outer_band)

    # Normalize NDVI and LST
    ndvi_minmax = ndvi_mean.reduceRegion(
        reducer=ee.Reducer.minMax(), geometry=outer_band, scale=1000, maxPixels=1e13
    )
    ndvi_min = ee.Number(ndvi_minmax.get('NDVI_min'))
    ndvi_max = ee.Number(ndvi_minmax.get('NDVI_max'))
    
    lst_minmax = lst_mean.reduceRegion(
        reducer=ee.Reducer.minMax(), geometry=outer_band, scale=1000, maxPixels=1e13
    )
    lst_min = ee.Number(lst_minmax.get('LST_Day_1km_min'))
    lst_max = ee.Number(lst_minmax.get('LST_Day_1km_max'))
    
    # Normalize NDVI and LST
    ndvi_normal = ndvi_mean.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)).multiply(100)
    lst_normal = lst_mean.subtract(lst_min).divide(lst_max.subtract(lst_min)).multiply(100)

    # Cleanup large variables to free memory
    del ndvi, lst, ndvi_minmax, lst_minmax
    gc.collect()
    
    # Calculate GES
    GES = ndvi_normal.multiply(0.5).add(lst_normal.multiply(0.5))

    lst_valid_mask = lst_mean.mask()  # Areas where LST is valid
    GES = GES.updateMask(lst_valid_mask)  # Keep only valid areas

    # 5 classes (equal intervals)
    GES_class = GES.multiply(100).int() \
        .where(GES.lte(20), 1) \
        .where(GES.gt(20).And(GES.lte(40)), 2) \
        .where(GES.gt(40).And(GES.lte(60)), 3) \
        .where(GES.gt(60).And(GES.lte(80)), 4) \
        .where(GES.gt(80), 5)

    
    if st.button("Export to Drive"):
        export_ndvi_to_drive()
  
    st.markdown('</div>', unsafe_allow_html=True)

# Right Panel
with col2:
    st.subheader("Good Environmental Status")
    st.markdown('<div class="right-column">', unsafe_allow_html=True)

    Map = geemap.Map(zoom=6, draw_ctrl=False, data_ctrl=True)

    # Add mean NDVI and LST layers (optional, hidden by default)
    Map.addLayer(ndvi_normal, vis_params, 'Mean NDVI', shown=False)
    Map.addLayer(lst_normal, lst_params, 'Mean LST', shown=False)
    Map.addLayer(GES_class,ges_params, 'GES Classification', shown=True)

    # Add country border
    Map.addLayer(filtered.style(**{
        "color": "black",
        "fillColor": "00000000",
        "width": 2
    }), {}, f"{country} Border")

    # Center the map and render
        
    # Cleanup large variables to free memory
    del ndvi_normal, lst_normal, GES, GES_class,lst_mean, ndvi_mean
    gc.collect() 
    
    Map.centerObject(filtered)
    Map.to_streamlit(height=500)

    st.markdown('</div>', unsafe_allow_html=True)




