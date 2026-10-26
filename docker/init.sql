create schema api;

create table api.todos (
    id    bigint generated always as identity primary key,
    title text    not null,
    done  boolean not null default false
);

insert into api.todos (title, done) values
    ('Write the query builder', true),
    ('Add the async client', true),
    ('Publish 0.1.0', false);

create role web_anon nologin;
grant usage on schema api to web_anon;
grant select, insert on api.todos to web_anon;

create role authenticator noinherit login password 'authenticator';
grant web_anon to authenticator;
