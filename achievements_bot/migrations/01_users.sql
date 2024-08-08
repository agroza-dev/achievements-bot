CREATE TABLE IF NOT EXISTS user (
    id int primary key,
    name string not null,
    points_rate integer not null default 0

);