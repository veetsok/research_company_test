#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_single_company():
    """Тестирование одной компании для понимания структуры"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })
    
    # URL компании ПИК
    url = "https://erzrf.ru/zastroyschiki/brand/pik-429726001?region=vse-regiony&regionKey=0&organizationId=429726001"
    
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print("=== АНАЛИЗ СТРАНИЦЫ КОМПАНИИ ПИК ===")
        
        # Ищем все ссылки на странице
        all_links = soup.find_all('a', href=True)
        print(f"Всего ссылок на странице: {len(all_links)}")
        
        # Фильтруем внешние ссылки
        external_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if href.startswith('http') and 'erzrf.ru' not in href:
                external_links.append({
                    'href': href,
                    'text': text
                })
        
        print(f"\nВнешние ссылки ({len(external_links)}):")
        for i, link in enumerate(external_links, 1):
            print(f"{i}. {link['href']} - {link['text']}")
        
        # Ищем блоки с информацией
        info_blocks = soup.find_all(['div', 'section'], class_=True)
        print(f"\nБлоки с классами ({len(info_blocks)}):")
        for i, block in enumerate(info_blocks[:10], 1):  # Показываем первые 10
            classes = ' '.join(block.get('class', []))
            print(f"{i}. <{block.name} class=\"{classes}\">")
        
        # Сохраняем HTML для детального анализа
        with open('single_company_analysis.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("\nHTML сохранен в single_company_analysis.html")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")

if __name__ == "__main__":
    test_single_company()