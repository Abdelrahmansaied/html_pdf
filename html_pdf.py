import streamlit as st
import time
import pandas as pd
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from PIL import Image
import tempfile
import io
import zipfile
import os

# Configure Streamlit
st.set_page_config(page_title="Excel URL to PDF Converter", layout="wide")

# Function to convert URLs to PDFs
def convert_urls_to_pdfs(urls, mpns):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")  # Headless mode for server
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration

    pdf_paths = []  # To store file paths for the zip
    with tempfile.TemporaryDirectory() as temp_dir:
        service = Service(executable_path='chromedriver')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options)
        
        for i, url in enumerate(urls):
            try:
                driver.get(url)
                time.sleep(5)  # Wait for the page to load

                # Set the window size to the full page size
                driver.set_window_size(1920, 1080)  # Adjust as needed
                time.sleep(2)  # Allow time for resizing

                # Get the full height of the page
                total_height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1920, total_height)  # Resize the window to capture the full page

                # Capture the full page as an image
                screenshot_path = f'{temp_dir}/screenshot_{i}.png'
                driver.save_screenshot(screenshot_path)
                image = Image.open(screenshot_path)

                # Save the image to a PDF
                pdf_path = f'{temp_dir}/{mpns[i].replace("/", "_").replace("\\", "_")}.pdf'
                image.convert('RGB').save(pdf_path)

                # Store the PDF path for zipping later
                pdf_paths.append(pdf_path)

            except Exception as e:
                st.error(f"Error processing {url}: {e}")
                continue

        driver.quit()
        return pdf_paths

# Streamlit interface
st.title("Excel URL to PDF Converter")
st.write("Upload an Excel file containing URLs and MPNs.")

# Upload Excel file
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file:
    # Read the Excel file
    df = pd.read_excel(uploaded_file)
    
    # Check for required columns
    if 'URL' in df.columns and 'MPN' in df.columns:
        urls = df['URL'].dropna().tolist()
        mpns = df['MPN'].dropna().tolist()

        if st.button("Convert"):
            if urls:
                with st.spinner("Converting..."):
                    pdf_paths = convert_urls_to_pdfs(urls, mpns)
                    st.success("Conversion completed!")

                    # Create a zip file to download all PDFs
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for pdf_path in pdf_paths:
                            zip_file.write(pdf_path, arcname=os.path.basename(pdf_path))  # Use only the filename

                    zip_buffer.seek(0)  # Move to the beginning of the buffer

                    # Provide a download button for the zip file
                    st.download_button(
                        label="Download All PDFs as a ZIP File",
                        data=zip_buffer,
                        file_name="pdfs.zip",
                        mime='application/zip'
                    )
            else:
                st.warning("No valid URLs found in the Excel file.")
    else:
        st.error("Excel file must contain 'URL' and 'MPN' columns.")
