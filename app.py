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



@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        url = request.form['url']
        selector_type = request.form['selector_type']
        selector = request.form['selector']
        paragraphs = False

        if request.form.get("paragraphs"):
            paragraphs = True

        if not url:
            flash('URL is required!')
        if not selector_type:
            flash('Selector Type is required!')
        if not selector:
            flash('Selector is required!')
        else:
            r = requests.get(url)
            soup = BeautifulSoup(r.content, 'html.parser')

            if selector_type == 'id':
                content_div = soup.find('div', id=selector)
            elif selector_type == 'html':
                content_div = soup.find(selector)
            else:
                content_div = soup.find('div', class_=selector)

            article_paragraph_string = ''

            if paragraphs:
                # Find all paragraphs within the content div
                article_paragraphs = content_div.find_all('p')
                # Extract and concatenate the text from paragraphs
                for paragraph in article_paragraphs:
                    article_paragraph_string += paragraph.get_text()
            else:
                article_paragraph_string = content_div.get_text()

            grading = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": ("You will get a text, please grade it on a few criteria. "
                                    "1: Customer Service and Care, 2: (Software) Reliability and 3: Responsibility. "
                                    "Grade them on a scale from 0 to 2. If you're unable to grade it, please state 'undefined' at the specific criteria. "
                                    "Also explain why you chose this score. Return JSON: {\"car_brand\", \"headline\", \"scoring\": {\"customer_service\": {\"grade\", \"explanation\"}, \"reliability\": {\"grade\", \"explanation\"}, \"responsibility\": {\"grade\", \"explanation\"}}}")
                    },
                    {
                        "role": "user",
                        "content": article_paragraph_string
                    }
                ]
            )

            cleaned_article = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": ("Return the article text within one string without linebreaks, with things like: "
                                    "'read more after the picture' and 'sign up now' removed.")
                    },
                    {
                        "role": "user",
                        "content": article_paragraph_string
                    }
                ]
            )

            json_object = json.loads(grading.choices[0].message.content)
            # json_object_cleaned_stuff = json.loads(cleaned_article.choices[0].message.content)

            # return redirect(url_for('reviewchatgpt', data=json_object['scoring']['customer_service']['grade']))

            company = json_object['car_brand']
            headline = json_object['headline']
            content = cleaned_article.choices[0].message.content
            score_openai_customer_service = json_object['scoring']['customer_service']['grade']
            ex_score_openai_customer_service = json_object['scoring']['customer_service']['explanation']
            score_openai_reliability = json_object['scoring']['reliability']['grade']
            ex_score_openai_reliability = json_object['scoring']['reliability']['explanation']
            score_openai_responsibility = json_object['scoring']['responsibility']['grade']
            ex_score_openai_responsibility = json_object['scoring']['responsibility']['explanation']

            conn = get_db_connection()
            conn.execute(
                'INSERT INTO articles (company, url, headline, content, score_openai_customer_service, ex_score_openai_customer_service, score_openai_reliability, ex_score_openai_reliability, score_openai_responsibility, ex_score_openai_responsibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (company, url, headline, content, score_openai_customer_service, ex_score_openai_customer_service,
                 score_openai_reliability, ex_score_openai_reliability, score_openai_responsibility,
                 ex_score_openai_responsibility))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

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

@app.route('/<string:data>/reviewchatgpt')
def reviewchatgpt(data):
    return render_template('reviewchatgpt.html', data=data)
