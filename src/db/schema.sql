CREATE TABLE IF NOT EXISTS students (
  student_id   VARCHAR(20) PRIMARY KEY,
  name         VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS attempts (
  attempt_id                   VARCHAR(50) PRIMARY KEY,
  student_id                   VARCHAR(20) REFERENCES students(student_id),
  date                         DATE,
  mode                         VARCHAR(20),
  exam_pattern                 VARCHAR(20),
  subject                      VARCHAR(50),
  chapters                     TEXT[],
  duration_minutes             INT,
  time_taken_minutes           INT,
  completed                    BOOLEAN,
  total_questions              INT,
  attempted                    INT,
  skipped                      INT,
  marks_raw                    TEXT,
  marks_score                  NUMERIC(7,2),
  marks_total                  NUMERIC(7,2),
  marks_pct                    NUMERIC(5,2),
  avg_time_per_question_sec    INT,
  slowest_question_id          VARCHAR(100),
  fastest_question_id          VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS questions (
  question_id    VARCHAR(100) PRIMARY KEY,
  question_type  VARCHAR(20),
  subject        VARCHAR(50),
  topic          VARCHAR(100),
  subtopic       VARCHAR(100),
  difficulty     INT,
  question_html  TEXT,
  question_text  TEXT,
  solution_html  TEXT,
  answer         TEXT,
  has_issues     BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS dost_configs (
  dost_type  VARCHAR(50) PRIMARY KEY,
  config     JSONB
);