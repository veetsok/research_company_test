#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import csv
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Dict, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_top_companies():
    """Парсинг топ компаний с ограниченным количеством страниц"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })
    
    companies = []
    processed_companies = set()
    
    # Парсим первые 5 страниц
    for page in range(1, 6):
        url = f"https://erzrf.ru/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801&page={page}"
        print(f"Парсинг страницы {page}: {url}")
        
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
                    
                    if not company_name or company_name.isdigit() or len(company_name) < 3:
                        continue
                    
                    if company_name in processed_companies:
                        continue
                    
                    profile_url = urljoin('https://erzrf.ru', href)
                    
                    # Простое извлечение региона
                    region = "Не указан"
                    parent_text = link.parent.get_text() if link.parent else ""
                    if "Москва" in parent_text:
                        region = "Москва"
                    elif "Санкт-Петербург" in parent_text:
                        region = "Санкт-Петербург"
                    elif "Краснодарский край" in parent_text:
                        region = "Краснодарский край"
                    
                    company_data = {
                        'rank': len(companies) + 1,
                        'name': company_name,
                        'region': region,
                        'profile_url': profile_url,
                        'website': '',
                        'social_networks': ''
                    }
                    
                    companies.append(company_data)
                    processed_companies.add(company_name)
                    page_companies += 1
                    
                    print(f"#{len(companies)}: {company_name} ({region})")
            
            print(f"На странице {page} найдено {page_companies} новых компаний")
            
            if page_companies == 0:
                print("Больше новых компаний не найдено")
                break
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Ошибка при загрузке страницы {page}: {e}")
            break
    
    print(f"\nВсего найдено {len(companies)} уникальных компаний")
    
    # Сохраняем базовый список
    save_to_csv(companies, 'test_companies_basic.csv')
    
    # Парсим детальную информацию для первых 10 компаний
    print("\nНачинаем парсинг детальной информации...")
    
    for i, company in enumerate(companies[:10]):
        print(f"Обрабатываем {i+1}/10: {company['name']}")
        
        try:
            response = session.get(company['profile_url'], timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем внешние ссылки
            links = soup.find_all('a', href=True)
            external_links = []
            
            for link in links:
                href = link.get('href', '')
                if href.startswith('http') and 'erzrf.ru' not in href:
                    external_links.append(href)
            
            # Простая логика определения сайта и соцсетей
            website = ''
            social_networks = []
            
            for link in external_links:
                if any(domain in link.lower() for domain in ['vk.com', 'instagram.com', 'facebook.com', 't.me']):
                    social_networks.append(link)
                elif not any(domain in link.lower() for domain in ['yandex.ru', 'google.com', 'metrika.yandex.ru']):
                    website = link
                    break
            
            company['website'] = website if website else 'Не найден'
            company['social_networks'] = '; '.join(social_networks) if social_networks else 'Не найдены'
            
            print(f"  Сайт: {company['website']}")
            print(f"  Соцсети: {company['social_networks']}")
            
        except Exception as e:
            print(f"  Ошибка при парсинге профиля: {e}")
        
        time.sleep(1.5)
    
    # Сохраняем финальный результат
    save_to_csv(companies, 'test_companies_final.csv')
    
    return companies

def save_to_csv(companies, filename):
    """Сохранение данных в CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Место', 'Название', 'Город/Регион', 'Сайт', 'Социальные сети']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for company in companies:
            writer.writerow({
                'Место': company['rank'],
                'Название': company['name'],
                'Город/Регион': company['region'],
                'Сайт': company['website'],
                'Социальные сети': company['social_networks']
            })
    
    print(f"Данные сохранены в {filename}")

if __name__ == "__main__":
    parse_top_companies()