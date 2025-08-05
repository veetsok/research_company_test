#!/usr/bin/env python3
"""
Тестовый скрипт для Selenium парсера
"""

from erzrf_selenium_parser import ERZRFSeleniumParser
import time

def test_single_page():
    """Тест парсинга одной страницы"""
    parser = ERZRFSeleniumParser(headless=False)  # Не headless для отладки
    
    try:
        print("Тестируем парсинг одной страницы...")
        
        # Тестируем извлечение ссылок с первой страницы
        links = parser.get_company_links_from_page(1)
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
    finally:
        parser.close()

def test_specific_company():
    """Тест парсинга конкретной компании из примера"""
    parser = ERZRFSeleniumParser(headless=False)  # Не headless для отладки
    
    try:
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
    finally:
        parser.close()

def test_few_companies():
    """Тест парсинга нескольких компаний"""
    parser = ERZRFSeleniumParser(headless=True)
    
    try:
        print("Тестируем парсинг первых 5 компаний...")
        
        # Получаем ссылки с первой страницы
        links = parser.get_company_links_from_page(1)
        if not links:
            print("Не удалось получить ссылки")
            return
        
        # Парсим первые 5 компаний
        for i, link in enumerate(links[:5], 1):
            print(f"\n--- Компания {i}/5 ---")
            company_data = parser.extract_company_data(link)
            if company_data:
                parser.companies_data.append(company_data)
                print(f"Название: {company_data['название']}")
                print(f"Город: {company_data['город']}")
                print(f"Сайт: {company_data['сайт']}")
                print(f"Соцсети: {company_data['соцсети']}")
            else:
                print("Не удалось извлечь данные")
        
        # Сохраняем результат
        if parser.companies_data:
            parser.save_to_excel('test_result.xlsx')
            parser.save_to_csv('test_result.csv')
            print(f"\nТест завершен! Обработано {len(parser.companies_data)} компаний")
        
    finally:
        parser.close()

if __name__ == "__main__":
    print("=== ТЕСТ SELENIUM ПАРСЕРА ERZRF.RU ===\n")
    
    # Выберите тест для запуска:
    
    # Тест 1: Парсинг одной страницы (с видимым браузером)
    # test_single_page()
    
    # Тест 2: Парсинг конкретной компании (с видимым браузером)  
    # test_specific_company()
    
    # Тест 3: Парсинг нескольких компаний (в headless режиме)
    test_few_companies()