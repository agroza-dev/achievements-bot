CREATE TABLE IF NOT EXISTS new_rate_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recipient_user_id INTEGER NOT NULL, -- Пользователь, над чьим сообщением, совершается действие
  actor_user_id INTEGER NOT NULL,     -- Пользователь, который совершает действие
  chat_id INTEGER NOT NULL DEFAULT 0, -- Чат, в котором происходит действие
  points INTEGER NOT NULL,            -- Количество очков
  message INTEGER,                    -- Id сообщения, по отношению к которому совершается действие
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);


INSERT INTO new_rate_history (id, recipient_user_id, actor_user_id, points, message, created_at)
SELECT id, appreciated_user AS recipient_user_id, rated_user AS actor_user_id, points, message, created_at
FROM rate_history;

DROP TABLE rate_history;

ALTER TABLE new_rate_history RENAME TO rate_history;