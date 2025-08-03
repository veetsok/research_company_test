#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import time

def test_site_structure():
    """Тестирование структуры сайта erzrf.ru"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    })
    
    # URL из задачи
    url = 'https://erzrf.ru/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801'
    
    print(f"Тестируем URL: {url}")
    
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"Статус ответа: {response.status_code}")
        print(f"Размер страницы: {len(response.text)} символов")
        
        # Ищем различные элементы на странице
        print("\n=== АНАЛИЗ СТРУКТУРЫ СТРАНИЦЫ ===")
        
        # Ищем таблицы
        tables = soup.find_all('table')
        print(f"Найдено таблиц: {len(tables)}")
        
        # Ищем строки таблиц
        rows = soup.find_all('tr')
        print(f"Найдено строк таблиц: {len(rows)}")
        
        # Ищем списки
        lists = soup.find_all(['ul', 'ol'])
        print(f"Найдено списков: {len(lists)}")
        
        # Ищем элементы списков
        list_items = soup.find_all('li')
        print(f"Найдено элементов списков: {len(list_items)}")
        
        # Ищем ссылки
        all_links = soup.find_all('a', href=True)
        print(f"Найдено ссылок: {len(all_links)}")
        
        # Ищем ссылки на застройщиков
        company_links = []
        for link in all_links:
            href = link.get('href', '')
            if '/zastroyshchik/' in href or 'zastroy' in href.lower():
                company_links.append(link)
        
        print(f"Найдено ссылок на застройщиков: {len(company_links)}")
        
        # Показываем первые несколько ссылок на застройщиков
        print("\n=== ПЕРВЫЕ ССЫЛКИ НА ЗАСТРОЙЩИКОВ ===")
        for i, link in enumerate(company_links[:10]):
            name = link.get_text(strip=True)
            href = link.get('href', '')
            print(f"{i+1}. {name} -> {href}")
        
        # Ищем элементы с рейтингом
        print("\n=== ПОИСК РЕЙТИНГОВЫХ ЭЛЕМЕНТОВ ===")
        
        # Ищем элементы с классами, содержащими "rating", "rank", "top"
        rating_elements = soup.find_all(attrs={"class": lambda x: x and any(keyword in str(x).lower() for keyword in ['rating', 'rank', 'top', 'place'])})
        print(f"Найдено элементов с рейтинговыми классами: {len(rating_elements)}")
        
        # Ищем числа в начале текста (возможные места в рейтинге)
        import re
        potential_ranks = []
        for element in soup.find_all(text=True):
            text = element.strip()
            if re.match(r'^\d+\s', text):
                potential_ranks.append(text[:20])
        
        print(f"Найдено потенциальных рейтинговых позиций: {len(set(potential_ranks))}")
        print("Примеры:", list(set(potential_ranks))[:5])
        
        # Сохраняем HTML для анализа
        with open('erzrf_page_structure.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        
        print(f"\nHTML страницы сохранен в 'erzrf_page_structure.html'")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    print("Тестирование структуры сайта erzrf.ru...")
    success = test_site_structure()
    if success:
        print("Тестирование завершено успешно!")
    else:
        print("Тестирование завершилось с ошибкой!")