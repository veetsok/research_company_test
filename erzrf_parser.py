#!/usr/bin/env python3
"""
Парсер для сайта erzrf.ru - извлечение данных о застройщиках
Извлекает: название, город, сайт, соцсети
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse
import json

class ERZRFParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.base_url = 'https://erzrf.ru'
        self.companies_data = []
        
    def get_page(self, url, retries=3):
        """Получение страницы с повторными попытками"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except Exception as e:
                print(f"Ошибка при получении {url} (попытка {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    return None
        return None
    
    def extract_company_links_from_page(self, page_num):
        """Извлечение ссылок на компании со страницы топа"""
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801&page={page_num}"
        print(f"Парсинг страницы {page_num}: {url}")
        
        response = self.get_page(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        company_links = []
        
        # Ищем ссылки на карточки компаний
        # Обычно они в таблице или списке
        links = soup.find_all('a', href=re.compile(r'/zastroyschiki/brand/'))
        
        for link in links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                company_links.append(full_url)
        
        print(f"Найдено {len(company_links)} компаний на странице {page_num}")
        return company_links
    
    def extract_company_data(self, company_url):
        """Извлечение данных о компании из её карточки"""
        print(f"Парсинг компании: {company_url}")
        
        response = self.get_page(company_url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        company_data = {
            'название': '',
            'город': '',
            'сайт': '',
            'соцсети': '',
            'url_карточки': company_url
        }
        
        # Извлечение названия компании
        title_selectors = [
            'h1',
            '.company-name',
            '.org-name',
            '[class*="title"]',
            '[class*="name"]'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                company_data['название'] = title_elem.get_text(strip=True)
                break
        
        # Извлечение города
        # Ищем в различных местах где может быть указан город
        city_patterns = [
            r'г\.\s*([А-Яа-яё\s\-]+)',
            r'город\s+([А-Яа-яё\s\-]+)',
            r'([А-Яа-яё\s\-]+)\s*область',
        ]
        
        text_content = soup.get_text()
        for pattern in city_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                company_data['город'] = match.group(1).strip()
                break
        
        # Извлечение сайта
        site_div = soup.find('div', id='org-site')
        if site_div:
            site_link = site_div.find('a')
            if site_link:
                href = site_link.get('href')
                if href:
                    company_data['сайт'] = href
        
        # Если не нашли в org-site, ищем другими способами
        if not company_data['сайт']:
            # Ищем ссылки которые могут быть сайтами
            site_selectors = [
                'a[href*="http"]:contains("Сайт")',
                'a[href*="http"]:contains("сайт")',
                '.site a',
                '.website a'
            ]
            
            for selector in site_selectors:
                try:
                    site_elem = soup.select_one(selector)
                    if site_elem:
                        href = site_elem.get('href')
                        if href and not 'erzrf.ru' in href:
                            company_data['сайт'] = href
                            break
                except:
                    continue
        
        # Извлечение соцсетей
        social_networks = []
        
        # Ищем блок с соцсетями
        social_div = soup.find('app-org-social') or soup.find(id='org-social')
        if social_div:
            social_links = social_div.find_all('a', href=True)
            for link in social_links:
                href = link.get('href')
                if href and any(social in href.lower() for social in ['vk.com', 'facebook', 'instagram', 'twitter', 'telegram', 'youtube']):
                    social_networks.append(href)
        
        # Если не нашли в специальном блоке, ищем по всей странице
        if not social_networks:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href')
                if href:
                    social_domains = ['vk.com', 'facebook.com', 'instagram.com', 'twitter.com', 't.me', 'youtube.com']
                    for domain in social_domains:
                        if domain in href.lower():
                            social_networks.append(href)
                            break
        
        company_data['соцсети'] = '; '.join(social_networks) if social_networks else ''
        
        # Дополнительная попытка найти город из адреса или контактов
        if not company_data['город']:
            contact_sections = soup.find_all(['div', 'span', 'p'], text=re.compile(r'[Аа]дрес|[Кк]онтакт|[Гг]ород'))
            for section in contact_sections:
                text = section.get_text()
                for pattern in city_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        company_data['город'] = match.group(1).strip()
                        break
                if company_data['город']:
                    break
        
        return company_data
    
    def parse_all_pages(self, max_pages=15):
        """Парсинг всех страниц топа"""
        print("Начинаем парсинг всех страниц...")
        
        all_company_links = []
        
        # Собираем ссылки со всех страниц
        for page_num in range(1, max_pages + 1):
            links = self.extract_company_links_from_page(page_num)
            if not links:
                print(f"Страница {page_num} пуста, завершаем сбор ссылок")
                break
            all_company_links.extend(links)
            time.sleep(1)  # Пауза между запросами
        
        print(f"Всего найдено {len(all_company_links)} компаний")
        
        # Удаляем дубликаты
        all_company_links = list(set(all_company_links))
        print(f"Уникальных компаний: {len(all_company_links)}")
        
        # Парсим данные каждой компании
        for i, company_url in enumerate(all_company_links, 1):
            print(f"\nОбрабатываем компанию {i}/{len(all_company_links)}")
            
            company_data = self.extract_company_data(company_url)
            if company_data:
                self.companies_data.append(company_data)
                print(f"Добавлена: {company_data['название']}")
            
            # Пауза между запросами
            time.sleep(1)
            
            # Промежуточное сохранение каждые 10 компаний
            if i % 10 == 0:
                self.save_to_excel(f'companies_backup_{i}.xlsx')
        
        return self.companies_data
    
    def save_to_excel(self, filename='companies.xlsx'):
        """Сохранение данных в Excel"""
        if not self.companies_data:
            print("Нет данных для сохранения")
            return
        
        df = pd.DataFrame(self.companies_data)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"Данные сохранены в {filename}")
        print(f"Всего компаний: {len(df)}")
        
        # Показываем статистику
        print(f"Компаний с сайтами: {df['сайт'].notna().sum()}")
        print(f"Компаний с соцсетями: {df[df['соцсети'] != ''].shape[0]}")
        print(f"Компаний с городами: {df['город'].notna().sum()}")
    
    def save_to_csv(self, filename='companies.csv'):
        """Сохранение данных в CSV"""
        if not self.companies_data:
            print("Нет данных для сохранения")
            return
        
        df = pd.DataFrame(self.companies_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Данные сохранены в {filename}")

def main():
    parser = ERZRFParser()
    
    print("Запуск парсера ERZRF.ru")
    print("Будем парсить топ застройщиков...")
    
    try:
        # Парсим все страницы
        companies = parser.parse_all_pages(max_pages=15)  # 250 компаний ≈ 13 страниц
        
        # Сохраняем результаты
        parser.save_to_excel('erzrf_companies.xlsx')
        parser.save_to_csv('erzrf_companies.csv')
        
        print(f"\nПарсинг завершен! Обработано {len(companies)} компаний")
        
    except KeyboardInterrupt:
        print("\nПарсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_partial.xlsx')
            print("Частичные данные сохранены")
    except Exception as e:
        print(f"Ошибка: {e}")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_error.xlsx')
            print("Данные сохранены до ошибки")

if __name__ == "__main__":
    main()