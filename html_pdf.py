import streamlit as st
import time
import random
from distutils.core import setup
import distutils
import pandas as pd
import undetected_chromedriver as uc  # Use undetected-chromedriver
from selenium.webdriver.common.by import By
from PIL import Image
import tempfile
import io
from googletrans import Translator
from webdriver_manager.chrome import ChromeDriverManager

contentjs = """
// content.js

// Mock navigator.languages and navigator.plugins
Object.defineProperty(navigator, 'languages', {
    get: function() {
        return ['en-US', 'en'];
    }
});

Object.defineProperty(navigator, 'plugins', {
    get: function() {
        return [1, 2, 3, 4, 5]; // Length > 0
    }
});

// Mock WebGL rendering context
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Intel Open Source Technology Center'; // UNMASKED_VENDOR_WEBGL
    }
    if (parameter === 37446) {
        return 'Mesa DRI Intel(R) Ivybridge Mobile '; // UNMASKED_RENDERER_WEBGL
    }
    return getParameter.call(this, parameter);
};

// Mock broken image dimensions
['height', 'width'].forEach(property => {
    const imageDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, property);
    Object.defineProperty(HTMLImageElement.prototype, property, {
        ...imageDescriptor,
        get: function() {
            if (this.complete && this.naturalHeight == 0) {
                return 20; // Non-zero dimension for broken images
            }
            return imageDescriptor.get.call(this);
        }
    });
});

// Mock offsetHeight for retina detection
const elementDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
Object.defineProperty(HTMLDivElement.prototype, 'offsetHeight', {
    ...elementDescriptor,
    get: function() {
        if (this.id === 'modernizr') {
            return 1; // Pass retina detection
        }
        return elementDescriptor.get.call(this);
    }
});
"""

# Configure Streamlit
st.set_page_config(page_title="HTML to PDF Converter", layout="wide")

# Function to close cookie consent pop-ups
def close_cookie_consent(driver):
    keywords = ["I agree", "OK", "I consent", "Cookies", "Alle"]

    # Wait until any elements are present and fetch them
    elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//*")))

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

# Function to convert URLs to PDFs
def convert_urls_to_pdfs(urls, mpns):
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-xss-auditor")
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-extensions")  # Disable extensions
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # Disable GPU acceleration
    options.add_argument("--window-size=1920x1080")  # Set window size

    pdf_buffers = []  # To store PDF file-like objects
    with tempfile.TemporaryDirectory() as temp_dir:
        chrome_driver_path = ChromeDriverManager().install()  # Handle ChromeDriver installation
        driver = uc.Chrome(options=options, executable_path=chrome_driver_path)

        for i, url in enumerate(urls):
            try:
                driver.get(url)
                driver.execute_script(contentjs)
                time.sleep(random.uniform(1, 3))  # Wait for the page to load

                # Close any cookie consent pop-up
                close_cookie_consent(driver)
                time.sleep(random.uniform(1, 3))  # Wait for a while after consent closure

                # Capture the full height of the page and save a screenshot
                driver.execute_script("document.body.style.zoom='100%';")
                time.sleep(random.uniform(1, 3))  # Give time for adjustments

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
st.title("HTML to PDF Converter")
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
