#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import time
import re

def analyze_pagination():
    """Анализ пагинации на сайте erzrf.ru"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    })
    
    base_url = 'https://erzrf.ru/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801'
    
    print("Анализируем пагинацию...")
    
    # Проверяем первые несколько страниц
    for page in range(1, 6):
        url = f"{base_url}&page={page}"
        print(f"\n=== СТРАНИЦА {page} ===")
        print(f"URL: {url}")
        
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем ссылки на компании
            company_links = []
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                if '/zastroyschiki/brand/' in href:
                    company_name = link.get_text(strip=True)
                    if company_name and len(company_name) > 2 and not company_name.isdigit():
                        company_links.append({
                            'name': company_name,
                            'url': href,
                            'full_url': f"https://erzrf.ru{href}" if href.startswith('/') else href
                        })
            
            # Убираем дубликаты
            unique_companies = []
            seen_names = set()
            for company in company_links:
                if company['name'] not in seen_names:
                    unique_companies.append(company)
                    seen_names.add(company['name'])
            
            print(f"Найдено уникальных компаний: {len(unique_companies)}")
            
            # Показываем первые 5 компаний
            for i, company in enumerate(unique_companies[:5], 1):
                print(f"{i + (page-1)*20}. {company['name']}")
                print(f"   URL: {company['full_url']}")
            
            if len(unique_companies) == 0:
                print("Компании не найдены - возможно, страница пустая")
                break
                
            time.sleep(1)  # Пауза между запросами
            
        except Exception as e:
            print(f"Ошибка на странице {page}: {e}")
    
    print(f"\nАнализ завершен!")

def analyze_company_card():
    """Анализ структуры карточки компании"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    })
    
    # Пример карточки из задачи
    test_url = "https://erzrf.ru/zastroyschiki/brand/profi-invest-3732427001?region=vse-regiony&regionKey=0&organizationId=3732427001&costType=1"
    
    print(f"\n=== АНАЛИЗ КАРТОЧКИ КОМПАНИИ ===")
    print(f"URL: {test_url}")
    
    try:
        response = session.get(test_url, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"Размер страницы: {len(response.text)} символов")
        
        # Ищем блок с сайтом
        site_block = soup.find('div', id='org-site')
        if site_block:
            print("\n✅ Найден блок org-site:")
            site_link = site_block.find('a')
            if site_link:
                href = site_link.get('href', '')
                text = site_link.get_text(strip=True)
                print(f"   Сайт: {href}")
                print(f"   Текст: {text}")
            else:
                print("   Ссылка не найдена в блоке")
        else:
            print("\n❌ Блок org-site не найден")
        
        # Ищем блок с соцсетями
        social_block = soup.find('app-org-social', id='org-social')
        if not social_block:
            social_block = soup.find(id='org-social')
        
        if social_block:
            print("\n✅ Найден блок org-social:")
            social_links = social_block.find_all('a', href=True)
            for link in social_links:
                href = link.get('href', '')
                if any(social in href.lower() for social in ['vk.com', 'instagram', 'facebook', 't.me', 'youtube', 'ok.ru']):
                    print(f"   Соцсеть: {href}")
        else:
            print("\n❌ Блок org-social не найден")
        
        # Сохраняем HTML для анализа
        with open('company_card_example.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"\nHTML карточки сохранен в 'company_card_example.html'")
        
    except Exception as e:
        print(f"Ошибка при анализе карточки: {e}")

if __name__ == "__main__":
    analyze_pagination()
    analyze_company_card()