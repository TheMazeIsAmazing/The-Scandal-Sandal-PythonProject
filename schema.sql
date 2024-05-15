DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS articles;

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT NOT NULL,
    content TEXT NOT NULL
);

CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    headline TEXT NOT NULL,
    content TEXT NOT NULL,
    score_openai_customer_service SMALLINT NOT NULL,
    ex_score_openai_customer_service TEXT NOT NULL,
    score_openai_reliability SMALLINT NOT NULL,
    ex_score_openai_reliability TEXT NOT NULL,
    score_openai_responsibility SMALLINT NOT NULL,
    ex_score_openai_responsibility TEXT NOT NULL
);