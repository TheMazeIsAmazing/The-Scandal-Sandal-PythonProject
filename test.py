import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY'],
)

# Making a GET request
# r = requests.get('https://www.businessinsider.com/ford-mustang-mach-e-software-glitch-brick-electric-vehicle-2021-4?international=true&r=US&IR=T')
r = requests.get('https://www.carthrottle.com/news/former-employee-claims-tesla-knowingly-sold-defective-cars')

# Parsing the HTML
soup = BeautifulSoup(r.content, 'html.parser')

# Find the specific div containing the article content
content_div = soup.find('article')
# content_div = soup.find('div', class_='elementor-section-wrap')

print(soup)

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
          "content": "You will get a text, please grade it on a few criteria. 1: Customer Service and Care, 2: (Software) Reliability and 3: Responsibiltiy. Grade them on a scale from 0 to 2. If you're unable to grade it, please state 'unknown' at the specific criteria.)"
        },
        {
          "role": "user",
          "content": paragraphString
        }
    ]
)

print(completion.choices[0].message)
