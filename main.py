import urllib.request
from bs4 import BeautifulSoup
from datetime import date, datetime
import requests
from selenium import webdriver
import selenium
import time
import re
import os
import codecs
from html_bases import HTML_BASE_START,HTML_BASE_END
import webbrowser
import getpass

teacher_ids_list = []
TEMPLATE_NAME = ""
USERNAME = ""
PASSWORD = ""
ASSIGNMENT_BASE = "https://magshimim.edu20.org/teacher_assignments/list/"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MONTHS = ['Jan', "Feb", 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
CURRENT_YEAR = 2019
relevant_data = {}


def login_to_site():
    with requests.Session() as s:
        url = 'https://magshimim.edu20.org/'
        driver = webdriver.Chrome(executable_path=r'C:/Users/Prkr_Xps/Downloads/chromedriver_win32/chromedriver.exe')
        driver.get(url)
        button = driver.find_element_by_class_name('loginHolder')
        button.click()
        time.sleep(1)
        username = driver.find_element_by_id("userid")
        password = driver.find_element_by_id("password")
        username.send_keys(USERNAME)
        password.send_keys(PASSWORD)
        driver.find_element_by_id("submit_button").click()
        time.sleep(1)

        # Download homePage
        content = driver.page_source
        soup = BeautifulSoup(content, 'html.parser')
        with open("data/home.html", 'wb') as out:
            out.write(soup.encode("utf-8"))
        get_teacher_ids()
        get_teacher_assignments(driver)
        get_teacher_data()
        generate_conclusion()


def get_teacher_assignments(driver):
    for id in teacher_ids_list:
        driver.get("https://magshimim.edu20.org/teacher_assignments/list/" + id)
        content = driver.page_source

        soup = BeautifulSoup(content, 'html.parser')
        # relevant = re.search(r'סקר חניכים סמסטר א', str(soup))
        relevant = str(soup.find('h1'))
        if TEMPLATE_NAME in relevant:
            with open("data/" + id + ".html", 'wb') as out:
                out.write(soup.encode("utf-8"))
        time.sleep(1)


def get_teacher_ids():
    with codecs.open('data/home.html', 'r', encoding="utf8") as file:
        home_page = file.read()
        ids = re.findall(r'<a href="/teacher_class/show/\w+', home_page)
        for element in ids:
            teacher_ids_list.append(element.split('show/')[1])


def get_teacher_data():
    data_dict = {}
    files_list = get_file_list()
    for file in files_list:
        with open(file, 'r', encoding="utf8") as input_f:
            raw_data = input_f.read()
            t_id = os.path.basename(file)
            t_id = t_id.split('.')[0]
            get_relevant_data(raw_data, t_id)
    return "Done"


def get_relevant_data(raw_data, t_id):
    global relevant_data
    rel_rows = []
    soup = BeautifulSoup(raw_data, 'html.parser')
    class_name = soup.find("h1")
    class_name = str(class_name).replace('\n', '')
    class_name = class_name.replace('<h1>', '')
    class_name = class_name.replace('</h1>', '')
    class_name = class_name.lstrip()
    class_name = class_name.rstrip()
    rows = soup.find_all("tr")
    for row in rows:
        for month in MONTHS:
            if month in str(row):
                rel_rows.append(str(row))
    for row in rel_rows:
        try:
            to_grade = None
            if 'Essay' in str(row):
                ass_name = row.split('title="Essay:')[1]
                ass_name = ass_name.split('</a>')[0]
                ass_name = ass_name.split('>')[0]
                ass_name = ass_name.replace('"', '')
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
                if '-' in days_passed:  # if days past is negative we need to take the previous year
                    due_day = datetime.strptime(due + ' ' + str(CURRENT_YEAR - 1), '%b %d %Y')
                    today = date.today()
                    days_passed = datetime.today() - due_day
                    days_passed = str(days_passed).split(' ')[0]
                given = row.split('<span class="textOffScreen">')[1]
                given = given.split('</span>')[0]
                try:
                    if '/teacher_freeform_assignment/to_grade/' in str(row):
                        to_grade = row.split('<a href="/teacher_freeform_assignment/to_grade/')[0]
                        to_grade = to_grade.split('<td align="center" width="45">')[1]
                        to_grade = to_grade.replace('\n', '')
                        to_grade = to_grade.replace(' ', '')
                    else:
                        to_grade = None
                except IndexError:
                    to_grade = None
                if class_name not in relevant_data:
                    relevant_data[class_name] = {}
                relevant_data[class_name][ass_name] = {}
                relevant_data[class_name][ass_name]['to_grade'] = to_grade
                if given == 'Yes' or to_grade is not None:
                    relevant_data[class_name][ass_name]['days_passed'] = days_passed
        except Exception as e:
            print(e)


def get_file_list():
    path = os.path.join(BASE_DIR, 'data')
    file_list = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if 'home' not in file:
                file_list.append(os.path.join(root, file))
    return file_list


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
                    cell_value = '''<td bgcolor="#ed3300">'''+'late ' + str(value[a_name]['days_passed'])+'''</td>'''
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
