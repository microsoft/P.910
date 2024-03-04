"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

from fastapi import FastAPI,  Response, Request,  status, BackgroundTasks,  Header
from fastapi import Form
from fastapi.staticfiles import StaticFiles
import psycopg2
from psycopg2.extras import RealDictCursor
import time,random
import hashlib
import aiofiles
import os
from jinja2 import Environment, Template, FileSystemLoader
import csv
import json
from shutil import copyfile
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime
import pandas as pd
from fastapi import File, UploadFile

app = FastAPI()


#origins = [
#    "",
#    "http://localhost",
#    "localhost",
#    "http://localhost:8000",
#   "http://localhost:8080"
#]

#app.add_middleware(
#    CORSMiddleware,
#    allow_origins=origins,
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"]
#)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=Path(BASE_DIR, "static")), name="static")

BASE_URL = None

while True:
    try:
        print("***************try to connect************")
        now = datetime.now()

        current_time = now.strftime("%H:%M:%S")
        print("Current Time =", current_time)
        #if not 'POSTGRES_SERVER' in os.environ:
        #    load_dotenv('../.env')
        #    os.environ['POSTGRES_SERVER'] = 'localhost'
        #    print("no environment variable")

        conn = psycopg2.connect(host=os.environ['POSTGRES_SERVER'],
                                port=os.environ['POSTGRES_PORT'],
                                dbname=os.environ['APP_DB_NAME'],
                                user=os.environ['APP_DB_USER'],
                                password=os.environ['APP_DB_PASS'],
                                cursor_factory=RealDictCursor)

        print('connected to database')
        break
    except Exception as error:
        print("Connection failed")
        print(error)
        time.sleep(2)


@app.get("/")
async def root():
    return {"message": "Welcome to the HIT App server."}


@app.get("/version")
def test():
    return {'version': '0.1'}


def set_base_url(url):
    global BASE_URL
    if BASE_URL is not None:
        return
    url = url.split('?')[0]
    possible_entries = ['/create_project.html',
                       '/index.html',
                       '/project_status.html',
                       '/verification.html']
    for st in possible_entries:
        if st in url:
            BASE_URL = url.replace(st, '/api')
            print("+++++++++++++++++++++")
            print(f"####### BASE URL:{BASE_URL}")
            print("-----------------------")
            return



@app.post("/projects")
async def create_project(response: Response,
                         request: Request,
                         background_tasks: BackgroundTasks,
                         html_template: UploadFile = File(...),
                         csv_variables: UploadFile = File(...),
                         project_name: str = Form(...),
                         num_assignment: int = Form(...),
                         platform: str = Form(...)):
    set_base_url(request.headers['referer'])
    with conn.cursor() as cursor:
        response.status_code = status.HTTP_202_ACCEPTED
        hash_name = int(hashlib.sha256(project_name.encode('utf-8')).hexdigest(), 16) % 10**15

        out_file_path_html = f"{BASE_DIR}/static/projects/{hash_name}.html"
        out_file_path_csv = f"{BASE_DIR}/static/projects/{hash_name}.csv"

        #store html file
        async with aiofiles.open(out_file_path_html, 'wb') as out_file:
            content = await html_template.read()  # async read
            await out_file.write(content)  # async write

        # store csv file
        async with aiofiles.open(out_file_path_csv, 'wb') as out_file:
            content = await csv_variables.read()  # async read
            await out_file.write(content)  # async write

        cursor.execute("""INSERT INTO "Projects"(name, html_template_path, input_csv_path, n_assignment, status, platform) VALUES(%s, %s, %s, %s, %s, %s) RETURNING id""",
                       (project_name, out_file_path_html, out_file_path_csv, num_assignment, "CREATING", platform))

        conn.commit()
        project_id = cursor.fetchone()['id']
        print(project_id)
        background_tasks.add_task(create_hits, project_id, hash_name, out_file_path_html, out_file_path_csv)
        #return {"message":f"done: {project_id}"}
        #res = RedirectResponse(f'{BASE_URL}/static/html/project_status.html?id={project_id}')
        res = RedirectResponse(f'../project_status.html?id={project_id}')
        res.status_code = status.HTTP_302_FOUND
        return res


def generate_hit_id(row):
    flatten_row = ''.join(row.values())+str(random.randint(1000, 9999))
    return hashlib.md5(flatten_row.encode()).hexdigest()


def get_customized_html(hit_app_template, row):
    return hit_app_template.render(row)


