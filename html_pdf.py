import streamlit as st
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from PIL import Image
import tempfile

# Configure Streamlit
st.set_page_config(page_title="HTML to PDF Converter", layout="wide")

# Function to convert URLs to PDFs
def convert_urls_to_pdfs(urls):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Create a temporary directory to store screenshots and PDFs
    with tempfile.TemporaryDirectory() as temp_dir:
        service = Service(executable_path='chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        
        for i, url in enumerate(urls):
            try:
                driver.get(url)
                driver.maximize_window()
                time.sleep(15)  # Wait for the page to load
                screenshot_path = os.path.join(temp_dir, f'screenshot_{i}.png')
                pdf_path = os.path.join(temp_dir, f'document_{i}.pdf')

                driver.save_screenshot(screenshot_path)
                image = Image.open(screenshot_path)
                image.convert('RGB').save(pdf_path)

            except Exception as e:
                st.error(f"Error processing {url}: {e}")
                continue

        driver.quit()
        return temp_dir

# Streamlit interface
st.title("HTML to PDF Converter")
st.write("Convert HTML pages to PDF files by entering URLs below.")

# Input for URLs
urls_input = st.text_area("Enter URLs (one per line):", height=200)
urls = [url.strip() for url in urls_input.splitlines() if url]

if st.button("Convert"):
    if urls:
        with st.spinner("Converting..."):
            temp_dir = convert_urls_to_pdfs(urls)
            st.success("Conversion completed!")

            # Allow users to download PDFs
            for i in range(len(urls)):
                pdf_path = os.path.join(temp_dir, f'document_{i}.pdf')
                with open(pdf_path, 'rb') as pdf_file:
                    st.download_button(
                        label=f"Download PDF for {urls[i]}",
                        data=pdf_file,
                        file_name=f'document_{i}.pdf',
                        mime='application/pdf'
                    )
    else:
        st.warning("Please enter at least one URL.")