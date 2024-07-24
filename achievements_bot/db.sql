create table bot_user (
  telegram_id bigint primary key,
  created_at timestamp default current_timestamp not null
);