#!/usr/bin/env python3
"""
Тестовый скрипт для улучшенного парсера
"""

from erzrf_improved_parser import ERZRFImprovedParser

def test_specific_company():
    """Тест парсинга конкретной компании из примера"""
    parser = ERZRFImprovedParser()
    
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
    parser = ERZRFImprovedParser()
    
    try:
        print("Тестируем парсинг первых 3 компаний...")
        
        # Получаем ссылки с первой страницы
        links = parser.get_company_links_from_page(1)
        if not links:
            print("Не удалось получить ссылки")
            return
        
        print(f"Найдено {len(links)} ссылок. Парсим первые 3...")
        
        # Парсим первые 3 компании
        for i, link in enumerate(links[:3], 1):
            print(f"\n--- Компания {i}/3 ---")
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
            parser.save_to_excel('test_improved_result.xlsx')
            parser.save_to_csv('test_improved_result.csv')
            print(f"\nТест завершен! Обработано {len(parser.companies_data)} компаний")
        
    finally:
        parser.close()

if __name__ == "__main__":
    print("=== ТЕСТ УЛУЧШЕННОГО ПАРСЕРА ERZRF.RU ===\n")
    
    # Тест 1: Конкретная компания
    test_specific_company()
    
    print("\n" + "="*50 + "\n")
    
    # Тест 2: Несколько компаний
    test_few_companies()