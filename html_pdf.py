import streamlit as st
import pandas as pd
import os
import time
import random
import tempfile
from webdriver_manager.core.os_manager import ChromeType
import zipfile
from PIL import Image
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from langdetect import detect, DetectorFactory
from bs4 import BeautifulSoup

# Ensure consistent language detection
DetectorFactory.seed = 0

# Function to close cookie consent pop-ups
def close_cookie_consent(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'akzeptieren')]"))).click()
        
    except:
        pass
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]"))).click()
        
    except:
        pass
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent')]"))).click()
        
    except:
        pass
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]"))).click()
        
    except:
        pass

def detect_language_from_url(url):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
    
    try:
        with webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options) as driver:
            driver.get(url)
            time.sleep(2)  # Wait for the page to load
            html = driver.page_source
            text = BeautifulSoup(html, 'html.parser').get_text(separator=' ', strip=True)

            if len(text) < 20:
                return "Not enough text to detect language."
            detected_lang = detect(text)
            return detected_lang
    except Exception as e:
        return f"Error: {e}"

def delete_price_elements(driver):
    currency_symbols = ["$", "€", "£", "EUR", "USD", "¥", "JPY", "₽"]
    for symbol in currency_symbols:
        try:
            elements_to_delete = driver.find_elements(By.XPATH, f"//*[contains(text(), '{symbol}')]")
            for element in elements_to_delete:
                driver.execute_script("arguments[0].remove();", element)
        except Exception as e:
            continue

def convert_urls_to_pdfs(urls, mpns, additional_text, output_dir):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--disable-gpu')
    options.add_argument('--ignore-certificate-errors')

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument('--lang=en')
        
    pdf_paths = []
    output_data = []

    driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options) 
    for i, url in enumerate(urls):
        try:
            detected_lang = detect_language_from_url(url)
            if detected_lang != 'en':
                url = f"https://translate.google.com/translate?hl=en&sl={detected_lang}&u={url}"
            driver.get(url)
            time.sleep(random.uniform(1, 3))
            close_cookie_consent(driver)

            if additional_text:
                try:
                    print("there is additional_text ")
                    keywords = [keyword.strip() for keyword in additional_text.split(',')]
                    for keyword in keywords:
                        expanded_elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]")
                        for element in expanded_elements:
                            try:
                                element.click()
                                print("clicked additional_text")
                            except Exception:
                                print("Not clicked additional_text")
                                continue
                except Exception as e:
                    continue
            time.sleep(random.uniform(1, 3))
            delete_price_elements(driver)

            driver.execute_script("document.body.style.zoom='110%';")
            time.sleep(random.uniform(1, 3))

            total_height = driver.execute_script("return document.body.scrollHeight")
            driver.set_window_size(1920, total_height)

            screenshot_path = f'{output_dir}/screenshot_{i}.png'
            driver.save_screenshot(screenshot_path)
            image = Image.open(screenshot_path)

            pdf_path = os.path.join(output_dir, f'{mpns[i]}.pdf')
            image.convert('RGB').save(pdf_path, format='PDF')
            pdf_paths.append(pdf_path)

            output_data.append({
                "MPN": mpns[i],
                "HTML": url,
                "PDF Path": pdf_path
            })

        except Exception as e:
            st.error(f"Error processing {url}: {e}")
            continue

    driver.quit()
    
    output_df = pd.DataFrame(output_data)
    output_excel_path = os.path.join(output_dir, "output.xlsx")
    output_df.to_excel(output_excel_path, index=False)  # Save output to Excel in specified folder
    return pdf_paths, output_excel_path

def create_zip_file(pdf_paths, output_dir):
    zip_filename = os.path.join(output_dir, 'pdfs.zip')
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for pdf in pdf_paths:
            zipf.write(pdf, os.path.basename(pdf))
    return zip_filename

# Streamlit UI
st.title("HTML to PDF Converter")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if 'URL' in df.columns and 'MPN' in df.columns:
        urls = df['URL'].dropna().tolist()
        mpns = df['MPN'].dropna().tolist()

        additional_text = st.text_input("Enter additional text to expand elements (leave blank for none):")
        output_dir = st.text_input("Enter output directory (leave blank for default temp directory):", value=os.getcwd())

        if st.button("Convert"):
            if urls:
                if not os.path.exists(output_dir):
                    st.error("The specified output directory does not exist.")
                else:
                    pdf_paths, output_excel_path = convert_urls_to_pdfs(urls, mpns, additional_text, output_dir)
                    
                    # Create a zip file for all PDFs
                    zip_file_path = create_zip_file(pdf_paths, output_dir)

                    st.success("Conversion completed! Download your files below:")
                    st.download_button(label="Download All PDFs as Zip", data=open(zip_file_path, "rb"), file_name="pdfs.zip", mime='application/zip')

                    with open(output_excel_path, "rb") as f:
                        st.download_button(label="Download Output Excel", data=f, file_name="output.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                st.warning("No valid URLs found.")
    else:
        st.error("'URL' and 'MPN' columns must be present in the Excel file.")
