#!/usr/bin/env python3
"""
Улучшенный парсер для сайта erzrf.ru
Извлекает: название, город, сайт, соцсети
"""

import requests
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin

class ERZRFImprovedParser:
    def __init__(self):
        # Обычная сессия для получения ссылок
        self.requests_session = requests.Session()
        self.requests_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        })
        
        # HTML сессия для рендеринга JavaScript
        self.html_session = HTMLSession()
        
        self.base_url = 'https://erzrf.ru'
        self.companies_data = []
        
    def get_company_links_from_page(self, page_num):
        """Извлечение ссылок на компании со страницы топа"""
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801&page={page_num}"
        print(f"Парсинг страницы {page_num}: {url}")
        
        try:
            response = self.requests_session.get(url, timeout=10)
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
    
    def extract_company_data(self, company_url):
        """Извлечение данных о компании из её карточки"""
        print(f"Парсинг компании: {company_url}")
        
        try:
            r = self.html_session.get(company_url)
            
            # Рендерим JavaScript
            print("Рендерим JavaScript для компании...")
            r.html.render(timeout=20, wait=5)
            
            company_data = {
                'название': '',
                'город': '',
                'сайт': '',
                'соцсети': '',
                'url_карточки': company_url
            }
            
            # Извлечение названия компании
            # Пробуем разные способы
            title_found = False
            
            # Способ 1: Из заголовка страницы
            try:
                title = r.html.find('title')
                if title:
                    title_text = title[0].text
                    if title_text and ' - ' in title_text:
                        name = title_text.split(' - ')[0].strip()
                        if name and len(name) < 200 and 'ЕРЗ' not in name:
                            company_data['название'] = name
                            title_found = True
            except:
                pass
            
            # Способ 2: Ищем в HTML элементах
            if not title_found:
                title_selectors = ['h1', '.org-name', '.company-name', '.brand-name']
                
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
            
            # Извлечение сайта - улучшенная логика
            site_found = False
            
            # Способ 1: Ищем в специальном блоке org-site
            try:
                site_elements = r.html.find('#org-site')
                if site_elements:
                    site_html = site_elements[0].html
                    # Ищем ссылку в этом блоке
                    site_links = r.html.find('#org-site a')
                    for link in site_links:
                        href = link.attrs.get('href', '')
                        if href and 'http' in href and 'erzrf.ru' not in href:
                            company_data['сайт'] = href
                            site_found = True
                            break
            except:
                pass
            
            # Способ 2: Ищем текст "Сайт" и ссылку рядом
            if not site_found:
                try:
                    page_html = r.html.html
                    # Ищем паттерн с "Сайт" и ссылкой
                    site_pattern = r'Сайт.*?href="([^"]*)"'
                    match = re.search(site_pattern, page_html, re.IGNORECASE | re.DOTALL)
                    if match:
                        href = match.group(1)
                        if href and 'http' in href and 'erzrf.ru' not in href:
                            company_data['сайт'] = href
                            site_found = True
                except:
                    pass
            
            # Способ 3: Ищем среди всех внешних ссылок, исключая соцсети и erzrf
            if not site_found:
                try:
                    all_links = r.html.find('a[href]')
                    excluded_domains = [
                        'erzrf.ru', 'vk.com', 'facebook.com', 'instagram.com', 
                        'twitter.com', 't.me', 'youtube.com', 'ok.ru',
                        'uniteddevelopers.ru'  # Исключаем этот домен
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
            
            # Извлечение соцсетей - улучшенная логика
            social_networks = []
            
            # Способ 1: Ищем в блоке org-social
            try:
                social_elements = r.html.find('#org-social a, app-org-social a')
                for element in social_elements:
                    href = element.attrs.get('href')
                    if href and any(social in href.lower() for social in ['vk.com', 'facebook', 'instagram', 'twitter', 't.me', 'youtube']):
                        if href not in social_networks:
                            social_networks.append(href)
            except:
                pass
            
            # Способ 2: Ищем по всей странице, но исключаем erzrf.ru соцсети
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
                                    'erzrf_ru' not in href and  # Исключаем соцсети erzrf
                                    '+kf4d9SlCRpRiMGQy' not in href):  # Исключаем телеграм erzrf
                                    social_networks.append(href)
                                    break
                except:
                    pass
            
            company_data['соцсети'] = '; '.join(social_networks) if social_networks else ''
            
            # Извлечение города - улучшенная логика
            city_found = False
            page_text = r.html.text
            
            # Ищем в тексте страницы
            city_patterns = [
                r'г\.\s*([А-Яа-яё][А-Яа-яё\s\-]{2,30})',
                r'город\s+([А-Яа-яё][А-Яа-яё\s\-]{2,30})',
                r'([А-Яа-яё][А-Яа-яё\s\-]{2,30})\s*область',
                r'([А-Яа-яё][А-Яа-яё\s\-]{2,30})\s*край',
                r'([А-Яа-яё][А-Яа-яё\s\-]{2,30})\s*республика'
            ]
            
            for pattern in city_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    city = match.strip()
                    # Фильтруем плохие совпадения
                    if (len(city) >= 3 and len(city) <= 30 and 
                        not any(word in city.lower() for word in [
                            'застройщик', 'компания', 'группа', 'строительство', 
                            'инвест', 'девелопмент', 'проект', 'учредитель'
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
            time.sleep(1)  # Пауза между страницами
        
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
                print(f"  Сайт: {company_data['сайт']}")
                print(f"  Город: {company_data['город']}")
            
            # Пауза между запросами
            time.sleep(2)
            
            # Промежуточное сохранение каждые 10 компаний
            if i % 10 == 0:
                self.save_to_excel(f'companies_backup_{i}.xlsx')
        
        return self.companies_data
    
    def save_to_excel(self, filename='erzrf_companies_improved.xlsx'):
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
    
    def save_to_csv(self, filename='erzrf_companies_improved.csv'):
        """Сохранение данных в CSV"""
        if not self.companies_data:
            print("Нет данных для сохранения")
            return
        
        df = pd.DataFrame(self.companies_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Данные сохранены в {filename}")
    
    def close(self):
        """Закрытие сессий"""
        if hasattr(self, 'html_session'):
            self.html_session.close()

def main():
    parser = ERZRFImprovedParser()
    
    print("Запуск улучшенного парсера ERZRF.ru")
    print("Будем парсить топ застройщиков...")
    
    try:
        # Парсим все страницы
        companies = parser.parse_all_pages(max_pages=15)  # 250 компаний ≈ 13 страниц
        
        # Сохраняем результаты
        parser.save_to_excel('erzrf_companies_improved.xlsx')
        parser.save_to_csv('erzrf_companies_improved.csv')
        
        print(f"\nПарсинг завершен! Обработано {len(companies)} компаний")
        
    except KeyboardInterrupt:
        print("\nПарсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_partial_improved.xlsx')
            print("Частичные данные сохранены")
    except Exception as e:
        print(f"Ошибка: {e}")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_error_improved.xlsx')
            print("Данные сохранены до ошибки")
    finally:
        parser.close()

if __name__ == "__main__":
    main()