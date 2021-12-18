import requests
import random
import sqlite3
import time
import os
from lxml import html
from datetime import datetime


# ****************************************************************
# ****************************************************************
def get_requests(url, log_comment="", time_sleep=3):
    """ Отримуємо відповідь сервера """
    res = ""
    for i in range(3):
        time.sleep(random.randint(1, time_sleep))
        res = requests.get(url=url, headers=headers)

        if res.status_code < 400:
            db_log(f"{log_comment}- {res.status_code} {res.url}", color_blue)
            break
        else:
            db_log(f"err {i}- {res.status_code} {res.url}", color_red)
    return res
# ****************************************************************
# ****************************************************************
def html_to_file(html_file=r'D:\blog.html', html_str=''):
    """ отримуємо HTML-код сторінки -html_str- і зберігаємо в локальний файл -html_file- """
    with open(html_file, 'w', encoding="utf-8") as f:
        f.write(html_str)
    return 'file:///' + html_file.replace("\\","/")
# ****************************************************************
# ****************************************************************
def str_find(str_in='', str_start='', str_end='', result_list=False, result_dubl=False, result_filter=''):
    """ Пошук в строці [str_in] тексту між строками [str_start ... str_end]
    result_list=False - пошук однієї підстроки (True - пошук списка підстрок)
    result_filter=''  - в знайденій підстроці повинна бути підстрока [result_filter]
    result_dubl=True  - виключити дублі з списку """

    if type(str_in) != str or type(str_start) != str or type(str_end) != str or type(result_filter) != str or \
       type(result_list) != bool or type(result_dubl) != bool or not str_in or (not str_start and not str_end):
        return "" if not result_list else []

    if not str_start:                                                       # від початку до позиції [str_end]
        pos = str_in.find(str_end)
        return "" if pos == -1 else str_in[:pos]
    elif not str_end:                                                       # від позиції [str_start] до кінця
        pos = str_in.find(str_start)
        return "" if pos == -1 else str_in[pos + len(str_start):]
    else:
        pos = 0
        str_out = ""
        str_out_list = []
        while True:
            pos_start = str_in.find(str_start, pos)
            if pos_start == -1: break
            pos_end = str_in.find(str_end, pos_start + len(str_start))
            if pos_end   == -1: break

            str_out = str_in[pos_start + len(str_start):pos_end]

            if result_filter and str_out.find(result_filter) == -1: str_out = ""    # str_filter повинна бути в строці
            elif result_dubl and str_out in str_out_list: str_out = ""              # дублі   не повинні бути в списку

            if not result_list: break
            if str_out: str_out_list.append(str_out)

            pos = pos_end + len(str_end)
    return str_out if not result_list else str_out_list
# *****************************************************************
# *****************************************************************
def db_create(db_file):
    """ Створюємо таблиці БД SQLITE """
    db_structure = """
    CREATE TABLE blog (
    b_id TEXT PRIMARY KEY,
    b_url TEXT,
    b_date TEXT,
    b_title TEXT,
    b_author TEXT,
    b_content TEXT);

    CREATE TABLE release (
    r_url TEXT PRIMARY KEY,
    r_id_blog TEXT,
    r_date TEXT,
    r_title TEXT,
    r_h1 TEXT,
    r_content TEXT,
    r_peps_list TEXT,
    FOREIGN KEY (r_id_blog) REFERENCES blog(b_id));

    CREATE TABLE files (
    f_url_release TEXT,
    f_Version TEXT,
    f_Operating_System TEXT,
    f_Description TEXT,
    f_MD5_Sum TEXT,
    f_File_Size TEXT,
    f_GPG TEXT);

    CREATE TABLE log_err (
    e_id_blog TEXT ,
    e_url_release TEXT,
    e_status_code TEXT,
    e_comment TEXT);

    CREATE TABLE log (
    log_line TEXT); 
    """
    cur.executescript(db_structure)

    db_log(f"[{str(datetime.now())[:-7]}]   Site scraping protocol [blog.python.org]", color_green)
    db_log(f"[{db_file}]   Create a database sqlite", color_green)
    return True
