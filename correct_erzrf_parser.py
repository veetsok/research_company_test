#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import csv
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
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
        logging.FileHandler('correct_erzrf_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CorrectERZRFParser:
    def __init__(self):
        self.setup_selenium()
        self.base_url = 'https://erzrf.ru'
        self.companies_data = []

    def setup_selenium(self):
        """Настройка Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            # Используем системный chromium
            chrome_options.binary_location = '/usr/bin/chromium-browser'
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("Selenium WebDriver успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации WebDriver: {e}")
            raise

    def get_companies_from_page(self, page_num: int) -> list:
        """Получение списка компаний со страницы"""
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801&page={page_num}"
        logger.info(f"Парсим страницу {page_num}: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(3)  # Ждем загрузки контента
            
            # Ищем все ссылки на компании
            company_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/zastroyschiki/brand/')]")
            
            companies = []
            seen_names = set()
            
            for link in company_links:
                try:
                    company_name = link.text.strip()
                    href = link.get_attribute('href')
                    
                    # Фильтруем валидные названия компаний
                    if (company_name and 
                        len(company_name) > 2 and 
                        not company_name.isdigit() and 
                        company_name not in seen_names and
                        not any(skip in company_name.lower() for skip in ['скачать', 'excel', 'топ-', 'весь список'])):
                        
                        companies.append({
                            'name': company_name,
                            'profile_url': href,
                            'rank': len(companies) + 1 + (page_num - 1) * 20
                        })
                        seen_names.add(company_name)
                        
                        if len(companies) >= 20:  # Максимум 20 компаний на странице
                            break
                            
                except Exception as e:
                    logger.debug(f"Ошибка при обработке ссылки: {e}")
                    continue
            
            logger.info(f"Найдено {len(companies)} компаний на странице {page_num}")
            return companies
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы {page_num}: {e}")
            return []

    def parse_company_details(self, company: dict) -> dict:
        """Парсинг детальной информации о компании"""
        logger.info(f"Парсим детали компании: {company['name']}")
        
        try:
            self.driver.get(company['profile_url'])
            time.sleep(3)  # Ждем загрузки Angular контента
            
            # Инициализируем данные
            company['region'] = 'Не указан'
            company['website'] = 'Не найден'
            company['social_networks'] = 'Не найдены'
            
            # Ищем регион в тексте страницы
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                region = self.extract_region_from_text(page_text)
                if region != "Не указан":
                    company['region'] = region
            except:
                pass
            
            # Ищем блок с сайтом по ID
            try:
                site_element = self.wait.until(EC.presence_of_element_located((By.ID, "org-site")))
                site_link = site_element.find_element(By.TAG_NAME, "a")
                website = site_link.get_attribute('href')
                if website and website.startswith('http'):
                    company['website'] = website
                    logger.info(f"Найден сайт: {website}")
            except TimeoutException:
                logger.debug(f"Блок org-site не найден для {company['name']}")
            except Exception as e:
                logger.debug(f"Ошибка при поиске сайта: {e}")
            
            # Ищем блок с соцсетями
            try:
                social_element = self.wait.until(EC.presence_of_element_located((By.ID, "org-social")))
                social_links = social_element.find_elements(By.TAG_NAME, "a")
                
                social_networks = []
                for link in social_links:
                    href = link.get_attribute('href')
                    if href and any(social in href.lower() for social in ['vk.com', 'instagram', 'facebook', 't.me', 'youtube', 'ok.ru']):
                        social_networks.append(href)
                
                if social_networks:
                    company['social_networks'] = '; '.join(social_networks)
                    logger.info(f"Найдены соцсети: {len(social_networks)} шт.")
                    
            except TimeoutException:
                logger.debug(f"Блок org-social не найден для {company['name']}")
            except Exception as e:
                logger.debug(f"Ошибка при поиске соцсетей: {e}")
            
            # Если не нашли через ID, пробуем альтернативные способы
            if company['website'] == 'Не найден':
                try:
                    # Ищем любые внешние ссылки
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        href = link.get_attribute('href')
                        if (href and 
                            href.startswith('http') and 
                            'erzrf.ru' not in href and
                            not any(social in href.lower() for social in ['vk.com', 'instagram', 'facebook', 't.me', 'youtube', 'ok.ru'])):
                            company['website'] = href
                            logger.info(f"Найден альтернативный сайт: {href}")
                            break
                except Exception as e:
                    logger.debug(f"Ошибка при альтернативном поиске сайта: {e}")
            
            time.sleep(2)  # Пауза между запросами
            return company
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге деталей для {company['name']}: {e}")
            return company

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
                region = match.group(1) if 'г\\.' in pattern else match.group(0)
                return region.strip()
        
        return "Не указан"

    def save_to_csv(self, filename: str = 'top_250_zastroyshchiki_correct.csv'):
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
                    'Сайт': company['website'],
                    'Социальные сети': company['social_networks']
                })
        
        logger.info(f"Данные сохранены в {filename}")

    def run(self, max_pages: int = 13, parse_details: bool = True):
        """Запуск парсера"""
        logger.info(f"Запуск правильного парсера для {max_pages * 20} компаний")
        
        try:
            all_companies = []
            
            # Парсим все страницы
            for page in range(1, max_pages + 1):
                companies = self.get_companies_from_page(page)
                
                if not companies:
                    logger.warning(f"Страница {page} пустая, завершаем парсинг")
                    break
                    
                all_companies.extend(companies)
                
                # Промежуточное сохранение каждые 5 страниц
                if page % 5 == 0:
                    logger.info(f"Промежуточное сохранение после {page} страниц")
                    temp_data = self.companies_data + all_companies
                    self.companies_data = temp_data
                    self.save_to_csv(f'partial_companies_page_{page}.csv')
                    self.companies_data = []
                
                time.sleep(1)  # Пауза между страницами
            
            self.companies_data = all_companies
            logger.info(f"Собрано {len(self.companies_data)} компаний со всех страниц")
            
            # Сохраняем базовый список
            self.save_to_csv('companies_basic_list.csv')
            
            if parse_details:
                logger.info("Начинаем парсинг детальной информации...")
                
                for i, company in enumerate(self.companies_data):
                    logger.info(f"Обрабатываем {i+1}/{len(self.companies_data)}: {company['name']}")
                    self.companies_data[i] = self.parse_company_details(company)
                    
                    # Промежуточное сохранение каждые 10 компаний
                    if (i + 1) % 10 == 0:
                        self.save_to_csv(f'detailed_partial_{i+1}.csv')
                        logger.info(f"Промежуточное сохранение: обработано {i+1} компаний")
            
            # Финальное сохранение
            self.save_to_csv()
            logger.info("Парсинг успешно завершен!")
            
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            if self.companies_data:
                self.save_to_csv('error_backup.csv')
        
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()
                logger.info("WebDriver закрыт")

def main():
    parser = CorrectERZRFParser()
    
    try:
        # Парсим первые 3 страницы для тестирования (60 компаний)
        parser.run(max_pages=3, parse_details=True)
        
    except KeyboardInterrupt:
        logger.info("Парсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_csv('interrupted_results.csv')
            
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
    
    finally:
        if hasattr(parser, 'driver'):
            parser.driver.quit()

if __name__ == "__main__":
    main()