#-------------------------------------------------------
# Libraries
#-------------------------------------------------------
import streamlit as st
import ee
import geemap.foliumap as geemap
from google.oauth2 import service_account
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely.geometry import shape
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
  'min': 0.0,
  'max': 9000.0,
  'palette': [
    'ffffff', 'ce7e45', 'df923d', 'f1b555', 'fcd163', '99b718', '74a901',
    '66a000', '529400', '3e8601', '207401', '056201', '004c00', '023b01',
    '012e01', '011d01', '011301'
  ],
}

vis_params = {
    'min': -1.0,
    'max': 1.0,
    'palette': ['grey', 'yellow', 'green']
}

lst_params = {
    'min': 12,
    'max': 52,
    'palette': ['blue', 'green', 'yellow', 'red']
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
        start_year_val = st.number_input("Start", value=2002, key="start_year")
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
    ndvi_mean = ndvi.median().clip(outer_band) 
    lst_mean = lst.mean().clip(outer_band)

    # Normalize NDVI and LST
    ndvi_minmax = ndvi_mean.reduceRegion(
        reducer=ee.Reducer.minMax(), geometry=outer_band, scale=250, maxPixels=1e13
    )
    ndvi_min = ee.Number(ndvi_minmax.get('NDVI_min'))
    ndvi_max = ee.Number(ndvi_minmax.get('NDVI_max'))
    
    lst_minmax = lst_mean.reduceRegion(
        reducer=ee.Reducer.minMax(), geometry=outer_band, scale=250, maxPixels=1e13
    )
    lst_min = ee.Number(lst_minmax.get('LST_Day_1km_min'))
    lst_max = ee.Number(lst_minmax.get('LST_Day_1km_max'))
    
    # Normalize NDVI and LST
    ndvi_normal = ndvi_mean.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min))
    lst_normal = lst_mean.subtract(lst_min).divide(lst_max.subtract(lst_min))
    
    # Calculate GES
    GES = ndvi_normal.multiply(0.5).add(lst_normal.multiply(0.5))

    # 5 classes (equal intervals)
    GES_class = GES.multiply(100).int() \
        .where(GES.lte(0.2), 1) \
        .where(GES.gt(0.2).And(GES.lte(0.4)), 2) \
        .where(GES.gt(0.4).And(GES.lte(0.6)), 3) \
        .where(GES.gt(0.6).And(GES.lte(0.8)), 4) \
        .where(GES.gt(0.8), 5)

        
    if st.button("Export to Drive"):
        export_ndvi_to_drive()
  
    st.markdown('</div>', unsafe_allow_html=True)

# Right Panel
with col2:
    st.subheader("Good Environmental Status")
    st.markdown('<div class="right-column">', unsafe_allow_html=True)
   
    Map = geemap.Map(zoom=6,draw_ctrl = True, data_ctrl=True)
   
    Map.addLayer(ndvi_mean, vis_params, 'Mean NDVI', shown=False)
    Map.addLayer(lst_mean, lst_params, 'Mean LST', shown=False)
    Map.addLayer(filtered.style(**{
        "color": "black",
        "fillColor": "00000000",
        "width": 2
    }), {}, f"{country} Border")
    
    Map.centerObject(filtered)
    if st.toggle("Draw Mode"):
        # Add draw control
        draw = Draw(
            export=False,
            draw_options={
                "polyline": False,
                "polygon": True,
                "circle": False,
                "rectangle": True,
                "marker": False,
            },
            edit_options={"edit": True}
        )
        draw.add_to(Map)

    # Show the map and capture draw events
    with st.expander("Click to open map and draw", expanded=False):
        st_data = st_folium(Map, height=300, width=500, returned_objects=["last_draw"])

    # Handle draw result
    if st_data.get("last_draw") is not None:
        geometry = st_data["last_draw"]["geometry"]
        ee_geom = geemap.geojson_to_ee(geometry)
        clipped = GES.clip(ee_geom)
    
    Map.to_streamlit(height=500)
   
    st.markdown('</div>', unsafe_allow_html=True)



