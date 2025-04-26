import ee
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Initialize Earth Engine
ee.Initialize()

# ---------------------------------
# FUNCTIONS
# ---------------------------------

# Get country geometry
@st.cache_data
def get_country_list():
    countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
    names = countries.aggregate_array('country_na').getInfo()
    names = sorted(list(set(names)))
    return names

def get_country_geometry(country_name):
    countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
    country = countries.filter(ee.Filter.eq('country_na', country_name)).first()
    return country.geometry()

def mask_mod13a1(image):
    qa = image.select('SummaryQA')
    mask = qa.eq(0)
    return image.updateMask(mask)

def mask_mod11a1(image):
    qc_day = image.select('QC_Day')
    mask = qc_day.bitwiseAnd(3).eq(0)
    return image.updateMask(mask)

def apply_cloud_mask(collection, dataset_name):
    if 'MOD13A1' in dataset_name:
        return collection.map(mask_mod13a1)
    elif 'MOD11A1' in dataset_name:
        return collection.map(mask_mod11a1)
    else:
        return collection

def filter_by_cloud_cover(collection, band_name, aoi, max_cloud_cover=10):
    def filter_image(image):
        valid = image.select(band_name).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=500,
            maxPixels=1e13
        ).get(band_name)
        return ee.Algorithms.If(ee.Number(valid).gt((100 - max_cloud_cover) / 100), image, None)

    return collection.map(filter_image).filter(ee.Filter.notNull([band_name]))

def extract_time_series(collection, band_name, aoi):
    def compute_mean(image):
        mean = image.select(band_name).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=500,
            maxPixels=1e13
        )
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'value': mean.get(band_name)
        })

    stats = collection.map(compute_mean).filter(ee.Filter.notNull(['value']))
    return stats

def ee_to_df(fc):
    data = fc.aggregate_array('date').getInfo()
    values = fc.aggregate_array('value').getInfo()
    df = pd.DataFrame({'date': pd.to_datetime(data), 'value': values})
    return df.sort_values('date')

def plot_time_series(df, title, y_label):
    fig, ax = plt.subplots(figsize=(12,6))
    ax.plot(df['date'], df['value'], marker='o', linestyle='-')
    ax.set_title(title, fontsize=16)
    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel(y_label, fontsize=14)
    ax.grid(True)
    st.pyplot(fig)

# ---------------------------------
# STREAMLIT APP
# ---------------------------------

st.set_page_config(page_title="NDVI and LST Time Series", layout="centered")

st.title("🌍 NDVI and LST Time Series Analysis")
st.markdown("Extract and plot vegetation (NDVI) and land surface temperature (LST) over any country!")

# Select parameters
country_list = get_country_list()
country_name = st.selectbox("Select a Country", country_list, index=country_list.index('Lebanon') if 'Lebanon' in country_list else 0)

col1, col2 = st.columns(2)
start_year = col1.number_input("Start Year", min_value=2000, max_value=2025, value=2020)
end_year = col2.number_input("End Year", min_value=2000, max_value=2025, value=2020)

# Button
if st.button("Run Analysis"):
    with st.spinner('Fetching data and generating plots...'):

        # Define dates
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"

        # Set datasets
        ndvi_dataset = 'MODIS/061/MOD13A1'
        lst_dataset = 'MODIS/061/MOD11A1'
        max_cloud_cover = 10  # %

        # Get AOI
        aoi = get_country_geometry(country_name)

        # Load collections
        ndvi_collection = ee.ImageCollection(ndvi_dataset).filterDate(start_date, end_date).filterBounds(aoi)
        lst_collection = ee.ImageCollection(lst_dataset).filterDate(start_date, end_date).filterBounds(aoi)

        # Apply cloud masks
        ndvi_masked = apply_cloud_mask(ndvi_collection, ndvi_dataset)
        lst_masked = apply_cloud_mask(lst_collection, lst_dataset)

        # Bands
        ndvi_band = 'NDVI'
        lst_band = 'LST_Day_1km'

        # Filter
        ndvi_final = filter_by_cloud_cover(ndvi_masked, ndvi_band, aoi, max_cloud_cover)
        lst_final = filter_by_cloud_cover(lst_masked, lst_band, aoi, max_cloud_cover)

        # Extract time series
        ndvi_stats = extract_time_series(ndvi_final, ndvi_band, aoi)
        lst_stats = extract_time_series(lst_final, lst_band, aoi)

        # Convert to dataframe
        df_ndvi = ee_to_df(ndvi_stats)
        df_lst = ee_to_df(lst_stats)
        df_lst['value'] = df_lst['value'] - 273.15  # Convert LST from Kelvin to Celsius

        # Plot
        st.subheader(f"NDVI Time Series for {country_name}")
        plot_time_series(df_ndvi, f"{country_name} NDVI ({start_year}-{end_year})", "NDVI")

        st.subheader(f"LST Time Series for {country_name}")
        plot_time_series(df_lst, f"{country_name} LST ({start_year}-{end_year})", "LST (°C)")

        st.success('Analysis complete!')


