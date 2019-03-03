from bs4 import BeautifulSoup
from datetime import date, datetime
import requests
from selenium import webdriver
import time
import re
import os
import codecs
from html_bases import HTML_BASE_START,HTML_BASE_END
import webbrowser

teacher_ids_list = []  # This list Contains all teachers ID's
TEMPLATE_NAME = ""  # Stores class template name for filtering
USERNAME = ""  # Stores users UserName
PASSWORD = ""  # Stores users Password
ASSIGNMENT_BASE = "https://magshimim.edu20.org/teacher_assignments/list/"  # Stores Base Assignment URL
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Stores Base Directory
MONTHS = ['Jan', "Feb", 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']  # Stores Month Format
CURRENT_YEAR = 2019  # Stores Default Year Value
relevant_data = {}  # Stores Data to Display
CHECK_TIME = 14  # Stores Base Time for checking assignment



'''
This Function will connect to https://magshimim.edu20.org/
Using the username and password that was entered. 
Inputs are Global.
'''
def login_to_site():
    # Create New session
    with requests.Session() as s:
        url = 'https://magshimim.edu20.org/'
        driver = webdriver.Chrome(executable_path=r'resources/chromedriver.exe')
        driver.get(url)
        # Get Login Button
        button = driver.find_element_by_class_name('loginHolder')
        button.click()
        time.sleep(1)
        username = driver.find_element_by_id("userid")
        password = driver.find_element_by_id("password")
        username.send_keys(USERNAME)
        password.send_keys(PASSWORD)
        # LogIn
        driver.find_element_by_id("submit_button").click()
        time.sleep(1)

        # Download homePage
        content = driver.page_source
        soup = BeautifulSoup(content, 'html.parser')
        with open("data/home.html", 'wb') as out:
            out.write(soup.encode("utf-8"))
        # Find all teacher id's
        get_teacher_ids()
        # Download relevant Pages
        get_teacher_assignments(driver)
        # Extract Data from HTML
        get_teacher_data()
        # Build HTML for presentation
        generate_conclusion()

'''
Download all relevant Pages using teachers ID's
'''
def get_teacher_assignments(driver):
    for id in teacher_ids_list:
        driver.get("https://magshimim.edu20.org/teacher_assignments/list/" + id)
        content = driver.page_source
        # Use soup to parse HTML
        soup = BeautifulSoup(content, 'html.parser')
        relevant = str(soup.find('h1'))
        # data is relevant if Template name is with in
        if TEMPLATE_NAME in relevant:
            with open("data/" + id + ".html", 'wb') as out:
                out.write(soup.encode("utf-8"))
        time.sleep(1)

'''
Extract Teachers ID's from Home Page
'''
def get_teacher_ids():
    with codecs.open('data/home.html', 'r', encoding="utf8") as file:
        home_page = file.read()
        ids = re.findall(r'<a href="/teacher_class/show/\w+', home_page)
        for element in ids:
            teacher_ids_list.append(element.split('show/')[1])

'''
This Function sees all the data and 
calls another function to extract only the relevant parts. 
'''
def get_teacher_data():
    # Get File list from folder
    files_list = get_file_list()
    for file in files_list:
        with open(file, 'r', encoding="utf8") as input_f:
            raw_data = input_f.read()
            t_id = os.path.basename(file)
            t_id = t_id.split('.')[0]
            # Parse text and calculate
            get_relevant_data(raw_data, t_id)
    return "Done"

'''
Get relevant Data From Assignments HTML Pages
'''
def get_relevant_data(raw_data, t_id):
    global relevant_data
    rel_rows = []
    soup = BeautifulSoup(raw_data, 'html.parser')
    # Parse class name
    class_name = soup.find("h1")
    class_name = str(class_name).replace('\n', '')
    class_name = class_name.replace('<h1>', '')
    class_name = class_name.replace('</h1>', '')
    class_name = class_name.lstrip()
    class_name = class_name.rstrip()
    rows = soup.find_all("tr")
    # save only Rows with Dates
    for row in rows:
        for month in MONTHS:
            if month in str(row):
                rel_rows.append(str(row))
    for row in rel_rows:
        try:
            to_grade = None
            if 'Essay' in str(row):
                # Get assignment name
                ass_name = row.split('title="Essay:')[1]
                ass_name = ass_name.split('</a>')[0]
                ass_name = ass_name.split('>')[0]
                ass_name = ass_name.replace('"', '')
                # Calculate Due
                due = row.split('<td class="hideCell">')[2]
                if len(due) > 6:
                    due = due.split('<')[0]
                due = due.split('<br/>')[0]
                due = due.replace('\n', '')
                due = due.replace('\t', '')
                due = due.lstrip()
                due = due.rstrip()
                due_day = datetime.strptime(due + ' ' + str(CURRENT_YEAR), '%b %d %Y')
                today = date.today()
                days_passed = datetime.today() - due_day
                days_passed = str(days_passed).split(' ')[0]
                # if days past is negative we need to take the previous year
                if '-' in days_passed:
                    due_day = datetime.strptime(due + ' ' + str(CURRENT_YEAR - 1), '%b %d %Y')
                    today = date.today()
                    days_passed = datetime.today() - due_day
                    days_passed = str(days_passed).split(' ')[0]
                # Get Given indicator
                given = row.split('<span class="textOffScreen">')[1]
                given = given.split('</span>')[0]
                try:
                    # if teacher has assignments to grade this line will appear in the row
                    if '/teacher_freeform_assignment/to_grade/' in str(row):
                        to_grade = row.split('<a href="/teacher_freeform_assignment/to_grade/')[0]
                        to_grade = to_grade.split('<td align="center" width="45">')[1]
                        to_grade = to_grade.replace('\n', '')
                        to_grade = to_grade.replace(' ', '')
                    else:
                        to_grade = None
                except IndexError:
                    to_grade = None
                # save Relevant Data in dedicated Dictionary
                if class_name not in relevant_data:
                    relevant_data[class_name] = {}
                relevant_data[class_name][ass_name] = {}
                relevant_data[class_name][ass_name]['to_grade'] = to_grade
                if given == 'Yes' or to_grade is not None:
                    relevant_data[class_name][ass_name]['days_passed'] = days_passed
        except Exception as e:
            print(e)

'''
Gets File list from Path
'''
def get_file_list():
    path = os.path.join(BASE_DIR, 'data')
    file_list = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if 'home' not in file:
                file_list.append(os.path.join(root, file))
    return file_list

'''
This is the main function for generating the results . 
the results are generated during run time and the HTML code is being writen 
accordingly.
The Function is heavily commented for further reuse.
'''
def generate_conclusion():
    global relevant_data
    first_iter = 1
    ass_list = []
    str_html = ""
    # Setup HTML
    str_html += HTML_BASE_START
    for key, value in relevant_data.items():
        if first_iter == 1:
            for ass_name in value:
                ass_list.append(ass_name)
            ass_list = sorted(ass_list)
            first_iter = 0
            # Insert Table Headers
            for a_name in ass_list:
                str_html += '''<th scope="col">''' + a_name + '''</th>'''
            # Close Headers
            str_html += '''</tr></thead><tbody>'''
        # Start New Row
        str_html +='''<tr><th scope="row">'''+key+'''</th>'''
        for a_name in ass_list:
            cell_value = ''
            try:
                if value[a_name]['to_grade'] != None:
                    day_p = int(str(value[a_name]['days_passed']))-CHECK_TIME
                    if day_p>0:
                        cell_value = '''<td bgcolor="#ed3300">'''+'late in ' + str(day_p)+" Days"'''</td>'''
                    else:
                        cell_value = '''<td">Not Dued Yet</td>'''
                else:
                    cell_value ='''<td>V</td>'''
            except:
                cell_value = '''<td bgcolor="#ffbb00">???</td>'''
            str_html +=cell_value
        #close Row
        str_html += '''</tr>'''
    #Close html Template
    str_html += HTML_BASE_END
    with open('conc.html','w',encoding="utf8") as output:
        output.write(str_html)
    webbrowser.open_new_tab('conc.html')


if __name__ == "__main__":
    CURRENT_YEAR = int(date.today().year)
    print("***************************************************************")
    print("* Hello, This Program will Generate an html output of the     *")
    print("* HOME_WORK check status in your classes.                     *")
    print("* You will be prompt to enter your username and password      *")
    print("* !! Password will not be saved.                              *")
    print("* Then you will be asked to enter base name of template class *")
    print("* this value is necessary to filter the results.              *")
    print("* -> example: 09-C_Programming-1                              *")
    print("*                                                             *")
    print("*                                                             *")
    print("* This Software was developed By Prkr                         *")
    print("*                                                             *")
    print("***************************************************************")
    cont = input("Press Enter to Continue.")
    USERNAME = input("Enter Your EDU UserName: ")
    PASSWORD = input("Enter Your EDU Password: ")
    TEMPLATE_NAME = input("Enter Base Name Of template Class: ")
    login_to_site()
    print()
    print("***************************************************************")
    print("*                       DONE!                                 *")
    print("***************************************************************")
