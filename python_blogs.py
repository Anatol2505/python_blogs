import requests
import random
import sqlite3
import time
import os
import python_blog_modules as MM
from lxml import html
from datetime import datetime

# *****************************************************************
nom_page = 0
nom_blog = 0
url_next = "https://blog.python.org/"
# *****************************************************************


# ***************************************************************** сторінка з списком блогів
while url_next:
    nom_page += 1

    MM.db_log(f"{'-' * 50}", MM.color_blue)
    res = MM.get_requests(url=url_next, log_comment=f"Page - {str(nom_page):4}")
    if res.status_code > 399:                                    # вихід з програми
        MM.db_log(f"{str(nom_page):4} - Job completed, no server response received", MM.color_red)
        url_next = ""
        continue
    tree = html.fromstring(res.text)

    url_next = tree.xpath('//*[@class="blog-pager-older-link"]/@href')       # наступна сторінка
    url_next = url_next[0] if url_next else ""                               # "" - завершення - остання сторінка !!!

    # -------------------------------------------------- сторінка - список блогів
    for blog in tree.xpath('//div[@class="blog-posts hfeed"]/div'):
        nom_blog += 1
        MM.db_log(f"{'-' * 50} Blog - {nom_blog}", MM.color_blue)
        item = MM.item_create()

        item['b_id'] = MM.xpath_find(blog, 'blog- номер  ', ['.//*[@class="post hentry"]/a/@name'])
        #  "5921857161094605303"
        item['b_url'] = MM.xpath_find(blog, 'blog- url    ', ['.//*[@class="post-title entry-title"]/a/@href'])
        #  "https://blog.python.org/2021/12/python-3110a3-is-available.html"
        item['b_date'] = MM.xpath_find(blog, 'blog- date   ', ['.//*[@class="date-header"]/span/text()'])
        #  'Wednesday, December 8, 2021'
        item['b_title'] = MM.xpath_find(blog, 'blog- title  ', ['.//*[@class="post-title entry-title"]//text()'])
        item['b_title'].replace('\n', ' ')
        #  ['\nPython 3.11.0a3 is available\n'] ---> 'Python 3.11.0a3 is available'
        item['b_author'] = MM.xpath_find(blog, 'blog- author ', ['.//*[@class="fn"]/text()'])
        #  'Pablo Galindo'
        item['b_content'] = MM.xpath_find(blog, 'blog- content',
        ['.//*[@class="post-body entry-content"]//text()', './/*[@class="gmail_default"]//text()'])
        # -------------------------------------------------- перевіряємо чи існує блог в таблиці blog БД

        if MM.db_select(table_name="blog", table_fields="*", table_where=f"b_id='{item['b_id']}'"):
            MM.db_log(f"---> Blog found. {item['b_id']} {item['b_url']}", MM.color_cyan)
            continue                                       # блог вже є в БД  ---> читаємо наступний

        if not MM.db_insert(table_name="blog", table_values="?, ?, ?, ?, ?, ?", table_fields=list(item.values())[:6]):
            continue                                       # збій запису в БД ---> читаємо наступний
        # -------------------------------------------------- список url релізів
        item['b_release'] = []
        for xpath_str in ['.//*[@class="post-body entry-content"]//@href',
                          './/*[@class="post-body entry-content"]//u/text()',
                          './/*[@class="post-body entry-content"]/a/@href',
                          './/*[@class="reference external"]//@href',
                          './/*[@class="post-body entry-content"]/p[2]/text()']:

            item['b_release'] += [x for x in blog.xpath(xpath_str) if '/downloads/release/' in x]
        #  ['https://www.python.org/downloads/release/python-3110a3/', ...]
        if not item['b_release']:                          # релізи не знайдено
            MM.db_log(f"---> No releases on blog", MM.color_red)
            continue
        item['b_release'] = list(set(item['b_release']))   # видаляємо дублікати
        # **************************************************


        # ************************************************** релізи
        for item["r_url"] in item['b_release']:
            for x in ["r_date", "r_title", "r_h1", "r_content", "r_peps"]: item[x] = ""

            item["r_url"] = item["r_url"].strip()
            item["r_id_blog"] = item["b_id"]

            if item["r_url"][-1] != "/" and item["r_url"].find("%"):     # некоректний url ---> видалити фрагмент -%20-
                element = item["r_url"]                      # https://www.python.org/downloads/release/python-3100a2/%20
                item["r_url"] = item["r_url"][:item["r_url"].rfind("/")+1]
                MM.db_log(f"---> Incorrect release url. {element} ---> {item['r_url']}", MM.color_red)

            if MM.db_select(table_name="release", table_fields="*", table_where=f"r_url='{item['r_url']}'"):
                MM.db_log(f"---> Release found. Blog- {item['b_id']} Release- {item['r_url']}", MM.color_cyan)
                continue                                   # блог вже є в БД  ---> читаємо наступний

            r_res = MM.get_requests(url=item["r_url"], log_comment="   - Release")
            if res.status_code > 399:
                MM.db_insert(table_name="log_err", table_values="?, ?, ?, ?",
                             table_fields=(item['b_id'], item["r_url"], r_res.status_code, ""))
                continue

            r_tree = html.fromstring(r_res.text)

            item['r_date'] = MM.xpath_find(r_tree, 'date', ['//*[@class="text"]/p[1]/text()'])
            # 'Dec. 8, 2021'
            item['r_title'] = MM.xpath_find(r_tree, 'title', ['//*[@class="text"]/h2/text()',
                                                              '//*[@class="text"]/p[2]/strong/text()',
                                                              '//*[@class="text"]/p[2]/text()',
                                                              '//div[@class="section"]/p[1]/strong/text()',
                                                              '//div[@class="section"]/p[1]/text()'])
            # 'This is an early developer preview of Python 3.11'
            item['r_h1'] = MM.xpath_find(r_tree, 'h1',
            ['//*[@class="text"]/header[1]/h1/text()', '//*[@class="text"]/h1[1]/text()'])
            # 'Python 3.11.0a3'
            # -------------------------------------------------- контент
            item['r_content'] = MM.xpath_find(r_tree, 'content', ['//article[@class="text"]//text()'])
            pos = item['r_content'].find('\nFiles\n')
            if pos != -1:
                item['r_content'] = item['r_content'][:pos]    # видаляємо таблицю
            # -------------------------------------------------- список peps
            item['r_peps'] = str([x for x in r_tree.xpath('//article[@class="text"]//@href') if 'peps/pep' in x])
            # ['https://www.python.org/dev/peps/pep-0657/', ...]
            # --------------------------------------------------
            if not MM.db_insert(table_name="release", table_values="?, ?, ?, ?, ?, ?, ?",
                                table_fields=list(item.values())[7:]):
                continue                                       # збій запису в БД ---> читаємо наступний
            # **************************************************


            # ************************************************** таблиця
            try:
                table = r_tree.xpath('//article[@class="text"]/table/tbody')
                if not table:
                    MM.db_log(f"---> The table is missing in the release", MM.color_red)
                else:
                    table_rows = 0
                    table_head = r_tree.xpath('//article[@class="text"]/table/thead/tr/th/text()')
                    # ['Version', 'Operating System', 'Description', 'MD5 Sum', 'File Size', 'GPG']
                    table = table[0]

                    for tr in range(1, len(table.xpath('//tr'))):     # строки
                        line = []
                        for td in range(1, len(table_head) + 1):      # поля !!! 1,6 - два значення (список)
                            element = MM.list_to_str(table.xpath(f'//tr[{tr}]/td[{td}]/text()')) if td not in [1,6] else \
                                 str([MM.list_to_str(table.xpath(f'//tr[{tr}]/td[{td}]/a/text()')),
                                      MM.list_to_str(table.xpath(f'//tr[{tr}]/td[{td}]/a/@href'))])
                            # ['XZ compressed source tarball', 'https://www.python.org/ftp/python/....']

                            line.append(element if element else "")

                        MM.db_insert(table_name="files", table_values="?, ?, ?, ?, ?, ?, ?", table_fields=[item["r_url"]] + line)
                        table_rows += 1
                    MM.db_log(f"---- Created table. Rows inserted -{table_rows}", MM.color_yellow)
                    MM.con.commit()
            except Exception as err:
                MM.db_log(f"---> Error in the process of forming the table. {err}", MM.color_red)
        # **************************************************
# **************************************************
MM.db_log(f"[{str(datetime.now())[:-7]}]   Site scraping is complete. [blog.python.org]", MM.color_green)
MM.db_log(f"Total pages [ {nom_page} ] blogs [ {nom_blog} ] ", MM.color_green)
# **************************************************
