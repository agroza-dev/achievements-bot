CREATE TABLE IF NOT EXISTS user_new (
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL DEFAULT 0,
    user_name STRING NOT NULL,
    points_rate INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, chat_id)
);

INSERT INTO user_new (user_id, user_name, points_rate)
SELECT id AS user_id, name, points_rate FROM user;

DROP TABLE user;

ALTER TABLE user_new RENAME TO user;