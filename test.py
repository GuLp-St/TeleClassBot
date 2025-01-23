import configparser
import time
import os
import re
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from lab_auto import check_for_time_range,config

def test():

    chrome_options = Options()
    # chrome_options.add_argument("--headless")

    # Initialize the WebDriver outside the loop
    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(
        ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)

    driver.get("https://qr.unimas.my/attendance/activity/index.html#!/activity/90826?c=profile")

    # Locate username/email field
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(config['credentials']['username'])

    # Locate password field
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(config['credentials']['password'])

    # Sign in button
    sign_in_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body > div.cont > div > div > form > button")))
    sign_in_button.click()

    driver.get("https://qr.unimas.my/attendance/activity/index.html#!/activity/91023?c=profile")

    # wait = WebDriverWait(driver, 10)
    # alert = wait.until(EC.alert_is_present())

    # alert_text = alert.text
    # print(f"Alert text: {alert_text}")

    # alert.accept()

    
    #https://qr.unimas.my/attendance/activity/index.html#!/activity/90823?c=profile

    print("checking")
    print(check_for_time_range(driver))
    

test()