import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs

def get_social_media_links(soup, company_url):
    """Извлекает ссылки на социальные сети с сайта компании"""
    social_media = []
    
    # Ищем ссылки на популярные соцсети
    social_patterns = {
        'vk.com': 'VK',
        'vk.ru': 'VK',
        'instagram.com': 'Instagram',
        'facebook.com': 'Facebook',
        'twitter.com': 'Twitter',
        't.me': 'Telegram',
        'youtube.com': 'YouTube',
        'ok.ru': 'Одноклассники'
    }
    
    # Ищем ссылки в тексте страницы
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()
        for pattern, platform in social_patterns.items():
            if pattern in href:
                social_media.append(f"{platform}: {link['href']}")
    
    return '; '.join(social_media) if social_media else ''

def get_company_website(company_url):
    """Пытается найти официальный сайт компании на странице компании"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(company_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем ссылки на официальные сайты
            website_patterns = [
                'официальный сайт',
                'сайт компании',
                'www.',
                'http://',
                'https://'
            ]
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True).lower()
                
                # Проверяем, что это внешняя ссылка
                if any(pattern in text for pattern in website_patterns) or href.startswith('http'):
                    if not href.startswith('https://erzrf.ru') and not href.startswith('http://erzrf.ru'):
                        return href
            
    except:
        pass
    
    return ""

def parse_companies_from_page(soup, headers):
    """Парсит данные о компаниях с одной страницы"""
    data = []
    
    # Ищем все элементы с классом developer (это строки с данными компаний)
    developer_items = soup.find_all('li', class_='developer')
    
    for i, item in enumerate(developer_items):
        try:
            # Извлекаем название компании и ссылку
            name_link = item.find('a', href=True)
            if name_link:
                name = name_link.get_text(strip=True)
                company_url = name_link.get('href')
                if company_url and not company_url.startswith('http'):
                    company_url = urljoin('https://erzrf.ru', company_url)
            else:
                name = "Не указано"
                company_url = ""
            
            # Извлекаем город/регион
            city_span = item.find('span', class_='developer-td-3')
            if city_span:
                # Убираем название компании из текста, оставляем только город
                city_text = city_span.get_text(strip=True)
                # Ищем текст после запятой (город обычно идет после названия компании)
                if ',' in city_text:
                    city = city_text.split(',', 1)[1].strip()
                else:
                    city = city_text
            else:
                city = "Не указано"
            
            # Пытаемся найти официальный сайт компании
            official_website = ""
            social_media = ""
            
            if company_url and company_url.startswith('http'):
                try:
                    time.sleep(0.5)  # Небольшая задержка между запросами
                    official_website = get_company_website(company_url)
                    
                    # Если нашли официальный сайт, пытаемся получить соцсети с него
                    if official_website:
                        try:
                            time.sleep(0.5)
                            website_response = requests.get(official_website, headers=headers, timeout=10)
                            if website_response.status_code == 200:
                                website_soup = BeautifulSoup(website_response.text, 'html.parser')
                                social_media = get_social_media_links(website_soup, official_website)
                        except:
                            pass
                except:
                    pass
            
            data.append({
                'Название': name,
                'Город': city,
                'Сайт': official_website if official_website else company_url,
                'Соцсети': social_media
            })
            
        except Exception as e:
            print(f"Ошибка при обработке компании: {e}")
            continue
    
    return data

def get_total_pages(soup):
    """Определяет общее количество страниц"""
    pagination_text = soup.find('p', class_='pagination__hint')
    if pagination_text:
        text = pagination_text.get_text(strip=True)
        # Ищем паттерн "1 - 20 из 2857"
        match = re.search(r'из (\d+)', text)
        if match:
            total_companies = int(match.group(1))
            companies_per_page = 20
            total_pages = (total_companies + companies_per_page - 1) // companies_per_page
            return min(total_pages, 13)  # Ограничиваем до 13 страниц (250 компаний)
    return 1

def parse_companies(url):
    """Парсит данные о компаниях-застройщиках с учетом пагинации"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Загружаем первую страницу для определения количества страниц
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        total_pages = get_total_pages(soup)
        print(f"Всего страниц для обработки: {total_pages}")
        
        all_data = []
        
        for page in range(1, total_pages + 1):
            print(f"\nОбрабатываем страницу {page} из {total_pages}...")
            
            # Формируем URL для текущей страницы
            if page == 1:
                page_url = url
            else:
                # Добавляем параметр страницы к URL
                if '?' in url:
                    page_url = f"{url}&page={page}"
                else:
                    page_url = f"{url}?page={page}"
            
            try:
                response = requests.get(page_url, headers=headers, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                page_data = parse_companies_from_page(soup, headers)
                all_data.extend(page_data)
                
                print(f"На странице {page} найдено компаний: {len(page_data)}")
                
                # Небольшая задержка между запросами страниц
                time.sleep(1)
                
            except Exception as e:
                print(f"Ошибка при загрузке страницы {page}: {e}")
                continue
        
        return pd.DataFrame(all_data)
        
    except Exception as e:
        print(f"Ошибка при загрузке страницы: {e}")
        return pd.DataFrame()

def main():
    """Основная функция"""
    # Ссылка на рейтинг ЕРЗ (топ 250 компаний)
    url = 'https://erzrf.ru/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801'
    
    print("Начинаем парсинг данных...")
    
    # Парсим данные
    df_companies = parse_companies(url)
    
    if not df_companies.empty:
        # Ограничиваем до 250 компаний
        df_companies = df_companies.head(250)
        
        # Сохраняем в Excel
        output_file = 'top_250_realestate_companies_final.xlsx'
        df_companies.to_excel(output_file, index=False)
        print(f"\nГотово! Данные сохранены в файл: {output_file}")
        print(f"Всего обработано компаний: {len(df_companies)}")
        
        # Показываем статистику
        companies_with_website = df_companies[df_companies['Сайт'].notna() & (df_companies['Сайт'] != '')]
        companies_with_social = df_companies[df_companies['Соцсети'].notna() & (df_companies['Соцсети'] != '')]
        
        print(f"Компаний с сайтами: {len(companies_with_website)}")
        print(f"Компаний с соцсетями: {len(companies_with_social)}")
        
        # Показываем первые 5 записей
        print("\nПервые 5 компаний:")
        print(df_companies.head())
    else:
        print("Не удалось получить данные")

if __name__ == "__main__":
    main()