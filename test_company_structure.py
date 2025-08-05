#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_company_page():
    """Тестирование структуры страницы компании"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })
    
    # URL компании ПИК из примера
    url = "https://erzrf.ru/zastroyschiki/brand/pik-429726001?region=vse-regiony&regionKey=0&organizationId=429726001"
    
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print("=== АНАЛИЗ СТРУКТУРЫ СТРАНИЦЫ КОМПАНИИ ===")
        
        # Ищем все блоки с классом cmn_row
        cmn_rows = soup.find_all('div', class_='cmn_row')
        print(f"Найдено блоков cmn_row: {len(cmn_rows)}")
        
        for i, row in enumerate(cmn_rows):
            print(f"\n--- Блок {i+1} ---")
            print(f"HTML: {row}")
            
            # Ищем элемент с названием
            name_elem = row.find('div', class_='name')
            if name_elem:
                print(f"Название: {name_elem.get_text(strip=True)}")
            
            # Ищем ссылки
            links = row.find_all('a', href=True)
            for link in links:
                print(f"Ссылка: {link.get('href')} - {link.get_text(strip=True)}")
        
        # Ищем все ссылки на странице
        all_links = soup.find_all('a', href=True)
        print(f"\n=== ВСЕ ССЫЛКИ НА СТРАНИЦЕ ({len(all_links)}) ===")
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if href.startswith('http') and 'erzrf.ru' not in href:
                print(f"Внешняя ссылка: {href} - {text}")
        
        # Сохраняем HTML для анализа
        with open('company_page_structure.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("\nHTML сохранен в company_page_structure.html")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")

if __name__ == "__main__":
    test_company_page()