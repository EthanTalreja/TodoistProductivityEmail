import requests
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To
import firebase_admin
from firebase_admin import firestore

count = 0
firestore_client = 0

# todoist api
token = '** REMOVED FOR PRIVACY **'
url = 'https://api.todoist.com/rest/v2/tasks'
headers = {'Authorization' : 'Bearer {}'.format(token), 'Content-Type': 'application/json'}

# sendgrid api
api_key = 'S** REMOVED FOR PRIVACY **'

def initialize_firebase():
    credentials = {
  "type": "service_account",
  "project_id": "** REMOVED FOR PRIVACY **",
  "private_key_id": "** REMOVED FOR PRIVACY **",
  "private_key": "** REMOVED FOR PRIVACY **n",
  "client_email": "** REMOVED FOR PRIVACY **",
  "client_id": "** REMOVED FOR PRIVACY **",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "** REMOVED FOR PRIVACY **",
  "universe_domain": "googleapis.com"
    }
    cred_obj = firebase_admin.credentials.Certificate(credentials)
    default_app = firebase_admin.initialize_app(cred_obj)
    firestore_clien = firestore.client()
    global firestore_client
    firestore_client = firestore_clien
    global count
    count += 1

    
def getTodoistTasks():
    response = requests.get(url, headers=headers)
    todoist_task_list = response.json()
    return todoist_task_list

def parse_todoist_json(todoist_task_list):
    task_list = []
    
    for task_json in todoist_task_list:
        task = {}
        task['name'] = task_json['content']
        task['due_date'] = task_json['due']['date']
        task['id'] = task_json['id']
        task['priority'] = task_json['priority']
        task['project_id'] = task_json['project_id']
        task['description'] = task_json['description']
        task['url'] = task_json['url']
        task['status'] = 'completed' if task_json['is_completed'] == True else 'active'
        task_list.append(task)
        
    return task_list

def filter_tasks_to_due_date_today(task_list, past_midnight):
    new_task_list = []
    today = datetime.today().strftime("%Y-%m-%d")
    if past_midnight:
        today = today - timedelta(1)
    
    for task in task_list:
        if task['due_date'] == today:
            new_task_list.append(task)
            
    return new_task_list

def filter_tasks_to_due_date_tomorrow(task_list, past_midnight):
    new_task_list = []
    today = datetime.today()
    if not past_midnight:
        tomorrow = today + timedelta(1)
    else:
        tomorrow = today
    tomorrow = tomorrow.strftime("%Y-%m-%d")
    
    for task in task_list:
        if task['due_date'] == tomorrow:
            new_task_list.append(task)
            
    task_ids = []
    
    for task in new_task_list:
        task_ids.append(task['id'])
            
    return new_task_list, tomorrow, task_ids

def separate_sorted_by_priorities(new_task_list):
    p1 = []
    p2 = []
    p3 = []
    none = []
    
    for task in new_task_list:
        if task['priority'] == 1:
            none.append(task)
        elif task['priority'] == 2:
            p3.append(task)
        elif task['priority'] == 3:
            p2.append(task)
        else:
            p1.append(task)
            
    return p1,p2,p3,none

def populate_email(p1, p2, p3, none, title, unique_message):
    
    button = """
    <center>
        <a href="a*5" style="padding: 7px 20px; background-color: #0087B2; color: #FBFBFB; 
        text-decoration: none; border-radius: 5px;">View</a>
    </center>
    """
    
    p1_content = ''
    
    for task in p1:
        content = "<tr><td>{}</td><td>".format(task['name'])
        content += button.replace('a*5', task['url'])
        content += "</td></tr>"
        p1_content += content 
        
    p2_content = ''
    
    for task in p2:
        content = "<tr><td>{}</td><td>".format(task['name'])
        content += button.replace('a*5', task['url'])
        content += "</td></tr>"
        p2_content += content 
        
    p3_content = ''
    
    for task in p3:
        content = "<tr><td>{}</td><td>".format(task['name'])
        content += button.replace('a*5', task['url'])
        content += "</td></tr>"
        p3_content += content 
        
    none_content = ''
    
    for task in none:
        content = "<tr><td>{}</td><td>".format(task['name'])
        content += button.replace('a*5', task['url'])
        content += "</td></tr>"
        none_content += content 

    
    html_content = """
    <!DOCTYPE html>
    <html style="margin:0; padding:0; width:100%;">

    <head>
        <style>
            body {
                background-color: #eaeaea;
                width: 100%;
                min-width: fit-content;
                margin:0;
                padding:0;
            }

            table {
                margin-left: 20px;
            }

            th, td {
                width: 33%;
                padding: 10px;
            }

            h1, p {
                padding-left: 30px;
                padding-top: 20px;
            }

            table, th, td {
            text-align: center;
                vertical-align: middle;
            }
        </style>
    </head>

    <body>
    """
    
    html_content += unique_message + "<br>"
    
    html_content += """
        <h1>P1 tasks</h1>
        <table>
            {p1_html_content}
        </table>
        <br>
        <h1>P2 tasks</h1>
        <table>
            {p2_html_content}
        </table>
        <br>
        <h1>P3 tasks</h1>
        <table>
            {p3_html_content}
        </table>
        <br>
        <h1>No priority tasks</h1>
        <table>
            {none_html_content}
        </table>
    </body>

    </html>
        """.format(p1_html_content=p1_content, p2_html_content=p2_content, p3_html_content=p3_content, 
                   none_html_content=none_content)
    
    
    message = Mail(
    from_email = From('** REMOVED FOR PRIVACY **', '** REMOVED FOR PRIVACY **'),
    to_emails='** REMOVED FOR PRIVACY **',
    subject = title,
    html_content=html_content)
    
    return message

