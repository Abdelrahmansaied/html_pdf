import streamlit as st
import time
import random
import pandas as pd
import undetected_chromedriver as uc  # Use undetected-chromedriver
from selenium.webdriver.common.by import By
from PIL import Image
import tempfile
import io
from googletrans import Translator
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

contentjs = """
// content.js
// Your content.js code remains unchanged
"""

# Configure Streamlit
st.set_page_config(page_title="HTML to PDF Converter", layout="wide")

# Function to close cookie consent pop-ups
def close_cookie_consent(driver):
    keywords = ["I agree", "OK", "I consent", "Cookies", "Alle"]
    elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//*")))
    for element in elements:
        if any(keyword.lower() in element.text.lower() for keyword in keywords):
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
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-xss-auditor")
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")

    pdf_buffers = []
    with tempfile.TemporaryDirectory() as temp_dir:
        driver = uc.Chrome(options=options)

        for i, url in enumerate(urls):
            try:
                driver.get(url)
                driver.execute_script(contentjs)
                time.sleep(random.uniform(1, 3))  # Wait for the page to load
                close_cookie_consent(driver)
                time.sleep(random.uniform(1, 3))  # Wait for a while after consent closure

                driver.execute_script("document.body.style.zoom='100%';")
                time.sleep(random.uniform(1, 3))  # Give time for adjustments

                total_height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1920, total_height)

                screenshot_path = f'{temp_dir}/screenshot_{i}.png'
                driver.save_screenshot(screenshot_path)
                image = Image.open(screenshot_path)

                pdf_buffer = io.BytesIO()
                image.convert('RGB').save(pdf_buffer, format='PDF')
                pdf_buffer.seek(0)  # Move to the beginning of the buffer
                pdf_buffers.append((pdf_buffer, f'{mpns[i].replace("/", "_").replace("\"", "_")}.pdf'))

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
