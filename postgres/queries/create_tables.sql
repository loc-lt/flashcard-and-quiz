CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

create table "user" (
	id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
	name VARCHAR(50),
	email VARCHAR(50),
	password VARCHAR(200),
	role INT,
	created_at TIMESTAMP,
	updated_at TIMESTAMP,
	is_deleted BOOLEAN
);

create table "set" (
	id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
	user_id UUID REFERENCES "user" (id),
	created_at TIMESTAMP,				
	updated_at TIMESTAMP,
	is_deleted BOOLEAN,
	public_or_not BOOLEAN,
	description VARCHAR(200)
);

create table question (
	id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
	content VARCHAR(500),
	type VARCHAR(20),
	set_id UUID REFERENCES "set" (id),
	created_at TIMESTAMP,				
	updated_at TIMESTAMP,
	is_deleted BOOLEAN
);

create table answer (
	id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
	content VARCHAR(100),
	is_correct BOOLEAN,
	question_id UUID REFERENCES question (id),
	created_at TIMESTAMP,				
	updated_at TIMESTAMP,
	is_deleted BOOLEAN
);