import sqlite3
from statistics import mean
import xmltodict
from flask import Flask, render_template, request, url_for, flash, redirect, jsonify, Response
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

app = Flask(__name__,
            static_url_path='',
            static_folder='static',
            template_folder='templates')

app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = 'your secret key'

if __name__ == "__main__":
    app.run(host='0.0.0.0')

@app.route('/')
def index():
    conn = get_db_connection()
    articles = conn.execute('SELECT * FROM articles').fetchall()
    conn.close()
    return render_template('index.html', articles=articles)


@app.route('/articles/<int:article_id>')
def article(article_id):
    article = get_article(article_id)
    return render_template('article.html', article=article)


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
            article_text = ' '.join(p.get_text()
                                    for p in content_div.find_all('p'))
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
        grading_result = json.loads(
            grading_response.choices[0].message.content)
        cleaned_article = cleaned_article_response.choices[0].message.content

        # Prepare the data for the database
        article_data = {
            'company': grading_result['car_brand'].lower(),
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
    article = get_article(id)

    if request.method == 'POST':
        headline = request.form['headline']
        content = request.form['content']
        url = request.form['url']
        company = request.form['company']
        score_openai_customer_service = request.form['score_openai_customer_service']
        ex_score_openai_customer_service = request.form['ex_score_openai_customer_service']
        score_openai_reliability = request.form['score_openai_reliability']
        ex_score_openai_reliability = request.form['ex_score_openai_reliability']
        score_openai_responsibility = request.form['score_openai_responsibility']
        ex_score_openai_responsibility = request.form['ex_score_openai_responsibility']

        # company, url, headline, content, score_openai_customer_service, ex_score_openai_customer_service,
        # score_openai_reliability, ex_score_openai_reliability, score_openai_responsibility, ex_score_openai_responsibility

        if not headline:
            flash('Headline is required!')
        if not content:
            flash('Content is required!')
        if not url:
            flash('URL is required!')
        if not company:
            flash('Company is required!')
        else:
            conn = get_db_connection()
            conn.execute('UPDATE articles SET company = ?, url = ?, headline = ?, content = ?, score_openai_customer_service = ?, ex_score_openai_customer_service = ?, score_openai_reliability = ?, ex_score_openai_reliability = ?, score_openai_responsibility = ?, ex_score_openai_responsibility = ?'
                         ' WHERE id = ?',
                         (company, url, headline, content, score_openai_customer_service, ex_score_openai_customer_service, score_openai_reliability, ex_score_openai_reliability, score_openai_responsibility, ex_score_openai_responsibility, id))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('edit.html', article=article)


@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    article = get_article(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM articles WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(article['headline']))
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/developers/creator')
def iframe_creator():
    return render_template('iframe_creator.html', load_colour_picker=True, company="Score preview")


@app.route('/api')
def api():
    conn = get_db_connection()
    articles = conn.execute('SELECT * FROM articles').fetchall()
    conn.close()

    car_brand_scores = {}

    articles_list = [dict(article) for article in articles]

    for article in articles_list:
        car_brand = article.get('company')

        if car_brand not in car_brand_scores:
            car_brand_scores[car_brand] = {
                'customer_service': [int(article.get('score_openai_customer_service'))],
                'reliability': [int(article.get('score_openai_reliability'))],
                'responsibility': [int(article.get('score_openai_responsibility'))]
            }
        else:
            car_brand_scores[car_brand]['customer_service'].append(
                int(article.get('score_openai_customer_service')))
            car_brand_scores[car_brand]['reliability'].append(
                int(article.get('score_openai_reliability')))
            car_brand_scores[car_brand]['responsibility'].append(
                int(article.get('score_openai_responsibility')))

    for car_brand, scores in car_brand_scores.items():
        for category in scores:
            scores[category] = mean(scores[category])

    # Check if the request explicitly accepts XML
    if 'application/xml' in request.headers.get('Accept', ''):
        xml_output = xmltodict.unparse(
            {'car_brand_scores': car_brand_scores}, pretty=True)
        return Response(xml_output, mimetype='application/xml')
    else:
        # If the request doesn't specify a preference, or prefers JSON, return JSON
        return jsonify(car_brand_scores)


@app.route('/api/integration/')
@app.route('/api/integration/<company>')
def integration(company):
    color_bg = request.args.get('color-bg', 'white')
    color_container = request.args.get('color-container', 'rosybrown')
    border_color = request.args.get('border-color', 'black')
    score_display = request.args.get('score-display', 'scores-unfilled')
    font_family = request.args.get('font-family', 'Verdana')

    if company:
        conn = get_db_connection()
        articles = conn.execute('SELECT * FROM articles WHERE LOWER(company) = ?',
                                (company.lower(),)).fetchall()
        conn.close()

        car_brand_score = {}

        articles_list = [dict(article) for article in articles]

        for article in articles_list:
            car_brand = article.get('company')

            if car_brand.lower() not in car_brand_score:
                car_brand_score[car_brand] = {
                    'customer_service': [int(article.get('score_openai_customer_service'))],
                    'reliability': [int(article.get('score_openai_reliability'))],
                    'responsibility': [int(article.get('score_openai_responsibility'))]
                }
            else:
                car_brand_score[car_brand]['customer_service'].append(
                    int(article.get('score_openai_customer_service')))
                car_brand_score[car_brand]['reliability'].append(
                    int(article.get('score_openai_reliability')))
                car_brand_score[car_brand]['responsibility'].append(
                    int(article.get('score_openai_responsibility')))

        for car_brand, scores in car_brand_score.items():
            for category in scores:
                scores[category] = mean(scores[category])

        return render_template('iframe.html',
                               company=company,
                               customer_service=car_brand_score[car_brand]['customer_service'],
                               reliability=car_brand_score[car_brand]['reliability'],
                               responsibility=car_brand_score[car_brand]['responsibility'],
                               color_bg=color_bg,
                               color_container=color_container,
                               border_color=border_color,
                               score_display=score_display,
                               font_family=font_family,
                               )
    else:
        return render_template('iframe.html',
                               company='Score preview',
                               color_bg=color_bg,
                               color_container=color_container,
                               border_color=border_color,
                               score_display=score_display,
                               font_family=font_family,
                               )


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_article(article_id):
    conn = get_db_connection()
    article = conn.execute('SELECT * FROM articles WHERE id = ?',
                        (article_id,)).fetchone()
    conn.close()
    if article is None:
        abort(404)
    return article