async def create_hits(project_id, project_name, html_template, input_csv):
    """
    Runs in the background and create the HITs from the template
    :param project_id:
    :return:
    """
    print('start background task')
    with conn.cursor() as cursor:
        config = {}
        config['hit_type_id'] = project_name
        config['project_id'] = project_id
        tmp = os.path.split(os.path.abspath(html_template))
        env = Environment(loader=FileSystemLoader(searchpath=tmp[0]), variable_start_string='${', variable_end_string='}')

        hit_app_template = env.get_template(tmp[1])

        async with aiofiles.open(f'{BASE_DIR}/res/frame_template.html', 'r', encoding="utf8") as file:
            form_row = await file.read()
            file.seek(0)
        form_template = Template(form_row)

        print('Start by create_hits...')
        hit_urls = []
        with open(input_csv, encoding="utf8") as csvfile:
            reader = csv.DictReader(csvfile)
            # lowercase the fieldnames
            # reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
            for row in reader:
                print(f'start by row: {row}')
                row = dict(row)
                hit_id = f'{config["hit_type_id"]}_{generate_hit_id(row)}'
                config['hit_id'] = hit_id

                config['html'] = get_customized_html(hit_app_template, row)
                form_html = form_template.render(cfg=config)
                out_path = os.path.join(f'{BASE_DIR}/static/hits', hit_id + '.html')

                async with aiofiles.open(out_path, 'w', encoding="utf8") as file:
                    await file.write(form_html)
                config.pop('html', None)
                tmp_row = row.copy()
                tmp_row['hit_type_id'] = project_name
                inputs = {f"Input.{key}": val for key, val in tmp_row.items()}
                #url = f'{BASE_URL}/static/hits/{hit_id}.html?assignmentId='+'{0}'+'&campaign_id=hit_app_server'
                url = f'{BASE_URL}/static/hits/{hit_id}.html?assignmentId=' + '{0}' + '&campaign_id=hit_app_server'
                hit_urls.append({'url': url})
                cursor.execute("""INSERT INTO "Hits"(project_id, inputs, hash_id) VALUES(%s, %s, %s)""",
                               (project_id,  json.dumps(inputs), hit_id))
        conn.commit()
        csv_path = f'static/downloads/data_{project_name}.csv'
        html_path = f'static/downloads/AMT_{project_name}.html'
        await write_dict_as_csv(hit_urls, f'{BASE_DIR}/{csv_path}')
        copyfile(f'{BASE_DIR}/res/HIT_app_rand_assignment.html', f'{BASE_DIR}/{html_path}')

        data_for_amt = {'csv':f'{BASE_URL}/{csv_path}',
                'html':f'{BASE_URL}/{html_path}'}
        # record the list of urls

        cursor.execute("""UPDATE "Projects" SET  data_for_amt =%s, n_hits=%s, status=%s WHERE id =%s""",
                       (json.dumps(data_for_amt), len(hit_urls), "CREATED", project_id))
        conn.commit()


@app.get("/projects")
def list_project(request: Request, skip: int = 0, limit: int = 20):
    set_base_url(request.headers['referer'])
    projects = []
    with conn.cursor() as cursor:
        cursor.execute("""SELECT * FROM "Projects" order by created_at DESC LIMIT %s OFFSET %s""", (limit, skip))
        for project in cursor.fetchall():
            projects.append(project)
        return projects


@app.get("/projects/{id}")
def get_project(request: Request, id: int):
    set_base_url(request.headers['referer'])
    with conn.cursor() as cursor:
        print(id)
        cursor.execute("""SELECT * FROM "Projects" where id =%s """, (str(id), ))
        project = cursor.fetchone()
        return{'project': project}
    
@app.get("/projects/{id}/answers/download")
def get_project_results(request: Request, id:int, background_tasks: BackgroundTasks):
    set_base_url(request.headers['referer'])
    background_tasks.add_task(create_ans_csv, id)


async def create_ans_csv(project_id):
    """
    Runs in the background and create the answer.csv to download
    :param project_id:
    :return:
    """
    hits = {}
    # get the HITs
    with conn.cursor() as cursor:
        cursor.execute("""SELECT inputs, hash_id FROM "Hits" where "project_id" = %s """, (project_id, ))
        for hit in cursor.fetchall():
            hits[hit['hash_id']] = hit['inputs']
    # create the answer csv
    answers = []
    with conn.cursor() as cursor:
        cursor.execute("""SELECT * FROM "Answers" where "ProjectId" = %s """, (project_id, ))
        for ans in cursor.fetchall():
            ans_part = ans.pop('Answer')
            tmp = hits[ans['HITId']]
            answers.append({**ans, **ans_part, **tmp})
        ans_path = f'static/downloads/Batch_{project_id}.csv'
        await write_dict_as_csv(answers, f'{BASE_DIR}/{ans_path}')
        cursor.execute("""UPDATE "Projects" SET  answer_link =%s, answer_link_created_at=NOW() """,
                       (BASE_URL+"/"+ans_path,))
        conn.commit()


async def write_dict_as_csv(dic_to_write, file_name):
    """
    async with aiofiles.open(file_name, 'w', newline='', encoding="utf8") as output_file:
        if len(dic_to_write)>0:
            headers = list(dic_to_write[0].keys())
            writer = csv.DictWriter(output_file, fieldnames=headers)
            await writer.writeheader()
            for d in dic_to_write:
                await writer.writerow(d)
    """
    df = pd.DataFrame(dic_to_write)
    df = df.fillna("")
    df.to_csv(file_name, index=False)


