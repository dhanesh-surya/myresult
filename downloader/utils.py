from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import os

STOP_FLAG_FILE = "stop_processing.flag"


def download_result(
    user_id,
    password,
    download_dir,
    url,
    username_field="userid",
    password_field="pass",
    download_button_id="download",
):
    if os.path.exists(STOP_FLAG_FILE):
        print(f"Processing stopped by user for {user_id}")
        return None

    os.makedirs(download_dir, exist_ok=True)
    download_dir = os.path.abspath(download_dir)

    print(f"Download directory: {download_dir}")
    print(f"Target URL: {url}")

    options = Options()

    prefs = {
        "download.default_directory": download_dir.replace("/", "\\"),
        "download.prompt_for_download": False,
    }

    options.add_experimental_option("prefs", prefs)
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        print(f"Opening website for {user_id}...")
        driver.get(url)
        time.sleep(3)

        # Find and fill username using dynamic field name
        print(f"Filling username ({username_field}): {user_id}")
        userid_field = driver.find_element(By.NAME, username_field)
        userid_field.clear()
        userid_field.send_keys(user_id)

        # Find and fill password using dynamic field name
        print(f"Filling password ({password_field})...")
        pass_field = driver.find_element(By.NAME, password_field)
        pass_field.clear()
        pass_field.send_keys(password + Keys.RETURN)

        time.sleep(4)

        # Check page content for result
        print(f"Page title after submit: {driver.title}")

        # Save page content to PDF file
        pdf_filename = f"{user_id}_result.pdf"
        pdf_path = os.path.join(download_dir, pdf_filename)

        # Use print to PDF
        print(f"Saving as PDF: {pdf_path}")

        # Hide only obvious ads
        time.sleep(1)
        driver.execute_script("""
            document.querySelectorAll('iframe, ins.adsbygoogle')
                .forEach(el => el.style.display = 'none');
        """)

        # Get the page and save as PDF using Chrome's print API
        result = driver.execute_cdp_cmd(
            "Page.printToPDF",
            {
                "printBackground": True,
                "paperWidth": 8.5,
                "paperHeight": 11,
                "marginTop": 0.5,
                "marginBottom": 0.5,
            },
        )

        # Write PDF content to file
        import base64

        pdf_data = base64.b64decode(result["data"])
        with open(pdf_path, "wb") as f:
            f.write(pdf_data)

        print(f"PDF saved: {pdf_path}")
        driver.quit()
        return pdf_path

    except Exception as e:
        print(f"Error processing {user_id}: {e}")
        import traceback

        traceback.print_exc()

    finally:
        try:
            driver.quit()
        except:
            pass

    return None