def send_email(message):
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        if response.status_code == 202:
            print('Sent!')
    except Exception as e:
        print(e.message)

def check_task_completion():
    return None

def send_next_day_preview_email():

    # adds tasks to firebase and returns list of tasks and date
    tomorrow_task_list = add_tomorrow_tasks_to_firebase()
    
    # sorts task list by priority
    p1,p2,p3,none = separate_sorted_by_priorities(tomorrow_task_list)
    
    # populates email
    tomorrow = datetime.today() + timedelta(1)
    tomorrow = tomorrow.strftime("%m.%d.%Y")
    
    title = "Take a peak at {} tasks".format(tomorrow)
    unique_message = "<p> Tomorrow, you have <strong>{} tasks </strong>!</p>".format(len(tomorrow_task_list))
    message = populate_email(p1, p2, p3, none, title, unique_message)
    
    # send email
    send_email(message)


def add_tomorrow_tasks_to_firebase():
    # get today tasks
    todoist_task_list = getTodoistTasks()
    task_list = parse_todoist_json(todoist_task_list)
    
    # gets list of tasks for tmrw, formatted date, and list of task IDs
    tomorrow_task_list, tomorrow, task_ids = filter_tasks_to_due_date_tomorrow(task_list, True)
    
    # adds tasks to Firebase
    add_tasks_to_firebase(tomorrow, tomorrow_task_list, task_ids)
    
    return tomorrow_task_list


def add_tasks_to_firebase(docName, task_list, task_ids):
    global firestore_client
    doc_ref = firestore_client.collection("tasks").document(docName)
    doc_ref.set({'tasks': task_list, 'task_ids': task_ids})

def send_morning_preview_email():
    # get today tasks
    todoist_task_list = getTodoistTasks()
    task_list = parse_todoist_json(todoist_task_list)
    today_task_list = filter_tasks_to_due_date_today(task_list, False)
    
    # sorts task list by priority
    p1,p2,p3,none = separate_sorted_by_priorities(today_task_list)
    
    # populates email
    today = datetime.today()
    today = today.strftime("%m.%d.%Y")
    
    title = "Prepare for today | {} tasks".format(today)
    unique_message = "<p> Today, you have <strong>{} tasks </strong>!</p>".format(len(today_task_list))
    message = populate_email(p1, p2, p3, none, title, unique_message)
    
    # send email
    send_email(message)

def send_midday_review_email():
    # get today tasks
    todoist_task_list = getTodoistTasks()
    task_list = parse_todoist_json(todoist_task_list)
    today_task_list = filter_tasks_to_due_date_today(task_list, False)
    
    # sorts task list by priority
    p1,p2,p3,none = separate_sorted_by_priorities(today_task_list)
    
    # populates email
    today = datetime.today()
    today = today.strftime("%m.%d.%Y")
    
    title = "Midday Review | {} tasks".format(today)
    unique_message = "<p> You have <strong>{} tasks to go</strong>!</p>".format(len(today_task_list))
    message = populate_email(p1, p2, p3, none, title, unique_message)
    
    # send email
    send_email(message)

def send_evening_review_email():
    # get today tasks
    todoist_task_list = getTodoistTasks()
    task_list = parse_todoist_json(todoist_task_list)
    today_task_list = filter_tasks_to_due_date_today(task_list, False)
    
    # sorts task list by priority
    p1,p2,p3,none = separate_sorted_by_priorities(today_task_list)
    
    # populates email
    today = datetime.today()
    today = today.strftime("%m.%d.%Y")
    
    title = "Evening Review | {} tasks".format(today)
    unique_message = "<p> You have <strong>{} tasks to go</strong>!</p>".format(len(today_task_list))
    message = populate_email(p1, p2, p3, none, title, unique_message)
    
    # send email
    send_email(message)

def send_end_of_day_review_email():
    # get today tasks
    todoist_task_list = getTodoistTasks()
    task_list = parse_todoist_json(todoist_task_list)
    today_task_list = filter_tasks_to_due_date_today(task_list, True)
    
    # sorts task list by priority
    p1,p2,p3,none = separate_sorted_by_priorities(today_task_list)
    
    # populates email
    today = datetime.today()
    today = today.strftime("%m.%d.%Y")
    
    title = "End of Day Review | {} tasks".format(today)
    unique_message = "<p> There are <strong>{} tasks uncompleted</strong>!</p>".format(len(today_task_list))
    message = populate_email(p1, p2, p3, none, title, unique_message)
    
    # send email
    send_email(message)

def main(a,b):
    print(count)
    if count == 0:
        initialize_firebase()
    now = datetime.now()
    time = now.strftime("%H:%M")
    
    if time == '12:30':
        send_morning_preview_email()
    elif time == '16:00':
        send_midday_review_email()
    elif time == '21:00':
        send_evening_review_email()
    elif time == '03:00':
        send_end_of_day_review_email()
    elif time == '03:03':
        send_next_day_preview_email()

main(1,2)

