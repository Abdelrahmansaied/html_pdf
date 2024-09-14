import streamlit as st
import time
import random
import pandas as pd
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PIL import Image
import tempfile
import io
import zipfile

# Configure Streamlit
st.set_page_config(page_title="HTML to PDF Converter", layout="wide")

# Function to close cookie consent pop-ups
def close_cookie_consent(driver):
    elem1 = driver.find_elements(By.XPATH, "//*[contains(text(), 'Accept')]")
    elem2 = driver.find_elements(By.XPATH, "//*[contains(text(), 'I accept')]")
    elements = elem1 + elem2     

    for element in elements:
        try:
            element.click()
            return True
        except Exception:
            continue
    return False

# Function to convert URLs to PDFs
def convert_urls_to_pdfs(urls, mpns):
    options = Options()
    options.add_argument("--headless")
    pdf_files = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)

        for i, url in enumerate(urls):
            try:
                driver.get(url)
                time.sleep(random.uniform(1, 3))
                close_cookie_consent(driver)
                time.sleep(random.uniform(1, 3))

                total_height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1920, total_height)

                # Capture screenshot and convert to PDF
                screenshot_path = f'{temp_dir}/screenshot_{i}.png'
                driver.save_screenshot(screenshot_path)
                pdf_buffer = io.BytesIO()
                image = Image.open(screenshot_path)
                image.convert('RGB').save(pdf_buffer, format='PDF')
                pdf_buffer.seek(0)

                # Prepare filename for saving
                pdf_filename = f'{mpns[i]}.pdf'
                pdf_files.append((pdf_filename, pdf_buffer))

            except Exception as e:
                st.error(f"Error processing {url}: {e}")

        driver.quit()
        return pdf_files

# Streamlit interface
st.title("HTML to PDF Converter")
st.write("Upload an Excel file containing URLs and MPNs.")

uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if 'URL' in df.columns and 'MPN' in df.columns:
        urls = df['URL'].dropna().tolist()
        mpns = df['MPN'].dropna().tolist()

        if st.button("Convert"):
            if urls:
                with st.spinner("Converting..."):
                    pdf_files = convert_urls_to_pdfs(urls, mpns)
                    st.success("Conversion completed!")

                    # Create a temporary zip file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as zip_file:
                        with zipfile.ZipFile(zip_file, 'w') as zf:
                            for pdf_filename, pdf_buffer in pdf_files:
                                pdf_buffer.seek(0)
                                zf.writestr(pdf_filename, pdf_buffer.read())

                    # Provide download link for the zip file
                    with open(zip_file.name, "rb") as f:
                        st.download_button(
                            label="Download All PDFs",
                            data=f,
                            file_name="converted_pdfs.zip",
                            mime="application/zip",
                        )

            else:
                st.warning("No valid URLs found in the Excel file.")
    else:
        st.error("Excel file must contain 'URL' and 'MPN' columns.")
