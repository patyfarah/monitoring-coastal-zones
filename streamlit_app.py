import streamlit as st
import ee
import geemap.foliumap as geemap
from google.oauth2 import service_account
import matplotlib.pyplot as plt
import datetime


# -----------------------
# Initialization
# -----------------------
SCOPES = ['https://www.googleapis.com/auth/earthengine']
def initialize_ee():
    service_account_info = dict(st.secrets["earthengine"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)
    ee.Initialize(credentials)


# -----------------------
# Constants and Settings
# -----------------------


COUNTRIES = [
    "Morocco", "Algeria", "Tunisia", "Libya", "Arab Republic of Egypt",
    "Syrian Arab Republic", "Lebanon", "Yemen", "Mauritania"
]
NDVI_PRODUCTS = {"MOD13A1": ee.ImageCollection("MODIS/061/MOD13A1").select("NDVI")}
LST_PRODUCTS = {"MOD11A1": ee.ImageCollection("MODIS/061/MOD11A1").select("LST_Day_1km")}

NDVI_VIS = {
    'min': 0,
    'max': 9000,
    'palette': [
        'ffffff', 'ce7e45', 'df923d', 'f1b555', 'fcd163', '99b718', '74a901',
        '66a000', '529400', '3e8601', '207401', '056201', '004c00', '023b01',
        '012e01', '011d01', '011301'
    ]
}

LST_VIS = {
    'min': 13000.0,
    'max': 16500.0,
    'palette': [
        '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6', '0602ff',
        '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef', '3be285', '3ff38f',
        '86e26f', '3ae237', 'b5e22e', 'd6e21f', 'fff705', 'ffd611', 'ffb613',
        'ff8b13', 'ff6e08', 'ff500d', 'ff0000', 'de0101', 'c21301', 'a71001',
        '911003'
    ]
}



# -----------------------
# Helper Functions
# -----------------------

def filter_country(country_name, buffer_km):
    countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    filtered = countries.filter(ee.Filter.eq('country_na', country_name))
    region_geom = filtered.geometry()
    buffered = region_geom.buffer(-buffer_km * 1000)
    outer_band = region_geom.difference(buffered)
    return filtered, region_geom, outer_band

def mask_lst(image):
    qc = image.select('QC_Day')
    good = qc.eq(0)
    return image.updateMask(good)

def mask_ndvi(image):
    qa = image.select('SummaryQA')
    good = qa.lte(1)
    return image.updateMask(good)

def get_image_collection(collection_dict, product, region, start_date, end_date, mask_func=None):
    collection = (
        collection_dict[product]
        .filterBounds(region)
        .filterDate(start_date, end_date)
    )
    if mask_func:
        collection = collection.map(mask_func)
    return collection

def export_to_drive(image, description, region):
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder='earthengine',
        fileNamePrefix=description,
        region=region.bounds(),
        scale=250,
        fileFormat='GeoTIFF'
    )
    task.start()
    return task.status()

def create_map(filtered, ndvi_mean, lst_mean, selected_layers):
    Map = geemap.Map(zoom=6, draw_ctrl=True)

    if "Mean NDVI" in selected_layers:
        Map.addLayer(ndvi_mean, NDVI_VIS, 'Mean NDVI', shown=True)
        Map.add_colorbar(NDVI_VIS, label="NDVI", layer_name="Mean NDVI", orientation="vertical")

    if "Mean LST" in selected_layers:
        Map.addLayer(lst_mean, LST_VIS, 'Mean LST', shown=True)
        Map.add_colorbar(LST_VIS, label="LST (°C)", layer_name="Mean LST", orientation="vertical")

    Map.addLayer(filtered.style(**{
        "color": "black",
        "fillColor": "00000000",
        "width": 2
    }), {}, "Country Border")

    Map.centerObject(filtered)
    return Map

# -----------------------
# Main App
# -----------------------

def main():
    st.title("GES-Coastal Monitor")
    initialize_ee()

    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Parameters")
        st.markdown('<div class="left-column">', unsafe_allow_html=True)

        country = st.selectbox("Select Country", COUNTRIES)

        st.markdown("**Year Range**")
        year_col1, year_col2 = st.columns(2)
        start_year = year_col1.number_input("Start", value=2002, key="start_year")
        end_year = year_col2.number_input("End", value=2022, key="end_year")

        start_date = f"{int(start_year)}-01-01"
        end_date = f"{int(end_year)}-12-31"

        buffer_km = st.number_input("Coastal Buffer (km)", min_value=0, max_value=100, value=10)

        ndvi_product = st.selectbox("NDVI Product", options=list(NDVI_PRODUCTS.keys()))
        lst_product = st.selectbox("LST Product", options=list(LST_PRODUCTS.keys()))

        filtered, region_geom, outer_band = filter_country(country, buffer_km)

        ndvi = get_image_collection(
            NDVI_PRODUCTS, ndvi_product, filtered, start_date, end_date, mask_func=mask_ndvi
        )

        lst = get_image_collection(
            LST_PRODUCTS, lst_product, filtered, start_date, end_date, mask_func=mask_lst
        )

        ndvi_mean = ndvi.mean().clip(outer_band)

        modcel = lst.map(lambda img: img
                         .multiply(0.02)
                         .subtract(273.15)
                         .copyProperties(img, ['system:time_start']))

        lst_mean = modcel.mean().clip(outer_band)

        if st.button("Export to Drive"):
            status = export_to_drive(
                image=ndvi_mean,
                description=f"{country}_NDVI_{start_date}_{end_date}",
                region=region_geom
            )
            if status['state'] == 'READY':
                st.success("Export task started! Check Earth Engine Tasks.")
            else:
                st.error(f"Export failed to start: {status}")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.subheader("Good Environmental Status")
        st.markdown('<div class="right-column">', unsafe_allow_html=True)

        selected_layers = st.multiselect(
            "Select Layers to Display",
            ["Mean NDVI", "Mean LST"],
            default=["Mean NDVI", "Mean LST"]
        )

        Map = create_map(filtered, ndvi_mean, lst_mean, selected_layers)
        Map.to_streamlit(height=500)

        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
