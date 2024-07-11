import re
import os
import argparse
import logging
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
from time import sleep
from functools import wraps

parser = argparse.ArgumentParser(description='Process email address.')
parser.add_argument('--email', required=True, help='Email address for processing')
arguments = parser.parse_args()

IGNORE_EXCEPTIONS = (NoSuchElementException, StaleElementReferenceException)
EMAIL = arguments.email
EMAIL_SUBJECT = 'Test Email Subject'
EMAIL_BODY = 'Test Email Body'
PASSWORD = os.getenv('PASSWORD_ENV_VAR')

# Set logging level
logging.basicConfig(level=logging.INFO)


# Decorator to retry interaction with driver before calling the function
def retry(func):
    @wraps(func)
    def wrapper(driver, *args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Call the function with the driver instance
                return func(driver, *args, **kwargs)
            except IGNORE_EXCEPTIONS as e:
                if attempt < max_retries - 1:
                    logging.info(f"Retrying with {e} while calling {func.__name__}...")
                    continue  # Retry the function
                else:
                    sleep(0.5)
                    logging.error(f"Max retries ({max_retries}) exceeded. Giving up.")
                    raise  # Re-raise the exception after max retries

    return wrapper


class Button:
    def __init__(self, driver, xpath):
        self.driver = driver
        self.button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )

    def find_and_click_button(self):
        try:
            self.button.click()
        except IGNORE_EXCEPTIONS:
            self.driver.execute_script("arguments[0].click();", self.button)


class Email:
    def __init__(self, sender, subject, time):
        self.sender = sender
        self.subject = subject
        self.time = time

    def __repr__(self):
        return f"sender: {self.sender}, subject: {self.subject}, time: {self.time}"


def retry_send_keys(driver, element, keys):
    try:
        # Attempt to send keys to the element
        element.send_keys(keys)
    except ElementNotInteractableException as e:
        # Log a warning with the exception details
        logging.warning(f"Encountered: {e}. Attempting to click the element using"
                        f"JavaScript before sending keys.")
        # Click the element using JavaScript to make it interactable
        driver.execute_script("arguments[0].click();", element)
        # Retry sending keys to the element
        element.send_keys(keys)


def login(driver):
    try:
        # Open Gmail login page
        driver.get('https://mail.google.com')

        # Wait for the email input field to be present
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        )

        retry_send_keys(driver, email_input, EMAIL)
        email_input.send_keys(Keys.ENTER)

        # Wait for the password input field to be present
        password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "Passwd"))
                                                         )
        retry_send_keys(driver, password_input, PASSWORD)
        password_input.send_keys(Keys.ENTER)

        # Wait for the Gmail inbox page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Compose')]"))
        )
        logging.info("Step 1: Pass! Logged in successfully!")

    except IGNORE_EXCEPTIONS:
        logging.info(f"Step 1: Fail! Log in failed, quitting program.")
        driver.quit()


@retry
def compose_email(driver):
    # Click on the Compose button
    compose_button = Button(driver, "//div[@role='button' and text()='Compose']")
    compose_button.find_and_click_button()

    # Wait for the recipient input field to be present
    to_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@aria-label='To recipients']")))

    try:
        to_input.send_keys(EMAIL)
    except ElementNotInteractableException:
        # Find the 'To recipients' element using XPath with class identification
        element = driver.find_element(By.XPATH, "//div[contains(@class, 'fX') and contains(@class, 'aiL')]")

        # Directly modify the style attribute of the 'element' object using JavaScript
        driver.execute_script("arguments[0].style = '';", element)

        # Send the EMAIL to the 'To recipients' input field
        to_input.send_keys(EMAIL)

    # Enter the subject
    subject_input = driver.find_element(By.NAME, "subjectbox")
    subject_input.send_keys(EMAIL_SUBJECT)

    # Enter the email body
    body_input = driver.find_element(By.XPATH, "//div[@aria-label='Message Body']")
    body_input.send_keys(EMAIL_BODY)
    logging.info("Step 2: Pass!  Mail composed")


@retry
def mark_email_as_label(driver):
    # click more options
    more_options = driver.find_element(By.XPATH, "//div[@data-tooltip='More options']")
    more_options.click()

    # click label
    label_as_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Label')]")
    label_as_option.click()

    # click social
    social_label_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Social')]")
    social_label_option.click()
    logging.info("Step 3: Pass!  Social label selected")


@retry
def send_email(driver):
    # Click on the Send button
    send_button = Button(driver, "//div[@role='button' and text()='Send']")
    send_button.find_and_click_button()
    logging.info("Step 4: Pass! Mail sent")


@retry
def get_number_of_unread_inbox(driver):
    inbox = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[@data-tooltip='Inbox']"))
    )
    children = inbox.find_element(By.XPATH, ".//div")

    inbox = re.findall(r'\d+', children.text)
    if inbox:
        return int(inbox[0])
    else:
        return 0


