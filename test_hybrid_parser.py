#!/usr/bin/env python3
"""
Тестовый скрипт для гибридного парсера
"""

from erzrf_hybrid_parser import ERZRFHybridParser

def test_few_companies():
    """Тест парсинга нескольких компаний"""
    parser = ERZRFHybridParser()
    
    try:
        print("Тестируем парсинг первых 5 компаний...")
        
        # Получаем ссылки с первой страницы
        links = parser.get_company_links_from_page(1)
        if not links:
            print("Не удалось получить ссылки")
            return
        
        print(f"Найдено {len(links)} ссылок. Парсим первые 5...")
        
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
            parser.save_to_excel('test_hybrid_result.xlsx')
            parser.save_to_csv('test_hybrid_result.csv')
            print(f"\nТест завершен! Обработано {len(parser.companies_data)} компаний")
        
    finally:
        parser.close()

if __name__ == "__main__":
    print("=== ТЕСТ ГИБРИДНОГО ПАРСЕРА ERZRF.RU ===\n")
    test_few_companies()