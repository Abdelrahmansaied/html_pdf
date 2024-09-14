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
import boto3
import os

# AWS S3 configuration
AWS_ACCESS_KEY = 'AKIA5MVDKQBEDJMHPL6K'
AWS_SECRET_KEY = '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'
S3_BUCKET_NAME = '1abdo'

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
            return True  # Consent pop-up was closed
        except Exception:
            continue
    return False  # No consent element found

# Function to upload file to S3
def upload_to_s3(file_buffer, filename):
    s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY,
                              aws_secret_access_key=AWS_SECRET_KEY)
    s3_client.upload_fileobj(file_buffer, S3_BUCKET_NAME, filename)

# Function to convert URLs to PDFs
def convert_urls_to_pdfs(urls, mpns):
    options = Options()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')

    pdf_buffers = []
    with tempfile.TemporaryDirectory() as temp_dir:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)

        for i, url in enumerate(urls):
            try:
                driver.get(url)
                time.sleep(random.uniform(1, 3))
                close_cookie_consent(driver)
                time.sleep(random.uniform(1, 3))

                driver.execute_script("document.body.style.zoom='110%';")
                time.sleep(random.uniform(1, 3))

                total_height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1920, total_height)

                # Capture screenshot and convert to PDF
                screenshot_path = f'{temp_dir}/screenshot_{i}.png'
                driver.save_screenshot(screenshot_path)
                image = Image.open(screenshot_path)

                pdf_buffer = io.BytesIO()
                image.convert('RGB').save(pdf_buffer, format='PDF')
                pdf_buffer.seek(0)

                # Upload to S3
                filename = f'{mpns[i]}.pdf'
                upload_to_s3(pdf_buffer, filename)
                pdf_buffers.append(f's3://{S3_BUCKET_NAME}/{filename}')

            except Exception as e:
                st.error(f"Error processing {url}: {e}")
                continue

        driver.quit()
        return pdf_buffers

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
                    pdf_buffers = convert_urls_to_pdfs(urls, mpns)
                    st.success("Conversion completed!")

                    # Provide a download link for all PDFs in S3
                    st.subheader("Download Links:")
                    for filename in pdf_buffers:
                        download_link = f'<a href="{filename}" target="_blank">Download {os.path.basename(filename)}</a>'
                        st.markdown(download_link, unsafe_allow_html=True)

            else:
                st.warning("No valid URLs found in the Excel file.")
    else:
        st.error("Excel file must contain 'URL' and 'MPN' columns.")