def verify_two_emails(old, new):
    if old.sender is None:
        return
    assert new.sender is not None
    logging.info(f"verify old: {old}")
    logging.info(f"verify new: {new}")
    if old.sender != new.sender:
        raise ValueError("Mail from different sender arrived during test")


@retry
def verify_new_mail_came(driver, old_count, old_email):
    timeout = 30  # seconds
    interval = 1  # seconds

    for _ in range(timeout):
        new_count = get_number_of_unread_inbox(driver)
        logging.info(f"new inbox: {new_count}")
        if new_count > old_count:
            new_email = Email(*get_newest_inbox(driver))
            verify_two_emails(old_email, new_email)
            return
        sleep(interval)
    else:
        raise ValueError(f"No mail did not arrive within specified timeout")


def get_inboxes(driver):
    emails = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Cp div table.F.cf.zt tbody tr"))
    )
    return emails


@retry
def mark_first_email_as_starred(driver):
    emails = get_inboxes(driver)
    first_email = emails[0]
    star_icon = first_email.find_element(By.CSS_SELECTOR, "span.aXw.T-KT[aria-label='Not starred']")
    star_icon.click()
    logging.info("Step 6: Pass! First email marked as starred.")


@retry
def open_received_email(driver):
    emails = get_inboxes(driver)
    first_email = emails[0]

    # Locate the subject within the first email row
    subject_element = first_email.find_element(By.CSS_SELECTOR, "span.bqe")

    # Ensure the subject element is visible
    if subject_element.is_displayed():
        # Scroll the subject element into view and click on it
        actions = ActionChains(driver)
        actions.move_to_element(subject_element).perform()
        subject_element.click()
    else:
        # Use JavaScript to click the element if it is not directly clickable
        driver.execute_script("arguments[0].click();", subject_element)
    logging.info("Step 7: Pass! First email opened.")


@retry
def check_if_mail_is_social(driver):
    # click more options
    parent_div = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//div[@class="iH bzn"]'))
    )

    # Now find the "more options" button within the parent div
    more_options_button = parent_div.find_element(By.XPATH, './/div[@aria-label="More email options"]')

    more_options_button.click()

    # click label
    label_as_element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.J-N.J-Ph'))
    )
    label_as_element.click()

    social_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.J-LC[title="Social"]'))
    )

    aria_checked = social_element.get_attribute("aria-checked")
    if aria_checked == "true":
        logging.info("Step 8 Pass! Social label verified")
    else:
        logging.info(f"Step 8 Fail! Social label value {aria_checked}")


@retry
def verify_subject_and_body(driver):
    email_body_parent = driver.find_element(By.XPATH, "//*[contains(@class, 'a3s') and contains(@class, 'aiL')]")
    email_body_text = email_body_parent.find_element(By.XPATH, ".//div[@dir='ltr']").text

    if email_body_text == EMAIL_BODY:
        logging.info("Step 9  1/2 Pass! Email body verified")
    else:
        logging.info(f"Step 9 1/2 Fail! Email body value {email_body_text}")

    email_list = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.Cp div table.F.cf.zt tbody'))
    )
    subject_text = email_list.find_element(By.XPATH, '//h2[contains(@class, "hP")]').text

    if subject_text == EMAIL_SUBJECT:
        logging.info("Step 9  2/2 Pass! Email subject verified")
    else:
        logging.info(f"Step 9 2/2 Fail! Email subject value {subject_text}")


@retry
def get_newest_inbox(driver):
    emails = driver.find_elements(By.CSS_SELECTOR, "div.Cp div table.F.cf.zt tbody tr")

    if emails:
        sender = emails[0].find_element(By.XPATH, ".//td[4]").text
        subject = emails[0].find_element(By.XPATH, ".//td[5]/div/div/div").text
        time = emails[0].find_element(By.CSS_SELECTOR, "td.xW.xY span").get_attribute('title')
        return sender, subject, time
    else:
        return None, None, None


def quit_browser(driver):
    driver.quit()


def main():
    # Set up the Firefox driver
    firefox = webdriver.Firefox()

    # step 1 -login
    login(firefox)

    # get number of inbox and newest email
    old_inbox_count = get_number_of_unread_inbox(firefox)
    if old_inbox_count == 0:
        old_email = Email(None, None, None)
    else:
        old_email = Email(*get_newest_inbox(firefox))

    # step 2 compose email
    compose_email(firefox)

    # step 3 mark email as social
    mark_email_as_label(firefox)

    # step 4 send email
    send_email(firefox)

    # step 5 verify new mail has come
    verify_new_mail_came(firefox, old_inbox_count, old_email)

    # step 6 mark first email as starred
    mark_first_email_as_starred(firefox)

    # step 7 open received email
    open_received_email(firefox)

    # step 8 check if the mail is in social
    check_if_mail_is_social(firefox)

    # step 9 verify subject and body of received email
    verify_subject_and_body(firefox)

    # quit
    quit_browser(firefox)


if __name__ == "__main__":
    main()
