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

create table quiz (
	id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
	created_at TIMESTAMP,				
	updated_at TIMESTAMP,
	is_deleted BOOLEAN,
	user_id UUID REFERENCES "user" (id),
	set_id UUID REFERENCES "set" (id),
	public_or_not BOOLEAN
);

create table quiz_question(
    user_id UUID NOT NULL,
    set_id UUID NOT NULL,
    PRIMARY KEY (user_id, set_id),
    FOREIGN KEY (user_id) REFERENCES "user" (id),
    FOREIGN KEY (set_id) REFERENCES "set" (id)
);

create table quiz_question_answer(
    user_id UUID NOT NULL,
    set_id UUID NOT NULL,
    PRIMARY KEY (user_id, set_id),
    FOREIGN KEY (user_id) REFERENCES "user" (id),
    FOREIGN KEY (set_id) REFERENCES "set" (id),
	json_question_answer JSONB
);