#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pagination():
    """Тестирование пагинации топа застройщиков"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })
    
    base_url = "https://erzrf.ru/top-zastroyshchikov/rf"
    params = {
        'regionKey': '0',
        'topType': '0', 
        'date': '250801'
    }
    
    page = 1
    total_companies = 0
    
    while True:
        params['page'] = page
        url = f"{base_url}?regionKey={params['regionKey']}&topType={params['topType']}&date={params['date']}&page={page}"
        
        print(f"\n=== Страница {page} ===")
        print(f"URL: {url}")
        
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем все ссылки на застройщиков
            company_links = soup.find_all('a', href=True)
            page_companies = 0
            
            for link in company_links:
                href = link.get('href', '')
                if '/zastroyschiki/brand/' in href:
                    company_name = link.get_text(strip=True)
                    if company_name and not company_name.isdigit() and len(company_name) > 3:
                        page_companies += 1
                        print(f"  {page_companies}. {company_name}")
            
            total_companies += page_companies
            print(f"Найдено компаний на странице: {page_companies}")
            
            # Если на странице нет компаний, значит достигли конца
            if page_companies == 0:
                print("Больше компаний не найдено")
                break
            
            page += 1
            
            # Ограничиваем количество страниц для теста
            if page > 20:
                print("Достигнут лимит страниц для теста")
                break
                
        except Exception as e:
            print(f"Ошибка при загрузке страницы {page}: {e}")
            break
    
    print(f"\n=== ИТОГО ===")
    print(f"Всего страниц: {page - 1}")
    print(f"Всего компаний: {total_companies}")

if __name__ == "__main__":
    test_pagination()