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
from googletrans import Translator
from selenium.webdriver.common.by import By

# Configure Streamlit
st.set_page_config(page_title="Excel URL to PDF Converter", layout="wide")

# Function to close cookie consent pop-ups
def close_cookie_consent(driver):
    keywords = ["I agree", "OK", "I consent", "Cookies"]
    elements = driver.find_elements(By.XPATH, "//*")  # Get all elements

    for element in elements:
        if any(keyword.lower() in element.text.lower() for keyword in keywords):
            try:
                element.click()
                print(f"Clicked on: {element.text}")  # Debugging output
                return True  # Consent pop-up was closed
            except Exception as e:
                print(f"Error clicking element: {e}")  # Handle exceptions
                continue  # If clicking fails, continue searching
    return False  # No consent element found

# Function to translate page content
def translate_page_content(driver):
    translator = Translator()

    # Get the full HTML of the page
    original_content = driver.page_source

    # Translate the content
    translated_content = translator.translate(original_content, dest='en').text  # Change 'en' to your desired language

    # Update the page with the translated content
    driver.execute_script("document.documentElement.innerHTML = arguments[0];", translated_content)

# Function to convert URLs to PDFs
def convert_urls_to_pdfs(urls, mpns):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")  # Headless mode for server
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument("--window-size=1920x1080")  # Set window size
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    pdf_buffers = []  # To store PDF file-like objects
    with tempfile.TemporaryDirectory() as temp_dir:
        service = Service(executable_path='chromedriver')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options)

        for i, url in enumerate(urls):
            try:
                driver.get(url)
                time.sleep(3)  # Wait for the page to load

                # Close any cookie consent pop-up
                close_cookie_consent(driver)

                # Translate the page content
                translate_page_content(driver)
                time.sleep(2)  # Give time for the page to be updated with translated content

                # Capture the full height of the page
                driver.execute_script("document.body.style.zoom='100%';")  # Adjust zoom level
                time.sleep(1)  # Delay for adjustments

                # Get the dimensions of the entire page
                total_height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1920, total_height)  # Resize the window to capture the full page

                # Save a screenshot of the full page
                screenshot_path = f'{temp_dir}/screenshot_{i}.png'
                driver.save_screenshot(screenshot_path)
                image = Image.open(screenshot_path)

                # Save the image to a bytes buffer to convert to PDF
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
                    pdf_buffers = convert_urls_to_pdfs(urls, mpns)
                    st.success("Conversion completed!")

                    # Allow users to download the PDFs
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
