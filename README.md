# Email Automation with Selenium

This script automates various tasks in Gmail using Selenium WebDriver. The script performs the following actions:

1. Logs into Gmail with provided credentials.
2. Composes an email with specified subject and body.
3. Labels the email as "Social".
4. Sends the email.
5. Verifies that a new email has arrived.
6. Marks the first email in the inbox as starred.
7. Opens the received email.
8. Verifies that the email is labeled as "Social".
9. Verifies the subject and body of the received email.

### **Prerequisites**

- Python 3.x
- Selenium WebDriver
- Firefox Browser
- Environment variable `PASSWORD_ENV_VAR` set to your Gmail password

- ### **Usage**

Run the script with the following command:

```sh
python email_automation.py --email your_email@gmail.com
