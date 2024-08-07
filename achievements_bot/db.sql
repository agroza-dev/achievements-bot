create table user (
    id int primary key,
    name string not null,
    points_rate integer not null default 0

);

create table rate_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  appreciated_user INTEGER not null ,
  rated_user INTEGER not null,
  points INTEGER not null,
  message INTEGER,
  created_at timestamp default current_timestamp not null
);