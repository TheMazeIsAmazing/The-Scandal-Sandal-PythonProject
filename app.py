import sqlite3
from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
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


def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM articles WHERE id = ?',
                        (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'


@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM articles').fetchall()
    conn.close()
    return render_template('index.html', posts=posts)


@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    return render_template('post.html', post=post)



@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        # Get form data
        url = request.form.get('url')
        selector_type = request.form.get('selector_type')
        selector = request.form.get('selector')
        paragraphs = request.form.get("paragraphs") is not None

        # Check if all required fields are provided
        if not url or not selector_type or not selector:
            flash('All fields (URL, Selector Type, and Selector) are required!')
            return render_template('create.html')

        # Fetch the URL content
        response = requests.get(url)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Select the content based on selector type
        if selector_type == 'id':
            content_div = soup.find('div', id=selector)
        elif selector_type == 'html':
            content_div = soup.select_one(selector)
        else:
            content_div = soup.find('div', class_=selector)

        # Check if content was found
        if not content_div:
            flash('No content found with the given selector!')
            return render_template('create.html')

        # Extract the text from the content div
        if paragraphs:
            # Extract text from all paragraphs if paragraphs option is selected
            article_text = ' '.join(p.get_text() for p in content_div.find_all('p'))
        else:
            article_text = content_div.get_text()

        # Call OpenAI API to grade the article
        grading_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You will get a text, please grade it on a few criteria. "
                        "1: Customer Service and Care, 2: (Software) Reliability and 3: Responsibility. "
                        "Grade them on a scale from 0 to 2. If you're unable to grade it, please state 'undefined' at the specific criteria. "
                        "Under Headline get the article's headline from the h1, or header. "
                        "Also explain why you chose this score. Return JSON: {\"car_brand\", \"headline\", \"scoring\": {\"customer_service\": {\"grade\", \"explanation\"}, \"reliability\": {\"grade\", \"explanation\"}, \"responsibility\": {\"grade\", \"explanation\"}}}"
                    )
                },
                {"role": "user", "content": article_text}
            ]
        )

        # Call OpenAI API to clean the article text
        cleaned_article_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return the article text within one string without linebreaks, with things like: "
                        "'read more after the picture' and 'sign up now' removed."
                    )
                },
                {"role": "user", "content": article_text}
            ]
        )

        # Parse the responses from OpenAI
        grading_result = json.loads(grading_response.choices[0].message.content)
        cleaned_article = cleaned_article_response.choices[0].message.content

        # Prepare the data for the database
        article_data = {
            'company': grading_result['car_brand'],
            'headline': grading_result['headline'],
            'content': cleaned_article,
            'score_openai_customer_service': grading_result['scoring']['customer_service']['grade'],
            'ex_score_openai_customer_service': grading_result['scoring']['customer_service']['explanation'],
            'score_openai_reliability': grading_result['scoring']['reliability']['grade'],
            'ex_score_openai_reliability': grading_result['scoring']['reliability']['explanation'],
            'score_openai_responsibility': grading_result['scoring']['responsibility']['grade'],
            'ex_score_openai_responsibility': grading_result['scoring']['responsibility']['explanation']
        }

        # Insert the data into the database
        with get_db_connection() as conn:
            conn.execute(
                '''INSERT INTO articles 
                (company, url, headline, content, score_openai_customer_service, ex_score_openai_customer_service, 
                score_openai_reliability, ex_score_openai_reliability, score_openai_responsibility, ex_score_openai_responsibility) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (article_data['company'], url, article_data['headline'], article_data['content'],
                 article_data['score_openai_customer_service'], article_data['ex_score_openai_customer_service'],
                 article_data['score_openai_reliability'], article_data['ex_score_openai_reliability'],
                 article_data['score_openai_responsibility'], article_data['ex_score_openai_responsibility'])
            )
            conn.commit()

        # Redirect to the index page after successful insertion
        return redirect(url_for('index'))

    # Render the create.html template for GET requests
    return render_template('create.html')


@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            conn.execute('UPDATE posts SET title = ?, content = ?'
                         ' WHERE id = ?',
                         (title, content, id))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)


@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM articles WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post['headline']))
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')
