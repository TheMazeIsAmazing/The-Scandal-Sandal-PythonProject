DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS api_pulls;

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

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    role INT NOT NULL DEFAULT 0
);

CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    key TEXT NOT NULL,
    note TEXT NOT NULL,
    account_id INTEGER,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

CREATE TABLE api_pulls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    key INTEGER,
    origin TEXT NOT NULL,
    FOREIGN KEY (key) REFERENCES api_keys (id)
);