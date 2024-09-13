import streamlit as st
import time
import os
import pandas as pd
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from PIL import Image
import tempfile

# Configure Streamlit
st.set_page_config(page_title="Excel URL to PDF Converter", layout="wide")

# Function to convert URLs to PDFs
def convert_urls_to_pdfs(urls, mpns, save_path):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")  # Headless mode for server
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument("--window-size=1920x1080")  # Set window size
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    # Create a temporary directory to store screenshots and PDFs
    pdf_paths = []
    with tempfile.TemporaryDirectory() as temp_dir:
        service = Service(executable_path='chromedriver')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options)
        
        for i, url in enumerate(urls):
            try:
                driver.get(url)
                driver.maximize_window()
                time.sleep(15)  # Wait for the page to load
                screenshot_path = os.path.join(temp_dir, f'screenshot_{i}.png')
                pdf_path = os.path.join(save_path, f'{mpns[i].replace("/", "_").replace("\\", "_")}.pdf')

                driver.save_screenshot(screenshot_path)
                image = Image.open(screenshot_path)
                image.convert('RGB').save(pdf_path)
                
                # Store the path of the generated PDF
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
                # Set the relative path for saving PDFs
                save_path = "output_pdfs"  # Ensure this directory is created
                os.makedirs(save_path, exist_ok=True)  # Create directory if it doesn't exist
                
                with st.spinner("Converting..."):
                    pdf_paths = convert_urls_to_pdfs(urls, mpns, save_path)
                    st.success("Conversion completed!")

                    # Allow users to download the PDFs
                    for pdf_path in pdf_paths:
                        pdf_filename = os.path.basename(pdf_path)
                        with open(pdf_path, 'rb') as pdf_file:
                            st.download_button(
                                label=f"Download {pdf_filename}",
                                data=pdf_file,
                                file_name=pdf_filename,
                                mime='application/pdf'
                            )
            else:
                st.warning("No valid URLs found in the Excel file.")
    else:
        st.error("Excel file must contain 'URL' and 'MPN' columns.")
