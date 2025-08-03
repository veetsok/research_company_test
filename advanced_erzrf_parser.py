#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import csv
import time
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('erzrf_advanced_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdvancedERZRFParser:
    def __init__(self, use_selenium: bool = False):
        self.use_selenium = use_selenium
        self.base_url = 'https://erzrf.ru'
        self.companies_data = []
        
        if use_selenium:
            self.setup_selenium()
        else:
            self.setup_requests()

    def setup_requests(self):
        """Настройка requests сессии"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def setup_selenium(self):
        """Настройка Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
        except Exception as e:
            logger.error(f"Ошибка инициализации WebDriver: {e}")
            self.use_selenium = False
            self.setup_requests()

    def get_page_requests(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Получение страницы через requests"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1} не удалась для {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Не удалось получить страницу {url}")
                    return None

    def get_page_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Получение страницы через Selenium"""
        try:
            self.driver.get(url)
            time.sleep(3)  # Ждем загрузки динамического контента
            html = self.driver.page_source
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.error(f"Ошибка Selenium для {url}: {e}")
            return None

    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Универсальный метод получения страницы"""
        if self.use_selenium:
            return self.get_page_selenium(url)
        else:
            return self.get_page_requests(url)

    def parse_companies_list(self, limit: int = 250) -> List[Dict]:
        """Парсинг списка компаний с основной страницы"""
        logger.info("Начинаем парсинг списка компаний...")
        
        # Формируем URL с нужными параметрами
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801"
        
        soup = self.get_page(url)
        if not soup:
            logger.error("Не удалось получить основную страницу")
            return []

        companies = []
        
        # Ищем таблицу с рейтингом
        # Сайт использует структуру с <li> элементами или таблицей
        company_rows = soup.find_all(['tr', 'li']) 
        
        logger.info(f"Найдено {len(company_rows)} потенциальных строк")
        
        rank = 1
        for row in company_rows:
            if rank > limit:
                break
                
            try:
                # Ищем ссылку на профиль застройщика
                company_link = row.find('a', href=lambda x: x and '/zastroyshchik/' in x)
                if not company_link:
                    continue
                
                company_name = company_link.get_text(strip=True)
                if not company_name or len(company_name) < 3:
                    continue
                
                profile_url = urljoin(self.base_url, company_link.get('href', ''))
                
                # Извлекаем регион из текста строки
                row_text = row.get_text()
                region = self.extract_region_from_text(row_text)
                
                company_data = {
                    'rank': rank,
                    'name': company_name,
                    'region': region,
                    'profile_url': profile_url,
                    'website': '',
                    'social_networks': ''
                }
                
                companies.append(company_data)
                logger.info(f"#{rank}: {company_name} ({region})")
                rank += 1
                
            except Exception as e:
                logger.error(f"Ошибка при парсинге строки: {e}")
                continue
        
        logger.info(f"Найдено {len(companies)} компаний")
        return companies

    def extract_region_from_text(self, text: str) -> str:
        """Извлечение региона из текста"""
        # Паттерны для различных форматов регионов
        region_patterns = [
            r'г\.([А-Я][а-я\-\s]+)',  # г.Москва, г.Санкт-Петербург
            r'([А-Я][а-я\-\s]+ область)',  # Московская область
            r'([А-Я][а-я\-\s]+ край)',  # Краснодарский край
            r'(Республика [А-Я][а-я\-\s]+)',  # Республика Татарстан
            r'([А-Я][а-я\-\s]+ автономный округ)',  # ХМАО
            r'([А-Я][а-я\-\s]+ Республика)',  # Чувашская Республика
        ]
        
        for pattern in region_patterns:
            match = re.search(pattern, text)
            if match:
                region = match.group(1) if 'г\.' in pattern else match.group(0)
                return region.strip()
        
        return "Не указан"

    def parse_company_profile(self, company: Dict) -> Dict:
        """Парсинг профиля компании для получения сайта и соцсетей"""
        logger.info(f"Парсинг профиля: {company['name']}")
        
        soup = self.get_page(company['profile_url'])
        if not soup:
            logger.warning(f"Не удалось загрузить профиль {company['name']}")
            return company
        
        try:
            # Поиск официального сайта
            website = self.find_company_website(soup)
            if website:
                company['website'] = website
            
            # Поиск социальных сетей
            social_networks = self.find_social_networks(soup)
            if social_networks:
                company['social_networks'] = '; '.join(social_networks)
            
            # Уточнение региона, если не найден ранее
            if company['region'] == "Не указан":
                region = self.find_region_in_profile(soup)
                if region:
                    company['region'] = region
                    
        except Exception as e:
            logger.error(f"Ошибка при парсинге профиля {company['name']}: {e}")
        
        # Задержка между запросами
        time.sleep(1.5)
        return company

    def find_company_website(self, soup: BeautifulSoup) -> Optional[str]:
        """Поиск официального сайта компании"""
        # Ищем ссылки с текстом "сайт", "официальный сайт" и т.д.
        website_indicators = ['сайт', 'официальный', 'www.', 'http']
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Проверяем по тексту ссылки
            if any(indicator in text for indicator in website_indicators):
                if self.is_valid_website_url(href):
                    return href
            
            # Проверяем по URL
            if self.is_valid_website_url(href) and not self.is_social_network(href):
                return href
        
        return None

    def find_social_networks(self, soup: BeautifulSoup) -> List[str]:
        """Поиск ссылок на социальные сети"""
        social_networks = []
        social_domains = [
            'vk.com', 'instagram.com', 'facebook.com', 't.me',
            'youtube.com', 'ok.ru', 'twitter.com', 'linkedin.com'
        ]
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            
            for domain in social_domains:
                if domain in href.lower() and href not in social_networks:
                    social_networks.append(href)
                    break
        
        return social_networks

    def find_region_in_profile(self, soup: BeautifulSoup) -> Optional[str]:
        """Поиск региона в профиле компании"""
        # Ищем в различных элементах страницы
        region_selectors = [
            '.region', '.location', '.address', '[class*="region"]',
            '[class*="location"]', '[class*="address"]'
        ]
        
        for selector in region_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                region = self.extract_region_from_text(text)
                if region != "Не указан":
                    return region
        
        return None

    def is_valid_website_url(self, url: str) -> bool:
        """Проверка валидности URL сайта"""
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        # Исключаем внутренние ссылки сайта
        if 'erzrf.ru' in url:
            return False
        
        # Исключаем файлы и якоря
        if url.endswith(('.pdf', '.doc', '.docx', '.jpg', '.png')) or '#' in url:
            return False
        
        return True

    def is_social_network(self, url: str) -> bool:
        """Проверка, является ли URL социальной сетью"""
        social_domains = [
            'vk.com', 'instagram.com', 'facebook.com', 't.me',
            'youtube.com', 'ok.ru', 'twitter.com', 'linkedin.com'
        ]
        
        return any(domain in url.lower() for domain in social_domains)

    def save_to_csv(self, filename: str = 'top_250_zastroyshchiki_advanced.csv'):
        """Сохранение данных в CSV"""
        if not self.companies_data:
            logger.warning("Нет данных для сохранения")
            return
        
        logger.info(f"Сохранение {len(self.companies_data)} записей в {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Место', 'Название', 'Город/Регион', 'Сайт', 'Социальные сети']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for company in self.companies_data:
                writer.writerow({
                    'Место': company['rank'],
                    'Название': company['name'],
                    'Город/Регион': company['region'],
                    'Сайт': company['website'] if company['website'] else 'Не найден',
                    'Социальные сети': company['social_networks'] if company['social_networks'] else 'Не найдены'
                })
        
        logger.info(f"Данные сохранены в {filename}")

    def run(self, limit: int = 250):
        """Запуск парсера"""
        logger.info(f"Запуск расширенного парсера для топ-{limit} застройщиков")
        
        try:
            # Получаем список компаний
            companies = self.parse_companies_list(limit)
            
            if not companies:
                logger.error("Не удалось получить список компаний")
                return
            
            self.companies_data = companies
            logger.info(f"Получен список из {len(companies)} компаний")
            
            # Парсим детальную информацию
            logger.info("Начинаем парсинг детальной информации...")
            
            for i, company in enumerate(self.companies_data):
                logger.info(f"Обрабатываем {i+1}/{len(self.companies_data)}: {company['name']}")
                self.companies_data[i] = self.parse_company_profile(company)
                
                # Промежуточное сохранение каждые 50 компаний
                if (i + 1) % 50 == 0:
                    self.save_to_csv(f'partial_results_{i+1}.csv')
                    logger.info(f"Промежуточное сохранение: обработано {i+1} компаний")
            
            # Финальное сохранение
            self.save_to_csv()
            logger.info("Парсинг успешно завершен!")
            
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            if self.companies_data:
                self.save_to_csv('error_backup.csv')
        
        finally:
            if self.use_selenium and hasattr(self, 'driver'):
                self.driver.quit()

def main():
    # Можно выбрать использовать Selenium или нет
    use_selenium = False  # Измените на True, если нужен Selenium
    
    parser = AdvancedERZRFParser(use_selenium=use_selenium)
    
    try:
        parser.run(limit=250)
    except KeyboardInterrupt:
        logger.info("Парсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_csv('interrupted_results.csv')
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")

if __name__ == "__main__":
    main()