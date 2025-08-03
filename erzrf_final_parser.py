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
        logging.FileHandler('erzrf_final_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ERZRFFinalParser:
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

    def parse_main_page(self, limit: int = 250) -> List[Dict]:
        """Парсинг основной страницы с топом застройщиков"""
        logger.info("Начинаем парсинг основной страницы...")
        
        # URL с параметрами из задачи
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801"
        
        soup = self.get_page(url)
        if not soup:
            logger.error("Не удалось получить основную страницу")
            return []

        companies = []
        
        # Ищем все ссылки на застройщиков
        all_links = soup.find_all('a', href=True)
        
        rank = 1
        for link in all_links:
            if rank > limit:
                break
                
            href = link.get('href', '')
            
            # Проверяем, что это ссылка на профиль застройщика
            if '/zastroyschiki/brand/' in href:
                try:
                    company_name = link.get_text(strip=True)
                    
                    # Пропускаем пустые названия или цифры
                    if not company_name or company_name.isdigit() or len(company_name) < 3:
                        continue
                    
                    # Пропускаем дубликаты
                    if any(comp['name'] == company_name for comp in companies):
                        continue
                    
                    profile_url = urljoin(self.base_url, href)
                    
                    # Извлекаем регион из контекста (родительские элементы)
                    region = self.extract_region_from_context(link)
                    
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
                    logger.error(f"Ошибка при парсинге ссылки: {e}")
                    continue
        
        logger.info(f"Найдено {len(companies)} компаний на основной странице")
        return companies

    def extract_region_from_context(self, link_element) -> str:
        """Извлечение региона из контекста ссылки"""
        try:
            # Ищем в родительских элементах
            parent = link_element.parent
            while parent and parent.name != 'body':
                text = parent.get_text()
                region = self.extract_region_from_text(text)
                if region != "Не указан":
                    return region
                parent = parent.parent
            
            # Ищем в соседних элементах
            siblings = link_element.find_next_siblings()
            for sibling in siblings[:3]:  # Проверяем первые 3 соседних элемента
                if sibling.name:
                    text = sibling.get_text()
                    region = self.extract_region_from_text(text)
                    if region != "Не указан":
                        return region
            
        except Exception as e:
            logger.debug(f"Ошибка при извлечении региона из контекста: {e}")
        
        return "Не указан"

    def extract_region_from_text(self, text: str) -> str:
        """Извлечение региона из текста"""
        if not text:
            return "Не указан"
            
        # Паттерны для различных форматов регионов
        region_patterns = [
            r'г\.([А-Я][\w\-\s]+)',  # г.Москва, г.Санкт-Петербург
            r'([А-Я][\w\-\s]+ область)',  # Московская область
            r'([А-Я][\w\-\s]+ край)',  # Краснодарский край
            r'(Республика [А-Я][\w\-\s]+)',  # Республика Татарстан
            r'([А-Я][\w\-\s]+ автономный округ)',  # ХМАО
            r'([А-Я][\w\-\s]+ Республика)',  # Чувашская Республика
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
        # Ищем ссылки с различными индикаторами сайта
        website_indicators = [
            'сайт', 'официальный', 'www.', 'http', 'site', 'website'
        ]
        
        links = soup.find_all('a', href=True)
        
        # Сначала ищем по тексту ссылки
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            if any(indicator in text for indicator in website_indicators):
                if self.is_valid_website_url(href):
                    return href
        
        # Затем ищем по URL
        for link in links:
            href = link.get('href', '')
            
            if self.is_valid_website_url(href) and not self.is_social_network(href):
                # Дополнительная проверка на корпоративный сайт
                domain = urlparse(href).netloc.lower()
                if any(word in domain for word in ['corp', 'group', 'company', 'строй', 'дом']):
                    return href
        
        return None

    def find_social_networks(self, soup: BeautifulSoup) -> List[str]:
        """Поиск ссылок на социальные сети"""
        social_networks = []
        social_domains = [
            'vk.com', 'vkontakte.ru', 'instagram.com', 'facebook.com', 
            't.me', 'telegram.me', 'youtube.com', 'youtu.be',
            'ok.ru', 'odnoklassniki.ru', 'twitter.com', 'linkedin.com'
        ]
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '').lower()
            
            for domain in social_domains:
                if domain in href and href.startswith('http'):
                    # Проверяем, что это не дубликат
                    if href not in [sn.lower() for sn in social_networks]:
                        social_networks.append(link.get('href', ''))
                    break
        
        return social_networks

    def find_region_in_profile(self, soup: BeautifulSoup) -> Optional[str]:
        """Поиск региона в профиле компании"""
        # Ищем в различных элементах страницы
        text_content = soup.get_text()
        region = self.extract_region_from_text(text_content)
        
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
        if url.endswith(('.pdf', '.doc', '.docx', '.jpg', '.png', '.zip')) or '#' in url:
            return False
        
        # Исключаем явно социальные сети
        if self.is_social_network(url):
            return False
        
        return True

    def is_social_network(self, url: str) -> bool:
        """Проверка, является ли URL социальной сетью"""
        social_domains = [
            'vk.com', 'vkontakte.ru', 'instagram.com', 'facebook.com',
            't.me', 'telegram.me', 'youtube.com', 'youtu.be',
            'ok.ru', 'odnoklassniki.ru', 'twitter.com', 'linkedin.com'
        ]
        
        return any(domain in url.lower() for domain in social_domains)

    def save_to_csv(self, filename: str = 'top_250_zastroyshchiki_final.csv'):
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

    def run(self, limit: int = 250, parse_details: bool = True):
        """Запуск парсера"""
        logger.info(f"Запуск финального парсера для топ-{limit} застройщиков")
        
        try:
            # Получаем список компаний
            companies = self.parse_main_page(limit)
            
            if not companies:
                logger.error("Не удалось получить список компаний")
                return
            
            self.companies_data = companies
            logger.info(f"Получен список из {len(companies)} компаний")
            
            # Сохраняем базовый список
            self.save_to_csv('basic_companies_list.csv')
            
            if parse_details:
                logger.info("Начинаем парсинг детальной информации...")
                
                for i, company in enumerate(self.companies_data):
                    logger.info(f"Обрабатываем {i+1}/{len(self.companies_data)}: {company['name']}")
                    self.companies_data[i] = self.parse_company_profile(company)
                    
                    # Промежуточное сохранение каждые 25 компаний
                    if (i + 1) % 25 == 0:
                        self.save_to_csv(f'partial_results_{i+1}.csv')
                        logger.info(f"Промежуточное сохранение: обработано {i+1} компаний")
            
            # Финальное сохранение
            self.save_to_csv()
            logger.info("Парсинг успешно завершен!")
            
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            if self.companies_data:
                self.save_to_csv('error_backup.csv')

def main():
    parser = ERZRFFinalParser()
    
    try:
        # Запускаем парсер для топ-250 компаний
        parser.run(limit=250, parse_details=True)
        
    except KeyboardInterrupt:
        logger.info("Парсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_csv('interrupted_results.csv')
            
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")

if __name__ == "__main__":
    main()