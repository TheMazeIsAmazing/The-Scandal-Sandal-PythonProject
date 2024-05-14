import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import sqlite3
import os
import json

# Load the .env file
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')

# Initialize the OpenAI client with the API key from the environment variable
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Making a GET request
r = requests.get('https://evrepairmag.com/shock-rates-60000-repair-bill-leads-to-scrapping-of-2022-model-year-ev/#:~:text=Vancouver%2C%20British%20Columbia%20%E2%80%94%20Kyle%20Hsu,his%20nearly%20brand%2Dnew%20vehicle.')
# r = requests.get('https://www.carthrottle.com/news/former-employee-claims-tesla-knowingly-sold-defective-cars')

# Parsing the HTML
soup = BeautifulSoup(r.content, 'html.parser')

# Find the specific div containing the article content
# content_div = soup.find('article')
content_div = soup.find('div', class_='elementor-widget-theme-post-content')

# print(soup)
print(content_div)

# Find all paragraphs within the content div
paragraphs = content_div.find_all('p')
paragraphString = ''

# Extract and print the text from paragraphs
for paragraph in paragraphs:
    print(paragraph.get_text())
    paragraphString += paragraph.get_text()

completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
          "role": "system",
          "content": "You will get a text, please grade it on a few criteria. 1: Customer Service and Care, 2: (Software) Reliability and 3: Responsibility. Grade them on a scale from 0 to 2. If you're unable to grade it, please state 'undefined' at the specific criteria. Also explain why you chose this score. Return JSON: {\"headline\", \"scoring\": {\"customer_service\": {\"grade\", \"explanation\"}, \"reliability\": {\"grade\", \"explanation\"}, \"responsibility\": {\"grade\", \"explanation\"}}}"
        },
        {
          "role": "user",
          "content": paragraphString
        }
    ]
)

cleanedArticle = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
          "role": "system",
          "content": "Return the article text within one string without linebreaks, with the things like: 'read more after the picture' and 'sign up now' removed."
        },
        {
          "role": "user",
          "content": paragraphString
        }
    ]
)



json_object = json.loads(completion.choices[0].message.content)
print(json_object)

headline = json_object['headline']
content = cleanedArticle.choices[0].message.content
score_openai_customer_service = json_object['scoring']['customer_service']['grade']
ex_score_openai_customer_service = json_object['scoring']['customer_service']['explanation']
score_openai_reliability = json_object['scoring']['reliability']['grade']
ex_score_openai_reliability = json_object['scoring']['reliability']['explanation']
score_openai_responsibility = json_object['scoring']['responsibility']['grade']
ex_score_openai_responsibility = json_object['scoring']['responsibility']['explanation']

conn = get_db_connection()
conn.execute('INSERT INTO articles (headline, content, score_openai_customer_service, ex_score_openai_customer_service, score_openai_reliability, ex_score_openai_reliability, score_openai_responsibility, ex_score_openai_responsibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
             (headline, content, score_openai_customer_service, ex_score_openai_customer_service, score_openai_reliability, ex_score_openai_reliability, score_openai_responsibility, ex_score_openai_responsibility))
conn.commit()
conn.close()
