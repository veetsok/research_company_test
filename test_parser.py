#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсера на одной странице
"""

from erzrf_parser import ERZRFParser
import time

def test_single_page():
    """Тест парсинга одной страницы"""
    parser = ERZRFParser()
    
    print("Тестируем парсинг одной страницы...")
    
    # Тестируем извлечение ссылок с первой страницы
    links = parser.extract_company_links_from_page(1)
    print(f"Найдено ссылок: {len(links)}")
    
    if links:
        print("Первые 3 ссылки:")
        for i, link in enumerate(links[:3], 1):
            print(f"{i}. {link}")
        
        # Тестируем парсинг первой компании
        print(f"\nТестируем парсинг первой компании: {links[0]}")
        company_data = parser.extract_company_data(links[0])
        
        if company_data:
            print("Данные компании:")
            for key, value in company_data.items():
                print(f"  {key}: {value}")
        else:
            print("Не удалось извлечь данные компании")
    else:
        print("Ссылки не найдены")

def test_specific_company():
    """Тест парсинга конкретной компании из примера"""
    parser = ERZRFParser()
    
    # URL из примера в задаче
    test_url = "https://erzrf.ru/zastroyschiki/brand/profi-invest-3732427001?region=vse-regiony&regionKey=0&organizationId=3732427001&costType=1"
    
    print(f"Тестируем парсинг конкретной компании: {test_url}")
    
    company_data = parser.extract_company_data(test_url)
    
    if company_data:
        print("Данные компании:")
        for key, value in company_data.items():
            print(f"  {key}: {value}")
    else:
        print("Не удалось извлечь данные компании")

if __name__ == "__main__":
    print("=== ТЕСТ ПАРСЕРА ERZRF.RU ===\n")
    
    # Тест 1: Парсинг одной страницы топа
    test_single_page()
    
    print("\n" + "="*50 + "\n")
    
    # Тест 2: Парсинг конкретной компании
    test_specific_company()