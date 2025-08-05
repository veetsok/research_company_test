#!/usr/bin/env python3
"""
Парсер для сайта erzrf.ru с использованием Selenium
Извлекает: название, город, сайт, соцсети
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re
from urllib.parse import urljoin
import json

class ERZRFSeleniumParser:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        self.base_url = 'https://erzrf.ru'
        self.companies_data = []
        
    def setup_driver(self, headless=True):
        """Настройка Chrome WebDriver"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Устанавливаем драйвер
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        
    def get_company_links_from_page(self, page_num):
        """Извлечение ссылок на компании со страницы топа"""
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801&page={page_num}"
        print(f"Парсинг страницы {page_num}: {url}")
        
        try:
            self.driver.get(url)
            
            # Ждем загрузки контента
            time.sleep(5)
            
            # Ищем ссылки на компании
            company_links = []
            
            # Пробуем разные селекторы
            selectors = [
                'a[href*="/zastroyschiki/brand/"]',
                'a[href*="brand"]',
                '.developer-name a',
                '.company-link',
                'tr a'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"Найдено {len(elements)} элементов с селектором: {selector}")
                        for element in elements:
                            href = element.get_attribute('href')
                            if href and '/zastroyschiki/brand/' in href:
                                company_links.append(href)
                        break
                except Exception as e:
                    continue
            
            # Удаляем дубликаты
            company_links = list(set(company_links))
            print(f"Найдено {len(company_links)} уникальных ссылок на странице {page_num}")
            
            return company_links
            
        except Exception as e:
            print(f"Ошибка при парсинге страницы {page_num}: {e}")
            return []
    
    def extract_company_data(self, company_url):
        """Извлечение данных о компании из её карточки"""
        print(f"Парсинг компании: {company_url}")
        
        try:
            self.driver.get(company_url)
            
            # Ждем загрузки контента
            time.sleep(5)
            
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
                '.org-name',
                '.company-name',
                '.brand-name',
                '[class*="title"]'
            ]
            
            for selector in title_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.text.strip():
                        company_data['название'] = element.text.strip()
                        break
                except:
                    continue
            
            # Если не нашли в селекторах, пробуем через title страницы
            if not company_data['название']:
                title = self.driver.title
                if title and ' - ' in title:
                    company_data['название'] = title.split(' - ')[0].strip()
            
            # Извлечение сайта
            try:
                # Ищем блок с сайтом
                site_element = self.driver.find_element(By.ID, 'org-site')
                site_link = site_element.find_element(By.TAG_NAME, 'a')
                company_data['сайт'] = site_link.get_attribute('href')
            except:
                # Если не нашли в org-site, ищем другими способами
                site_selectors = [
                    'a[href*="http"]:not([href*="erzrf.ru"])',
                    '.site-link',
                    '.website-link'
                ]
                
                for selector in site_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            href = element.get_attribute('href')
                            if href and 'erzrf.ru' not in href and any(domain in href for domain in ['.ru', '.com', '.рф']):
                                company_data['сайт'] = href
                                break
                        if company_data['сайт']:
                            break
                    except:
                        continue
            
            # Извлечение соцсетей
            social_networks = []
            
            try:
                # Ищем блок с соцсетями
                social_element = self.driver.find_element(By.ID, 'org-social')
                social_links = social_element.find_elements(By.TAG_NAME, 'a')
                
                for link in social_links:
                    href = link.get_attribute('href')
                    if href:
                        social_networks.append(href)
                        
            except:
                # Если не нашли в org-social, ищем по всей странице
                social_domains = ['vk.com', 'facebook.com', 'instagram.com', 'twitter.com', 't.me', 'youtube.com', 'ok.ru']
                
                for domain in social_domains:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, f'a[href*="{domain}"]')
                        for element in elements:
                            href = element.get_attribute('href')
                            if href and href not in social_networks:
                                social_networks.append(href)
                    except:
                        continue
            
            company_data['соцсети'] = '; '.join(social_networks) if social_networks else ''
            
            # Извлечение города
            # Ищем в различных местах
            city_patterns = [
                r'г\.\s*([А-Яа-яё\s\-]+)',
                r'город\s+([А-Яа-яё\s\-]+)',
                r'([А-Яа-яё\s\-]+)\s*область',
                r'([А-Яа-яё\s\-]+)\s*край'
            ]
            
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            for pattern in city_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    city = match.group(1).strip()
                    if len(city) < 50 and not any(word in city.lower() for word in ['застройщик', 'компания', 'группа']):
                        company_data['город'] = city
                        break
            
            # Дополнительный поиск города в адресе
            if not company_data['город']:
                try:
                    address_selectors = [
                        '[class*="address"]',
                        '[class*="location"]',
                        '[class*="city"]'
                    ]
                    
                    for selector in address_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                text = element.text
                                for pattern in city_patterns:
                                    match = re.search(pattern, text, re.IGNORECASE)
                                    if match:
                                        company_data['город'] = match.group(1).strip()
                                        break
                                if company_data['город']:
                                    break
                            if company_data['город']:
                                break
                        except:
                            continue
                except:
                    pass
            
            return company_data
            
        except Exception as e:
            print(f"Ошибка при парсинге компании {company_url}: {e}")
            return None
    
    def parse_all_pages(self, max_pages=15):
        """Парсинг всех страниц топа"""
        print("Начинаем парсинг всех страниц...")
        
        all_company_links = []
        
        # Собираем ссылки со всех страниц
        for page_num in range(1, max_pages + 1):
            links = self.get_company_links_from_page(page_num)
            if not links:
                print(f"Страница {page_num} пуста, завершаем сбор ссылок")
                break
            all_company_links.extend(links)
            time.sleep(2)  # Пауза между страницами
        
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
            time.sleep(2)
            
            # Промежуточное сохранение каждые 10 компаний
            if i % 10 == 0:
                self.save_to_excel(f'companies_backup_{i}.xlsx')
        
        return self.companies_data
    
    def save_to_excel(self, filename='erzrf_companies_selenium.xlsx'):
        """Сохранение данных в Excel"""
        if not self.companies_data:
            print("Нет данных для сохранения")
            return
        
        df = pd.DataFrame(self.companies_data)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"Данные сохранены в {filename}")
        print(f"Всего компаний: {len(df)}")
        
        # Показываем статистику
        print(f"Компаний с сайтами: {df[df['сайт'] != ''].shape[0]}")
        print(f"Компаний с соцсетями: {df[df['соцсети'] != ''].shape[0]}")
        print(f"Компаний с городами: {df[df['город'] != ''].shape[0]}")
    
    def save_to_csv(self, filename='erzrf_companies_selenium.csv'):
        """Сохранение данных в CSV"""
        if not self.companies_data:
            print("Нет данных для сохранения")
            return
        
        df = pd.DataFrame(self.companies_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Данные сохранены в {filename}")
    
    def close(self):
        """Закрытие браузера"""
        if hasattr(self, 'driver'):
            self.driver.quit()

def main():
    parser = ERZRFSeleniumParser(headless=True)
    
    print("Запуск парсера ERZRF.ru с Selenium")
    print("Будем парсить топ застройщиков...")
    
    try:
        # Парсим все страницы
        companies = parser.parse_all_pages(max_pages=15)  # 250 компаний ≈ 13 страниц
        
        # Сохраняем результаты
        parser.save_to_excel('erzrf_companies_selenium.xlsx')
        parser.save_to_csv('erzrf_companies_selenium.csv')
        
        print(f"\nПарсинг завершен! Обработано {len(companies)} компаний")
        
    except KeyboardInterrupt:
        print("\nПарсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_partial_selenium.xlsx')
            print("Частичные данные сохранены")
    except Exception as e:
        print(f"Ошибка: {e}")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_error_selenium.xlsx')
            print("Данные сохранены до ошибки")
    finally:
        parser.close()

if __name__ == "__main__":
    main()