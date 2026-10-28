-- EduPilot AI - PostgreSQL schema (generated from app/models.py)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
	user_id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) DEFAULT 'student' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (user_id), 
	CONSTRAINT ck_users_role CHECK (role IN ('student','instructor','admin'))
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE courses (
	course_id SERIAL NOT NULL, 
	course_name VARCHAR(150) NOT NULL, 
	course_code VARCHAR(30), 
	semester VARCHAR(40), 
	credits INTEGER DEFAULT '3' NOT NULL, 
	description TEXT, 
	color VARCHAR(20), 
	instructor_id INTEGER, 
	created_by INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (course_id), 
	CONSTRAINT ck_courses_credits CHECK (credits > 0 AND credits <= 30), 
	FOREIGN KEY(instructor_id) REFERENCES users (user_id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by) REFERENCES users (user_id) ON DELETE SET NULL
);

CREATE INDEX ix_courses_instructor_id ON courses (instructor_id);

CREATE TABLE ai_predictions (
	prediction_id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	predicted_score FLOAT NOT NULL, 
	lower_bound FLOAT NOT NULL, 
	upper_bound FLOAT NOT NULL, 
	risk_level VARCHAR(10) NOT NULL, 
	features JSONB NOT NULL, 
	model_version VARCHAR(50) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (prediction_id), 
	CONSTRAINT ck_predictions_range CHECK (predicted_score >= 0 AND predicted_score <= 100), 
	CONSTRAINT ck_predictions_risk CHECK (risk_level IN ('low','medium','high')), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE CASCADE
);

CREATE INDEX ix_predictions_user_course_time ON ai_predictions (user_id, course_id, created_at);

CREATE TABLE ai_recommendations (
	recommendation_id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	reason TEXT NOT NULL, 
	topics JSONB NOT NULL, 
	priority VARCHAR(10) NOT NULL, 
	source VARCHAR(10) DEFAULT 'rules' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (recommendation_id), 
	CONSTRAINT ck_recommendations_priority CHECK (priority IN ('low','medium','high')), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE CASCADE
);

CREATE INDEX ix_recommendations_user ON ai_recommendations (user_id);

CREATE TABLE assignments (
	assignment_id SERIAL NOT NULL, 
	course_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	due_date DATE NOT NULL, 
	status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
	priority VARCHAR(10) DEFAULT 'medium' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (assignment_id), 
	CONSTRAINT ck_assignments_status CHECK (status IN ('pending','in_progress','completed')), 
	CONSTRAINT ck_assignments_priority CHECK (priority IN ('low','medium','high')), 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE INDEX ix_assignments_course_id ON assignments (course_id);

CREATE INDEX ix_assignments_user_due ON assignments (user_id, due_date);

CREATE TABLE attendance (
	attendance_id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	attendance_date DATE NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (attendance_id), 
	CONSTRAINT ck_attendance_status CHECK (status IN ('present','absent','late','excused')), 
	CONSTRAINT uq_attendance_day UNIQUE (user_id, course_id, attendance_date), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE CASCADE
);

CREATE INDEX ix_attendance_course_id ON attendance (course_id);

CREATE TABLE documents (
	document_id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id INTEGER, 
	filename VARCHAR(255) NOT NULL, 
	stored_path VARCHAR(500) NOT NULL, 
	file_size INTEGER NOT NULL, 
	page_count INTEGER NOT NULL, 
	chunk_count INTEGER NOT NULL, 
	upload_date TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (document_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE SET NULL
);

CREATE INDEX ix_documents_user ON documents (user_id);

CREATE TABLE enrollments (
	user_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	enrollment_date DATE DEFAULT CURRENT_DATE NOT NULL, 
	PRIMARY KEY (user_id, course_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE CASCADE
);

CREATE INDEX ix_enrollments_course ON enrollments (course_id);

CREATE TABLE grades (
	grade_id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	assessment_type VARCHAR(20) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	score FLOAT NOT NULL, 
	max_score FLOAT DEFAULT '100' NOT NULL, 
	weight FLOAT DEFAULT '1' NOT NULL, 
	graded_on DATE DEFAULT CURRENT_DATE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (grade_id), 
	CONSTRAINT ck_grades_type CHECK (assessment_type IN ('quiz','assignment','midterm','final','project','lab','other')), 
	CONSTRAINT ck_grades_max_positive CHECK (max_score > 0), 
	CONSTRAINT ck_grades_score_range CHECK (score >= 0 AND score <= max_score), 
	CONSTRAINT ck_grades_weight_positive CHECK (weight > 0), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE CASCADE
);

CREATE INDEX ix_grades_user_course ON grades (user_id, course_id);

CREATE TABLE study_plans (
	plan_id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id INTEGER, 
	planned_date DATE NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	tasks JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (plan_id), 
	CONSTRAINT uq_study_plan_day UNIQUE (user_id, planned_date), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE SET NULL
);

CREATE TABLE study_sessions (
	session_id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id INTEGER, 
	duration_minutes INTEGER NOT NULL, 
	topic VARCHAR(200), 
	notes TEXT, 
	session_date DATE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (session_id), 
	CONSTRAINT ck_sessions_duration CHECK (duration_minutes > 0 AND duration_minutes <= 1440), 
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (course_id) ON DELETE SET NULL
);

CREATE INDEX ix_sessions_user_date ON study_sessions (user_id, session_date);

CREATE TABLE document_chunks (
	chunk_id SERIAL NOT NULL, 
	document_id INTEGER NOT NULL, 
	chunk_index INTEGER NOT NULL, 
	page_number INTEGER, 
	content TEXT NOT NULL, 
	embedding VECTOR(384) NOT NULL, 
	PRIMARY KEY (chunk_id), 
	CONSTRAINT uq_chunk_position UNIQUE (document_id, chunk_index), 
	FOREIGN KEY(document_id) REFERENCES documents (document_id) ON DELETE CASCADE
);

CREATE INDEX ix_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id);
