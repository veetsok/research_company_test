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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('erzrf_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

    def get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Получение страницы с повторными попытками"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1} не удалась для {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Экспоненциальная задержка
                else:
                    logger.error(f"Не удалось получить страницу {url}")
                    return None

    def parse_main_page(self, limit: int = 250) -> List[Dict]:
        """Парсинг основной страницы с топом застройщиков"""
        logger.info("Начинаем парсинг основной страницы...")
        
        # URL для получения топ застройщиков (с параметрами из задачи)
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801"
        
        soup = self.get_page(url)
        if not soup:
            logger.error("Не удалось получить основную страницу")
            return []

        companies = []
        
        # Поиск таблицы с застройщиками
        table_rows = soup.find_all('tr') if soup else []
        
        for i, row in enumerate(table_rows[:limit]):  # Ограничиваем топ-250
            try:
                # Поиск ссылки на застройщика
                company_link = row.find('a')
                if not company_link:
                    continue
                    
                company_name = company_link.get_text(strip=True)
                company_url = urljoin(self.base_url, company_link.get('href', ''))
                
                # Извлечение региона из текста строки
                region_text = row.get_text()
                region = self.extract_region(region_text)
                
                company_data = {
                    'rank': i + 1,
                    'name': company_name,
                    'region': region,
                    'profile_url': company_url,
                    'website': '',
                    'social_networks': ''
                }
                
                companies.append(company_data)
                logger.info(f"Найден застройщик #{i+1}: {company_name}")
                
            except Exception as e:
                logger.error(f"Ошибка при парсинге строки {i}: {e}")
                continue
                
        logger.info(f"Найдено {len(companies)} застройщиков на основной странице")
        return companies

    def extract_region(self, text: str) -> str:
        """Извлечение региона из текста"""
        # Регулярное выражение для поиска региона
        region_patterns = [
            r'г\.([А-Я][а-я\-]+)',  # г.Москва
            r'([А-Я][а-я\-]+ область)',  # Московская область
            r'([А-Я][а-я\-]+ край)',  # Краснодарский край
            r'Республика ([А-Я][а-я\-]+)',  # Республика Татарстан
        ]
        
        for pattern in region_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1) if 'г\.' in pattern else match.group(0)
        
        return "Не указан"

    def parse_company_details(self, company: Dict) -> Dict:
        """Парсинг детальной информации о компании"""
        logger.info(f"Парсинг деталей для {company['name']}")
        
        soup = self.get_page(company['profile_url'])
        if not soup:
            return company
            
        try:
            # Поиск официального сайта
            website_links = soup.find_all('a', href=True)
            for link in website_links:
                href = link.get('href', '')
                if self.is_company_website(href):
                    company['website'] = href
                    break
            
            # Поиск социальных сетей
            social_links = []
            social_patterns = [
                r'vk\.com',
                r'instagram\.com',
                r'facebook\.com',
                r't\.me',
                r'youtube\.com',
                r'ok\.ru'
            ]
            
            for link in website_links:
                href = link.get('href', '')
                for pattern in social_patterns:
                    if re.search(pattern, href, re.IGNORECASE):
                        social_links.append(href)
                        break
            
            company['social_networks'] = '; '.join(list(set(social_links)))
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге деталей для {company['name']}: {e}")
        
        # Задержка между запросами
        time.sleep(1)
        return company

    def is_company_website(self, url: str) -> bool:
        """Проверка, является ли ссылка официальным сайтом компании"""
        if not url or url.startswith('#') or 'erzrf.ru' in url:
            return False
            
        # Исключаем социальные сети и другие сервисы
        excluded_domains = [
            'vk.com', 'instagram.com', 'facebook.com', 't.me',
            'youtube.com', 'ok.ru', 'twitter.com', 'linkedin.com',
            'google.com', 'yandex.ru', 'mail.ru'
        ]
        
        for domain in excluded_domains:
            if domain in url.lower():
                return False
                
        return url.startswith('http')

    def save_to_csv(self, filename: str = 'top_250_zastroyshchiki.csv'):
        """Сохранение данных в CSV файл"""
        if not self.companies_data:
            logger.warning("Нет данных для сохранения")
            return
            
        logger.info(f"Сохранение {len(self.companies_data)} записей в {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['rank', 'name', 'region', 'website', 'social_networks', 'profile_url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for company in self.companies_data:
                writer.writerow({
                    'rank': company['rank'],
                    'name': company['name'],
                    'region': company['region'],
                    'website': company['website'],
                    'social_networks': company['social_networks'],
                    'profile_url': company['profile_url']
                })
        
        logger.info(f"Данные успешно сохранены в {filename}")

    def run(self, limit: int = 250, parse_details: bool = True):
        """Основной метод запуска парсера"""
        logger.info(f"Запуск парсера для топ-{limit} застройщиков")
        
        # Получаем список компаний с основной страницы
        companies = self.parse_main_page(limit)
        
        if not companies:
            logger.error("Не удалось получить список компаний")
            return
        
        self.companies_data = companies
        
        # Парсим детальную информацию для каждой компании
        if parse_details:
            logger.info("Начинаем парсинг детальной информации...")
            for i, company in enumerate(self.companies_data):
                logger.info(f"Обрабатываем {i+1}/{len(self.companies_data)}: {company['name']}")
                self.companies_data[i] = self.parse_company_details(company)
                
                # Прогресс каждые 10 компаний
                if (i + 1) % 10 == 0:
                    logger.info(f"Обработано {i+1} из {len(self.companies_data)} компаний")
        
        # Сохраняем результаты
        self.save_to_csv()
        logger.info("Парсинг завершен!")

def main():
    parser = ERZRFParser()
    
    try:
        # Запускаем парсер для топ-250 компаний
        parser.run(limit=250, parse_details=True)
        
    except KeyboardInterrupt:
        logger.info("Парсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_csv('partial_results.csv')
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        if parser.companies_data:
            parser.save_to_csv('error_results.csv')

if __name__ == "__main__":
    main()