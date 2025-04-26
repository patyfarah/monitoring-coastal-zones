import ee

# Initialize the Earth Engine module
ee.Initialize()

# PARAMETERS
country_name = 'Lebanon'  # Example: replace with your country
start_date = '2022-01-01'
end_date = '2022-12-31'

# STEP 1: Load country boundary
countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
country = countries.filter(ee.Filter.eq('country_na', country_name)).geometry()

# STEP 2: Load MOD13A1 (NDVI) collection
mod13a1 = ee.ImageCollection('MODIS/006/MOD13A1') \
    .filterDate(start_date, end_date) \
    .filterBounds(country)

# STEP 3: Load MOD09GA (Surface Reflectance) for cloud info
mod09ga = ee.ImageCollection('MODIS/006/MOD09GA') \
    .filterDate(start_date, end_date) \
    .filterBounds(country)

# STEP 4: Function to mask clouds using MOD09GA's 'state_1km' band
def mask_clouds(image):
    # Read QA band
    qa = image.select('state_1km')
    
    # Extract bits 0-1 (cloud state)
    cloud_state = qa.bitwiseAnd(3)
    
    # 0: clear, 1: cloudy, 2: mixed
    clear_mask = cloud_state.eq(0)
    return image.updateMask(clear_mask)

# STEP 5: Apply cloud masking to MOD09GA and link with MOD13A1
mod09ga_clear = mod09ga.map(mask_clouds)

# Function to match MOD13A1 with corresponding MOD09GA cloud mask
def apply_clear_mask(mod13_img):
    # Find closest MOD09GA image by time
    date = mod13_img.date()
    mod09_nearest = mod09ga_clear.filterDate(
        date.advance(-8, 'day'), date.advance(8, 'day')
    ).sort('system:time_start').first()
    
    # Apply the cloud mask
    mod09_mask = ee.Image(mod09_nearest).select('state_1km')
    cloud_state = mod09_mask.bitwiseAnd(3)
    clear_mask = cloud_state.eq(0)
    
    return mod13_img.updateMask(clear_mask)

# STEP 6: Apply the mask to MOD13A1 collection
mod13a1_clear = mod13a1.map(apply_clear_mask)

# STEP 7: Filter images with less than 10% cloud
def filter_by_cloud(image):
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=country,
        scale=500,
        maxPixels=1e13
    )
    ndvi = stats.get('NDVI')
    return ee.Algorithms.If(ndvi, image, None)

mod13a1_final = mod13a1_clear.map(filter_by_cloud).filter(ee.Filter.notNull(['NDVI']))

# STEP 8: Visualize or Export
first_image = mod13a1_final.first()

# NDVI Visualization parameters
ndvi_vis = {
    'min': 0.0,
    'max': 9000.0,
    'palette': ['blue', 'white', 'green']
}

# Example: Print URL to view the first image
url = first_image.getThumbURL(ndvi_vis)
print('Preview URL:', url)

# Example: Export the collection
# You can use Export functions here if needed