@app.get("/projects/{id}/answers/count")
def get_amt_data(request: Request, response: Response, id: int):
    set_base_url(request.headers['referer'])
    with conn.cursor() as cursor:
        cursor.execute("""SELECT count(id) as count FROM "Answers" where "ProjectId"=%s """, (id,))
        result = cursor.fetchone()
        print(result)
        return result


@app.post("/answers/{project_id}")
async def add_answer(response: Response, info : Request, x_real_ip: str = Header(None, alias='X-Real-IP')):
    req_info = await info.json()
    key_data, answers = json_formater(req_info, 'Answer.')
    with conn.cursor() as cursor:
        v_code = generate_vcode()
        answers['v_code'] = v_code     
        # annonymize the ip, uncomment it if you want to log this information in the answer table
        #answers['X-Real-IP'] = '.'.join(x_real_ip.split('.')[:-1])+'.0/24'
        cursor.execute(
            """INSERT INTO "Answers"("HITTypeId", "HITId", "Answer", "AssignmentStatus", "WorkerId", 
            "AssignmentId", "ProjectId") VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (key_data["HITTypeId"], key_data["HITId"], json.dumps(answers), "Submitted", key_data["WorkerId"],
             key_data["AssignmentId"], key_data["ProjectId"]))
        conn.commit()
    print(v_code)
    return {'vcode': v_code}


def json_formater(ajax_post, prefix=""):
    key_prop = ["hittypeid", "hitid", "assignmentid", "workerid", "url", "campaignid", "projectid"]
    key_remove = ["start_working_time","submission_time"]
    key_without_prefix = ["work_duration_sec"]
    data = {}
    key_data = {}
    for item in ajax_post:
        name = item["name"].lower()
        if name in key_remove: continue
        if name in key_prop:
            key_data[f'{item["name"]}'] = item["value"]
        elif name in key_without_prefix:
            data[f'{item["name"]}'] = item["value"]
        else:
            data[f'{prefix}{item["name"]}'] = item["value"]
    return key_data, data


def generate_vcode():
    rand = str(random.randint(1000, 9999)) + str(random.randint(1000, 9999)) + str(random.randint(1000, 9999))
    return hashlib.md5(rand.encode()).hexdigest()


@app.delete("/projects/{id}")
def del_project(id: int, background_tasks: BackgroundTasks):
    """
    Deletes a project
    """
    with conn.cursor() as cursor:
        # delete answers
        #cursor.execute(""" DELETE FROM public."Answers" WHERE  ProjectId= %s""", (id,))
        #conn.commit()
        # delete files
        print(id)
        cursor.execute("""SELECT * FROM "Projects" where id =%s """, (str(id), ))
        project = cursor.fetchone()
        html = project["data_for_amt"]["html"]
        html_projects = html.replace("downloads/AMT_", "projects/")
        csv_file = project["data_for_amt"]["csv"]
        csv_projects = csv_file.replace("downloads/data_", "projects/")
        delete_file(html)
        delete_file(csv_file)
        delete_file(html_projects)
        delete_file(csv_projects)
        
        # delete HITs
        cursor.execute("""SELECT hash_id FROM "Hits" WHERE  project_id= %s""", (id,))
        hits = []
        for hit in cursor.fetchall():
            hits.append(hit)
        print(hits)
        #background_tasks.add_task(delete_file, project_id, hash_name, out_file_path_html, out_file_path_csv)
        cursor.execute(""" DELETE FROM "Hits" WHERE  project_id= %s""", (id,))
        # delete project
        cursor.execute(""" DELETE FROM "Projects" WHERE  id= %s""", (id,))

def delete_file(filename):
    if filename[:4] == "http":
        filename = "/".join(filename.split("/")[3:])
    print(f"delete_file: {filename}")
    try:
        os.remove(f'./{filename}')
    except Exception as e:
        print(e)

"""
@app.post("/rec")
async def store_recordings(assignment_id: str = Form(...) , file: UploadFile = File(...)):
    v_code = generate_vcode()
    print(f'store_recordings: {assignment_id}, {v_code}')
    out_file_path_html=Path(BASE_DIR, f"static/rec/{assignment_id}.wav")
    # store html file
    async with aiofiles.open(out_file_path_html, 'wb') as out_file:
        content = await file.read()  # async read
        await out_file.write(content)  # async write

    return {"vcode": v_code}


@app.post("/recjson")
async def store_recordings2(response: Response, info : Request):
    req_info = await info.json()
    print(req_info)


@app.get("/rec_exist/{assignment_id}")
def check_recording_exist(response: Response, assignment_id:str):
    out_file_path_html = Path(BASE_DIR, f"static/rec/{assignment_id}.wav")
    if os.path.isfile(out_file_path_html):
        return {'exist': 1}
    else:
        return {'exist': 0}

"""