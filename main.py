import re
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from time import sleep

IGNORE_EXCEPTIONS =(NoSuchElementException, StaleElementReferenceException)

RECIPIENT_MAIL = 'panepojdtesihrat@gmail.com'
EMAIL_SUBJECT = 'Test Email Subject'
EMAIL_BODY = 'Test Email Body'
PASSWORD = os.getenv('PASSWORD_ENV_VAR')


class Button:
    def __init__(self, driver, xpath):
        self.driver = driver
        self.button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath)))

    def find_and_click_button(self):
        try:
            self.button.click()
        except:
            self.driver.execute_script("arguments[0].click();", self.button)


class Email:
    def __init__(self, sender, subject, time):
        self.sender = sender
        self.subject = subject
        self.time = time

    def __repr__(self):
        return f"sender: {self.sender}, subject: {self.subject}, time: {self.time}"


def login(driver):
    try:

        # Open Gmail login page
        driver.get('https://mail.google.com')

        # Wait for the email input field to be present
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        )
        email_input.send_keys('panepojdtesihrat@gmail.com')
        email_input.send_keys(Keys.ENTER)

        # Wait for the password input field to be present

        x = EC.presence_of_element_located((By.NAME, "Passwd"))
        password_input = WebDriverWait(driver, 10).until(
            x)

        password_input.send_keys(PASSWORD)
        password_input.send_keys(Keys.ENTER)

        # Wait for the Gmail inbox page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Compose')]"))
        )
        print("Step 1: Pass! Logged in successfully!")

    except Exception as e:
        print("Step 1: Fail! Log in failed!")
        driver.quit()


def compose_and_send_email(driver):

    try:
        # Click on the Compose button
        compose_button = Button(driver, "//div[@role='button' and text()='Compose']")
        compose_button.find_and_click_button()

        # Wait for the recipient input field to be present
        to_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@aria-label='To recipients']"))
        )
        sleep(1)
        to_input.send_keys(RECIPIENT_MAIL)

        # Enter the subject
        subject_input = driver.find_element(By.NAME, "subjectbox")
        subject_input.send_keys(EMAIL_SUBJECT)

        # Enter the email body
        body_input = driver.find_element(By.XPATH, "//div[@aria-label='Message Body']")
        body_input.send_keys(EMAIL_BODY)
        print("Step 2: Pass!  Mail composed")

        # click more options
        more_options = driver.find_element(By.XPATH, "//div[@data-tooltip='More options']")
        more_options.click()

        # click label
        label_as_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Label')]")
        label_as_option.click()

        # click social
        social_label_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Social')]")
        social_label_option.click()
        print("Step 3: Pass!  Social label selected")

        # Click on the Send button
        send_button = Button(driver, "//div[@role='button' and text()='Send']")
        send_button.find_and_click_button()
        print("Step 4: Pass! Mail sent")

    except Exception as e:
        driver.quit()
        print(f"An error {e} occurred while executing Step 2, 3, 4")


def get_number_of_inbox(driver):
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
    assert new.sender is not None
    print(f"verify old: {old}")
    print(f"verify new: {new}")
    if old.sender != new.sender:
        raise ValueError("Mail from different sender arrived during test")


def verify_new_mail_came(driver, old_count, old_email):
    timeout = 30  # seconds
    interval = 1  # seconds

    for _ in range(timeout):
        new_count = get_number_of_inbox(driver)
        print(f"new inbox: {new_count}")
        if new_count > old_count:
            new_email = Email(*get_newest_inbox(driver))
            verify_two_emails(old_email, new_email)
            return
        sleep(interval)
    else:
        raise ValueError(f"No mail did not arrive within specified timeout")


def get_inboxes(driver):
    emails = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Cp div table.F.cf.zt tbody tr"))
    )
    return emails


def get_newest_inbox(driver):
    emails = driver.find_elements(By.CSS_SELECTOR, "div.Cp div table.F.cf.zt tbody tr")
    if emails:
        sender_object = emails[0].find_element(By.CSS_SELECTOR, "span.zF")
        sender = sender_object.get_attribute("name")
        subject = emails[0].find_element(By.CSS_SELECTOR, "span.bog").text
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
    old_inbox_count = get_number_of_inbox(firefox)
    if old_inbox_count == 0:
        old_email = Email(None, None, None)
    else:
        old_email = Email(*get_newest_inbox(firefox))

    # step 2, 3, 4 - compose email, label social, send email
    compose_and_send_email(firefox)

    # step 5 verify new mail has come
    verify_new_mail_came(firefox, old_inbox_count, old_email)

    # step 6 mark first email as starred
    emails = get_inboxes(firefox)

    try:
        first_email = emails[0]
        star_icon = first_email.find_element(By.CSS_SELECTOR, "span.aXw.T-KT[aria-label='Not starred']")
        star_icon.click()
        print("Step 6: Pass! First email marked as starred.")

    except Exception as e:
        print(f"Step 6: Fail! An error occurred while starring the email: {e}")

    # step 7 open received email
    try:
        first_email = emails[0]

        # Locate the subject within the first email row
        subject_element = first_email.find_element(By.CSS_SELECTOR, "span.bqe")

        # Ensure the subject element is visible
        if subject_element.is_displayed():
            # Scroll the subject element into view and click on it
            actions = ActionChains(firefox)
            actions.move_to_element(subject_element).perform()
            subject_element.click()
        else:
            # Use JavaScript to click the element if it is not directly clickable
            firefox.execute_script("arguments[0].click();", subject_element)
        print("Step 7: Pass! First email opened.")
    except Exception as e:
        print(f"Step 7: Fail! An error occurred while opening the email: {e}")

    # step 8 check if the mail is in social
    # click more options
    more_options_button = WebDriverWait(firefox, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[id=":ao"]'))
    )
    more_options_button.click()

    # click label
    label_as_element = WebDriverWait(firefox, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.J-N.J-Ph'))
    )
    label_as_element.click()

    social_element = WebDriverWait(firefox, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.J-LC[title="Social"]'))
    )

    aria_checked = social_element.get_attribute("aria-checked")
    if aria_checked == "true":
        print("Step 8 Pass! Social label verified")
    else:
        print(f"Step 8 Fail! Social label value {aria_checked}")

    # step 9 verify subject and body of received email
    email_list = WebDriverWait(firefox, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.Cp div table.F.cf.zt tbody')))
    subject_element = email_list.find_element(By.XPATH, '//h2[contains(@class, "hP")]')

    email_body_element = WebDriverWait(firefox, 10).until(
        EC.presence_of_element_located((By.XPATH, '//div[@id=":43"]//div[@dir="ltr"]'))
    )

    email_body_element = WebDriverWait(firefox, 10).until(
        EC.presence_of_element_located((By.XPATH, '//div[@id=":43"]//div[@dir="ltr"]'))
    )

    if email_body_element.text == EMAIL_BODY:
        print("Step 9  1/2 Pass! Email body verified")
    else:
        print(f"Step 9 1/2 Fail! Email body value {email_body_element.text}")

    if subject_element.text == EMAIL_SUBJECT:
        print("Step 9  2/2 Pass! Email subject verified")
    else:
        print(f"Step 9 2/2 Fail! Email subject value {subject_element.text}")

    if subject_element.text == EMAIL_SUBJECT:
        print("Step 9  1/2 Pass! Email subject verified")
    else:
        print(f"Step 9 1/2 Fail! Email subject value {subject_element.text}")

    # quit
    quit_browser(firefox)


if __name__ == "__main__":
    main()