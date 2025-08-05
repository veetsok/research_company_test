#!/usr/bin/env python3
"""
Скрипт для отладки и изучения структуры HTML страниц
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_main_page():
    """Отладка главной страницы топа"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })
    
    url = "https://erzrf.ru/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801&page=1"
    print(f"Отладка страницы: {url}")
    
    response = session.get(url)
    print(f"Статус ответа: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Сохраняем HTML для анализа
    with open('main_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print("HTML сохранен в main_page.html")
    
    # Ищем различные селекторы для ссылок на компании
    print("\n=== ПОИСК ССЫЛОК НА КОМПАНИИ ===")
    
    # Вариант 1: ссылки с brand в href
    brand_links = soup.find_all('a', href=re.compile(r'/zastroyschiki/brand/'))
    print(f"Ссылки с /zastroyschiki/brand/: {len(brand_links)}")
    for i, link in enumerate(brand_links[:3]):
        print(f"  {i+1}. {link.get('href')} - {link.get_text(strip=True)[:50]}")
    
    # Вариант 2: все ссылки
    all_links = soup.find_all('a', href=True)
    print(f"\nВсего ссылок: {len(all_links)}")
    
    # Вариант 3: поиск таблиц
    tables = soup.find_all('table')
    print(f"\nТаблиц найдено: {len(tables)}")
    
    # Вариант 4: поиск div с классами
    divs_with_class = soup.find_all('div', class_=True)
    print(f"Div с классами: {len(divs_with_class)}")
    
    # Показываем структуру body
    body = soup.find('body')
    if body:
        print(f"\nСтруктура body (первые 1000 символов):")
        print(body.get_text()[:1000])

def debug_company_page():
    """Отладка страницы конкретной компании"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })
    
    url = "https://erzrf.ru/zastroyschiki/brand/profi-invest-3732427001?region=vse-regiony&regionKey=0&organizationId=3732427001&costType=1"
    print(f"\nОтладка страницы компании: {url}")
    
    response = session.get(url)
    print(f"Статус ответа: {response.status_code}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Сохраняем HTML для анализа
    with open('company_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print("HTML сохранен в company_page.html")
    
    # Ищем блок с сайтом
    print("\n=== ПОИСК САЙТА ===")
    site_div = soup.find('div', id='org-site')
    if site_div:
        print("Найден div#org-site:")
        print(site_div.prettify())
    else:
        print("div#org-site не найден")
    
    # Ищем блок с соцсетями
    print("\n=== ПОИСК СОЦСЕТЕЙ ===")
    social_div = soup.find('app-org-social') or soup.find(id='org-social')
    if social_div:
        print("Найден блок с соцсетями:")
        print(social_div.prettify())
    else:
        print("Блок с соцсетями не найден")
    
    # Ищем заголовок компании
    print("\n=== ПОИСК НАЗВАНИЯ ===")
    h1 = soup.find('h1')
    if h1:
        print(f"H1: {h1.get_text(strip=True)}")
    
    # Показываем весь текст страницы
    print(f"\nВесь текст страницы (первые 2000 символов):")
    print(soup.get_text()[:2000])

if __name__ == "__main__":
    print("=== ОТЛАДКА ПАРСЕРА ===")
    debug_main_page()
    debug_company_page()