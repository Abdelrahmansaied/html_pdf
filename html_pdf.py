import streamlit as st
import time
import random
import pandas as pd
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PIL import Image
import tempfile
import io

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
            print(f"Clicked on: {element.text}")  # Debugging output
            return True  # Consent pop-up was closed
        except Exception as e:
            print(f"Error clicking element: {e}")  # Handle exceptions
            continue
    return False  # No consent element found

# Function to convert URLs to PDFs
def convert_urls_to_pdfs(urls, mpns):
    options = Options()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    options.add_argument('--headless')  # Comment this out if you want to see the browser
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-certificate-errors')

    pdf_buffers = []
    with tempfile.TemporaryDirectory() as temp_dir:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        for i, url in enumerate(urls):
            try:
                driver.get(url)
                time.sleep(random.uniform(1, 3))  # Wait for the page to load
                close_cookie_consent(driver)
                time.sleep(random.uniform(1, 3))  # Wait for a while after consent closure

                driver.execute_script("document.body.style.zoom='110%';")
                time.sleep(random.uniform(1, 3))  # Give time for adjustments

                total_height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1920, total_height)

                screenshot_path = f'{temp_dir}/screenshot_{i}.png'
                driver.save_screenshot(screenshot_path)
                image = Image.open(screenshot_path)

                pdf_buffer = io.BytesIO()
                image.convert('RGB').save(pdf_buffer, format='PDF')
                pdf_buffer.seek(0)  # Move to the beginning of the buffer
                pdf_buffers.append((pdf_buffer, f'{mpns[i]}.pdf'))

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

                    for pdf_buffer, filename in pdf_buffers:
                        st.download_button(
                            label=f"Download {filename}",
                            data=pdf_buffer,
                            file_name=filename,
                            mime='application/pdf'
                        )
            else:
                st.warning("No valid URLs found in the Excel file.")
    else:
        st.error("Excel file must contain 'URL' and 'MPN' columns.")
