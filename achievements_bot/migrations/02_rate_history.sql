CREATE TABLE IF NOT EXISTS rate_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  appreciated_user INTEGER not null ,
  rated_user INTEGER not null,
  points INTEGER not null,
  message INTEGER,
  created_at timestamp default current_timestamp not null
);