# *****************************************************************
# *****************************************************************
def db_select(table_fetch="fetchone", table_name="release", table_fields="*", table_where="r_url='url_release'"):
    """ Вибираємо записи з таблиці БД """
    cur.execute(f"SELECT {table_fields} FROM {table_name} WHERE {table_where};")
    if   table_fetch == "fetchone": return cur.fetchone()
    elif table_fetch == "fetchall": return cur.fetchall()
    elif type(table_fetch) == int and table_fetch > 0: return cur.fetchmany(table_fetch)
    return ""
# *****************************************************************
# *****************************************************************
def db_insert(table_name="blog", table_values="?, ?, ?, ?, ?, ?", table_fields= ""):
    """ Записуємо кортеж значень в таблицю БД"""
    try:
        cur.execute(f"INSERT INTO {table_name} VALUES({table_values});", table_fields)
        con.commit()
        return True
    except Exception as err:
        db_log(f"---> Error while writing to the database. [{table_name}] {err}", color_red)
        return False
# *****************************************************************
def text_clear(line_list):
    """ Очистка тексту сторінки - список строк [line_list] ---> повертає строку форматовану /n  """
    line_new = ""
    line_plus = False
    for line in line_list:
        if not line.strip(): continue
        if line[0] in ['\xa0', ' ', '.', ',', ':', '-', ')'] or line_plus:     # приєднати до попередньої строки
            line_new = line_new[:-1] + " "
            line_plus = False
        if line[-1] in ['\xa0', ',', '(']:                           # Наступну строку приєднати
            line_plus = True

        line_new += line.strip() + "\n"
    return line_new[:-1] if line_new else line_new
# *****************************************************************
# *****************************************************************
def db_log(log_line, log_color=""):
    """ Виводить строку -log_line- на екран і зберігає в таблицю БД -log- """
    cur.execute("INSERT INTO log VALUES(?);", (log_line,))
    print(log_line if not log_color else f"{log_color}{log_line}{color_end}")
    con.commit()
    return True
# *****************************************************************
# *****************************************************************
def xpath_find(tttt, name_field, xpath_list):
    """ Пошук в -tttt- в циклі по списку -xpath_list-. :return: str"""
    element = []
    for xpath_str in xpath_list:
        element = tttt.xpath(xpath_str)
        if element: break

    element = "" if not element else text_clear(element) if 'content' in name_field else " ".join([str(_).strip() for _ in element])
    if not element:
        db_log(f"---> [{name_field}] Not found. [{xpath_list}]", color_red)
    elif 'content' in name_field:
        db_log(f"     [{name_field}] text size .... {len(element)} characters")
    else:
        db_log(f"     [{name_field}] {element}")
    return element
# *****************************************************************
# *****************************************************************
def xpath_test(tttt, xpath_list):
    """ Тест ---> Пошук елемента по списку [xpath_list] """
    element = []
    for xpath_str in xpath_list:
        element = tttt.xpath(xpath_str)
        if element:
            return f"[{element}] <--- [{xpath_str}]"
    print("Елемент не знайдено.")
    return False
# *****************************************************************


# *****************************************************************
# ***************************************************************** lambda
list_select = lambda element, element_str: [x for x in element if element_str in x]
list_to_str = lambda element: "" if not element or not isinstance(element, list) \
              else " ".join([str(_).strip() for _ in element])

item_create = lambda: {x: "" for x in ["b_id", "b_url", "b_date", "b_title", "b_author", "b_content", "b_release",
                                       "r_url", "r_id_blog", "r_date", "r_title", "r_h1", "r_content", "r_peps"]}

# ***************************************************************** url
headers = {'Content-Type': 'text/html',
           'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
# *****************************************************************

color_end    = '\033[0m'
color_black  = '\033[30m'
color_red    = '\033[31m'
color_green  = '\033[32m'
color_yellow = '\033[33m'
color_blue   = '\033[34m'
color_purple = '\033[35m'
color_cyan   = '\033[36m'
color_white  = '\033[37m'
# ============================================================== БД SQLITE
db_file = "d:\\python_blogs.db"
db_find = True if os.path.exists(db_file) else False                         # False -db не знайдено -створюємо нову

con = sqlite3.connect(db_file)
cur = con.cursor()

if not db_find: db_create(db_file)
cur.executescript("PRAGMA foreign_keys=on;")                                 # включить поддержку внешних ключей
con.commit()
# *****************************************************************
