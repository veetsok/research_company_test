#!/usr/bin/env python3
"""
Финальный парсер для сайта erzrf.ru - полный парсинг всех компаний
Извлекает: название, город, сайт, соцсети
"""

import requests
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin
import json
from datetime import datetime

class FinalERZRFParser:
    def __init__(self):
        # Обычная сессия для получения ссылок
        self.requests_session = requests.Session()
        self.requests_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # HTML сессия для рендеринга JavaScript
        self.html_session = HTMLSession()
        
        self.base_url = 'https://erzrf.ru'
        self.companies_data = []
        self.failed_urls = []
        
    def get_company_links_from_page(self, page_num):
        """Извлечение ссылок на компании со страницы топа"""
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801&page={page_num}"
        print(f"Парсинг страницы {page_num}: {url}")
        
        try:
            response = self.requests_session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем ссылки на компании
            company_links = []
            links = soup.find_all('a', href=re.compile(r'/zastroyschiki/brand/'))
            
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    company_links.append(full_url)
            
            # Удаляем дубликаты
            company_links = list(set(company_links))
            print(f"Найдено {len(company_links)} уникальных ссылок на странице {page_num}")
            
            return company_links
            
        except Exception as e:
            print(f"Ошибка при парсинге страницы {page_num}: {e}")
            return []
    
    def extract_company_data(self, company_url, attempt=1):
        """Извлечение данных о компании из её карточки"""
        print(f"Парсинг компании (попытка {attempt}): {company_url}")
        
        try:
            r = self.html_session.get(company_url, timeout=30)
            
            # Рендерим JavaScript с увеличенным временем ожидания
            print("Рендерим JavaScript для компании...")
            r.html.render(timeout=30, wait=10, sleep=2)
            
            company_data = {
                'название': '',
                'город': '',
                'сайт': '',
                'соцсети': '',
                'url_карточки': company_url
            }
            
            # Извлечение названия компании
            title_found = False
            
            # Способ 1: Из заголовка страницы
            try:
                title = r.html.find('title')
                if title:
                    title_text = title[0].text
                    if title_text and ' - ' in title_text:
                        name = title_text.split(' - ')[0].strip()
                        if name and len(name) < 200 and 'ЕРЗ' not in name and name != 'ПРОФИ-ИНВЕСТ':
                            company_data['название'] = name
                            title_found = True
                        elif name == 'ПРОФИ-ИНВЕСТ':
                            company_data['название'] = name
                            title_found = True
            except:
                pass
            
            # Способ 2: Ищем в HTML элементах
            if not title_found:
                title_selectors = ['h1', '.org-name', '.company-name', '.brand-name', '[class*="title"]']
                
                for selector in title_selectors:
                    try:
                        elements = r.html.find(selector)
                        if elements:
                            title_text = elements[0].text.strip()
                            if title_text and len(title_text) < 200 and 'ЕРЗ' not in title_text:
                                company_data['название'] = title_text
                                title_found = True
                                break
                    except:
                        continue
            
            # Извлечение сайта
            site_found = False
            
            # Способ 1: Ищем в HTML коде паттерн с сайтом
            try:
                html_content = r.html.html
                
                # Паттерны для поиска сайта
                site_patterns = [
                    r'<div[^>]*id="org-site"[^>]*>.*?<a[^>]*href="([^"]*)"',
                    r'"Сайт".*?href="([^"]*)"',
                    r'Сайт.*?<a[^>]*href="([^"]*)"'
                ]
                
                for pattern in site_patterns:
                    matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                    for match in matches:
                        if (match and 'http' in match and 'erzrf.ru' not in match and 
                            'metrika.yandex' not in match and 'uniteddevelopers' not in match):
                            company_data['сайт'] = match
                            site_found = True
                            break
                    if site_found:
                        break
            except:
                pass
            
            # Способ 2: Ищем среди всех ссылок
            if not site_found:
                try:
                    all_links = r.html.find('a[href]')
                    excluded_domains = [
                        'erzrf.ru', 'vk.com', 'facebook.com', 'instagram.com', 
                        'twitter.com', 't.me', 'youtube.com', 'ok.ru',
                        'uniteddevelopers.ru', 'metrika.yandex.ru', 'google.com'
                    ]
                    
                    for link in all_links:
                        href = link.attrs.get('href', '')
                        if (href and 'http' in href and 
                            not any(domain in href.lower() for domain in excluded_domains) and
                            any(tld in href for tld in ['.ru', '.com', '.рф', '.org', '.net'])):
                            company_data['сайт'] = href
                            site_found = True
                            break
                except:
                    pass
            
            # Извлечение соцсетей
            social_networks = []
            
            try:
                # Ищем в HTML коде паттерн с соцсетями
                html_content = r.html.html
                
                # Паттерны для поиска соцсетей
                social_patterns = [
                    r'<app-org-social[^>]*>.*?href="([^"]*vk\.com[^"]*)"',
                    r'<app-org-social[^>]*>.*?href="([^"]*facebook[^"]*)"',
                    r'<app-org-social[^>]*>.*?href="([^"]*instagram[^"]*)"',
                    r'<div[^>]*id="org-social"[^>]*>.*?href="([^"]*)"'
                ]
                
                for pattern in social_patterns:
                    matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                    for match in matches:
                        if (match and any(social in match.lower() for social in ['vk.com', 'facebook', 'instagram']) and
                            'erzrf_ru' not in match and '+kf4d9SlCRpRiMGQy' not in match):
                            if match not in social_networks:
                                social_networks.append(match)
            except:
                pass
            
            # Если не нашли в специальных блоках, ищем по всей странице
            if not social_networks:
                social_domains = ['vk.com', 'facebook.com', 'instagram.com', 'twitter.com', 't.me', 'youtube.com', 'ok.ru']
                
                try:
                    all_links = r.html.find('a[href]')
                    for link in all_links:
                        href = link.attrs.get('href', '')
                        if href:
                            for domain in social_domains:
                                if (domain in href.lower() and 
                                    href not in social_networks and
                                    'erzrf_ru' not in href and
                                    '+kf4d9SlCRpRiMGQy' not in href):
                                    social_networks.append(href)
                                    break
                except:
                    pass
            
            company_data['соцсети'] = '; '.join(social_networks) if social_networks else ''
            
            # Извлечение города
            city_found = False
            page_text = r.html.text
            
            # Ищем в тексте страницы
            city_patterns = [
                r'г\.\s*([А-Яа-яё][А-Яа-яё\s\-]{2,25})',
                r'город\s+([А-Яа-яё][А-Яа-яё\s\-]{2,25})',
                r'([А-Яа-яё][А-Яа-яё\s\-]{2,25})\s*область',
                r'([А-Яа-яё][А-Яа-яё\s\-]{2,25})\s*край',
                r'([А-Яа-яё][А-Яа-яё\s\-]{2,25})\s*республика'
            ]
            
            for pattern in city_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    city = match.strip()
                    # Фильтруем плохие совпадения
                    if (len(city) >= 3 and len(city) <= 25 and 
                        not any(word in city.lower() for word in [
                            'застройщик', 'компания', 'группа', 'строительство', 
                            'инвест', 'девелопмент', 'проект', 'учредитель',
                            'алтайский', 'амурская', 'архангельская'
                        ]) and
                        city.lower() not in ['москва', 'санкт', 'петербург', 'российская']):
                        company_data['город'] = city
                        city_found = True
                        break
                if city_found:
                    break
            
            return company_data
            
        except Exception as e:
            print(f"Ошибка при парсинге компании {company_url}: {e}")
            # Повторная попытка
            if attempt < 2:
                time.sleep(5)
                return self.extract_company_data(company_url, attempt + 1)
            else:
                self.failed_urls.append(company_url)
                return None
    
    def parse_all_pages(self, max_pages=15):
        """Парсинг всех страниц топа"""
        print("Начинаем парсинг всех страниц...")
        print(f"Время начала: {datetime.now()}")
        
        all_company_links = []
        
        # Собираем ссылки со всех страниц
        for page_num in range(1, max_pages + 1):
            links = self.get_company_links_from_page(page_num)
            if not links:
                print(f"Страница {page_num} пуста, завершаем сбор ссылок")
                break
            all_company_links.extend(links)
            time.sleep(1)  # Пауза между страницами
        
        print(f"Всего найдено {len(all_company_links)} компаний")
        
        # Удаляем дубликаты
        all_company_links = list(set(all_company_links))
        print(f"Уникальных компаний: {len(all_company_links)}")
        
        # Парсим данные каждой компании
        for i, company_url in enumerate(all_company_links, 1):
            print(f"\n{'='*60}")
            print(f"Обрабатываем компанию {i}/{len(all_company_links)}")
            print(f"Время: {datetime.now()}")
            
            company_data = self.extract_company_data(company_url)
            if company_data:
                self.companies_data.append(company_data)
                print(f"✓ Добавлена: {company_data['название']}")
                if company_data['сайт']:
                    print(f"  Сайт: {company_data['сайт']}")
                if company_data['город']:
                    print(f"  Город: {company_data['город']}")
                if company_data['соцсети']:
                    print(f"  Соцсети: {company_data['соцсети'][:100]}...")
            else:
                print(f"✗ Не удалось извлечь данные")
            
            # Пауза между запросами
            time.sleep(3)
            
            # Промежуточное сохранение каждые 20 компаний
            if i % 20 == 0:
                self.save_to_excel(f'companies_backup_{i}.xlsx')
                print(f"Промежуточное сохранение: {len(self.companies_data)} компаний")
        
        return self.companies_data
    
    def save_to_excel(self, filename='erzrf_companies_final.xlsx'):
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
        
        if self.failed_urls:
            print(f"Не удалось обработать: {len(self.failed_urls)} компаний")
    
    def save_to_csv(self, filename='erzrf_companies_final.csv'):
        """Сохранение данных в CSV"""
        if not self.companies_data:
            print("Нет данных для сохранения")
            return
        
        df = pd.DataFrame(self.companies_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Данные сохранены в {filename}")
    
    def save_failed_urls(self, filename='failed_urls.txt'):
        """Сохранение списка неудачных URL"""
        if self.failed_urls:
            with open(filename, 'w', encoding='utf-8') as f:
                for url in self.failed_urls:
                    f.write(url + '\n')
            print(f"Список неудачных URL сохранен в {filename}")
    
    def close(self):
        """Закрытие сессий"""
        if hasattr(self, 'html_session'):
            self.html_session.close()

def main():
    parser = FinalERZRFParser()
    
    print("🚀 ЗАПУСК ФИНАЛЬНОГО ПАРСЕРА ERZRF.RU")
    print("Парсим ТОП-250 застройщиков России")
    print("="*60)
    
    try:
        # Парсим все страницы
        companies = parser.parse_all_pages(max_pages=15)  # 250 компаний ≈ 13 страниц
        
        # Сохраняем результаты
        parser.save_to_excel('erzrf_companies_final.xlsx')
        parser.save_to_csv('erzrf_companies_final.csv')
        parser.save_failed_urls('failed_urls.txt')
        
        print(f"\n🎉 ПАРСИНГ ЗАВЕРШЕН!")
        print(f"Время завершения: {datetime.now()}")
        print(f"Обработано компаний: {len(companies)}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Парсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_partial_final.xlsx')
            parser.save_to_csv('erzrf_companies_partial_final.csv')
            parser.save_failed_urls('failed_urls_partial.txt')
            print("Частичные данные сохранены")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_error_final.xlsx')
            parser.save_to_csv('erzrf_companies_error_final.csv')
            parser.save_failed_urls('failed_urls_error.txt')
            print("Данные сохранены до ошибки")
    finally:
        parser.close()

if __name__ == "__main__":
    main()