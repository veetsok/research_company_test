#!/usr/bin/env python3
"""
Парсер для сайта erzrf.ru с использованием requests-html
Извлекает: название, город, сайт, соцсети
"""

from requests_html import HTMLSession
import pandas as pd
import time
import re
from urllib.parse import urljoin
import asyncio

class ERZRFRequestsHTMLParser:
    def __init__(self):
        self.session = HTMLSession()
        self.base_url = 'https://erzrf.ru'
        self.companies_data = []
        
    def get_company_links_from_page(self, page_num):
        """Извлечение ссылок на компании со страницы топа"""
        url = f"{self.base_url}/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801&page={page_num}"
        print(f"Парсинг страницы {page_num}: {url}")
        
        try:
            r = self.session.get(url)
            
            # Рендерим JavaScript
            print("Рендерим JavaScript...")
            r.html.render(timeout=20, wait=3)
            
            # Ищем ссылки на компании
            company_links = []
            
            # Пробуем разные селекторы
            selectors = [
                'a[href*="/zastroyschiki/brand/"]',
                'a[href*="brand"]'
            ]
            
            for selector in selectors:
                try:
                    elements = r.html.find(selector)
                    if elements:
                        print(f"Найдено {len(elements)} элементов с селектором: {selector}")
                        for element in elements:
                            href = element.attrs.get('href')
                            if href and '/zastroyschiki/brand/' in href:
                                full_url = urljoin(self.base_url, href)
                                company_links.append(full_url)
                        break
                except Exception as e:
                    print(f"Ошибка с селектором {selector}: {e}")
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
            r = self.session.get(company_url)
            
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
            title_selectors = [
                'h1',
                '.org-name',
                '.company-name',
                '.brand-name'
            ]
            
            for selector in title_selectors:
                try:
                    elements = r.html.find(selector)
                    if elements:
                        title_text = elements[0].text.strip()
                        if title_text and len(title_text) < 200:
                            company_data['название'] = title_text
                            break
                except:
                    continue
            
            # Если не нашли в селекторах, пробуем через title страницы
            if not company_data['название']:
                title = r.html.find('title')
                if title:
                    title_text = title[0].text
                    if title_text and ' - ' in title_text:
                        company_data['название'] = title_text.split(' - ')[0].strip()
            
            # Извлечение сайта
            try:
                # Ищем блок с сайтом
                site_elements = r.html.find('#org-site a')
                if site_elements:
                    href = site_elements[0].attrs.get('href')
                    if href:
                        company_data['сайт'] = href
            except:
                pass
            
            # Если не нашли в org-site, ищем другими способами
            if not company_data['сайт']:
                try:
                    # Ищем все ссылки на внешние сайты
                    all_links = r.html.find('a[href]')
                    for link in all_links:
                        href = link.attrs.get('href', '')
                        if (href and 'http' in href and 'erzrf.ru' not in href and 
                            any(domain in href for domain in ['.ru', '.com', '.рф']) and
                            not any(social in href.lower() for social in ['vk.com', 'facebook', 'instagram', 'twitter', 't.me', 'youtube'])):
                            company_data['сайт'] = href
                            break
                except:
                    pass
            
            # Извлечение соцсетей
            social_networks = []
            
            try:
                # Ищем блок с соцсетями
                social_elements = r.html.find('#org-social a')
                for element in social_elements:
                    href = element.attrs.get('href')
                    if href:
                        social_networks.append(href)
            except:
                pass
            
            # Если не нашли в org-social, ищем по всей странице
            if not social_networks:
                social_domains = ['vk.com', 'facebook.com', 'instagram.com', 'twitter.com', 't.me', 'youtube.com', 'ok.ru']
                
                try:
                    all_links = r.html.find('a[href]')
                    for link in all_links:
                        href = link.attrs.get('href', '')
                        if href:
                            for domain in social_domains:
                                if domain in href.lower() and href not in social_networks:
                                    social_networks.append(href)
                                    break
                except:
                    pass
            
            company_data['соцсети'] = '; '.join(social_networks) if social_networks else ''
            
            # Извлечение города
            city_patterns = [
                r'г\.\s*([А-Яа-яё\s\-]+)',
                r'город\s+([А-Яа-яё\s\-]+)',
                r'([А-Яа-яё\s\-]+)\s*область',
                r'([А-Яа-яё\s\-]+)\s*край'
            ]
            
            page_text = r.html.text
            
            for pattern in city_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    city = match.group(1).strip()
                    if (len(city) < 50 and 
                        not any(word in city.lower() for word in ['застройщик', 'компания', 'группа', 'строительство']) and
                        city not in ['Москва', 'Санкт', 'Петербург']):  # Исключаем частичные совпадения
                        company_data['город'] = city
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
            time.sleep(3)  # Пауза между страницами
        
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
            time.sleep(3)
            
            # Промежуточное сохранение каждые 10 компаний
            if i % 10 == 0:
                self.save_to_excel(f'companies_backup_{i}.xlsx')
        
        return self.companies_data
    
    def save_to_excel(self, filename='erzrf_companies_requests_html.xlsx'):
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
    
    def save_to_csv(self, filename='erzrf_companies_requests_html.csv'):
        """Сохранение данных в CSV"""
        if not self.companies_data:
            print("Нет данных для сохранения")
            return
        
        df = pd.DataFrame(self.companies_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Данные сохранены в {filename}")
    
    def close(self):
        """Закрытие сессии"""
        if hasattr(self, 'session'):
            self.session.close()

def main():
    parser = ERZRFRequestsHTMLParser()
    
    print("Запуск парсера ERZRF.ru с requests-html")
    print("Будем парсить топ застройщиков...")
    
    try:
        # Парсим все страницы
        companies = parser.parse_all_pages(max_pages=15)  # 250 компаний ≈ 13 страниц
        
        # Сохраняем результаты
        parser.save_to_excel('erzrf_companies_requests_html.xlsx')
        parser.save_to_csv('erzrf_companies_requests_html.csv')
        
        print(f"\nПарсинг завершен! Обработано {len(companies)} компаний")
        
    except KeyboardInterrupt:
        print("\nПарсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_partial_requests_html.xlsx')
            print("Частичные данные сохранены")
    except Exception as e:
        print(f"Ошибка: {e}")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_error_requests_html.xlsx')
            print("Данные сохранены до ошибки")
    finally:
        parser.close()

if __name__ == "__main__":
    main()