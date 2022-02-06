#!/bin/bash


psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER $APP_DB_USER WITH PASSWORD '$APP_DB_PASS';
    CREATE DATABASE $APP_DB_NAME;
    GRANT ALL PRIVILEGES ON DATABASE $APP_DB_NAME TO $APP_DB_USER;
    \connect $APP_DB_NAME $APP_DB_USER

    CREATE TYPE "PLATFORM" AS ENUM (
    'AMT'
    );

    CREATE TYPE "STATUS" AS ENUM (
    'CREATING',
    'CREATED'
    );


    CREATE TABLE IF NOT EXISTS "Answers" (
        id integer NOT NULL,
        "Answer" json,
        "AssignmentStatus" character varying,
        "WorkerId" character varying NOT NULL,
        "AssignmentId" character varying,
        "ProjectId" integer,
        "HITId" character varying,
        "HITTypeId" character varying,
        "SubmitTime" timestamp with time zone DEFAULT now()
	);

	CREATE SEQUENCE "Answers_id_seq"
        AS integer
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER SEQUENCE "Answers_id_seq" OWNED BY "Answers".id;


    CREATE TABLE "Hits" (
        id integer NOT NULL,
        project_id integer,
        inputs json,
        created_at timestamp with time zone DEFAULT now() NOT NULL,
        hash_id character varying NOT NULL
    );

    CREATE SEQUENCE "Hits_id_seq"
        AS integer
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;

    ALTER SEQUENCE "Hits_id_seq" OWNED BY "Hits".id;



    CREATE TABLE "Projects" (
        id integer NOT NULL,
        name character varying NOT NULL,
        html_template_path character varying NOT NULL,
        input_csv_path character varying NOT NULL,
        created_at timestamp with time zone DEFAULT now() NOT NULL,
        answer_link character varying,
        answer_link_created_at character varying,
        n_assignment integer,
        status "STATUS",
        platform "PLATFORM",
        data_for_amt json,
        n_hits integer
    );


    CREATE SEQUENCE "Projects_id_seq"
        AS integer
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;

    ALTER SEQUENCE "Projects_id_seq" OWNED BY "Projects".id;

    ALTER TABLE ONLY public."Answers" ALTER COLUMN id SET DEFAULT nextval('public."Answers_id_seq"'::regclass);

    ALTER TABLE ONLY public."Hits" ALTER COLUMN id SET DEFAULT nextval('public."Hits_id_seq"'::regclass);

	ALTER TABLE ONLY public."Projects" ALTER COLUMN id SET DEFAULT nextval('public."Projects_id_seq"'::regclass);

	ALTER TABLE ONLY public."Answers"
    ADD CONSTRAINT "Answers_pkey" PRIMARY KEY (id);

	ALTER TABLE ONLY public."Hits"
    ADD CONSTRAINT "Hits_pkey" PRIMARY KEY (id);

	ALTER TABLE ONLY public."Projects"
    ADD CONSTRAINT "Projects_pkey" PRIMARY KEY (id);

	ALTER TABLE ONLY public."Answers"
    ADD CONSTRAINT answer_project_fk FOREIGN KEY ("ProjectId") REFERENCES public."Projects"(id) NOT VALID;

	ALTER TABLE ONLY public."Hits"
    ADD CONSTRAINT project_hit_fk FOREIGN KEY (project_id) REFERENCES public."Projects"(id);

  COMMIT;

EOSQL