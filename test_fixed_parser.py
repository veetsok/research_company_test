#!/usr/bin/env python3
"""
Тест исправленного парсера
"""

from fixed_erzrf_parser import FixedERZRFParser

def test_fixed_parser():
    """Тест исправленного парсера на 3 компаниях"""
    parser = FixedERZRFParser()
    
    try:
        print("🔧 ТЕСТИРУЕМ ИСПРАВЛЕННЫЙ ПАРСЕР")
        print("Парсим первые 3 компании с первой страницы...")
        print("="*60)
        
        # Получаем ссылки с первой страницы
        links = parser.get_company_links_from_page(1)
        if not links:
            print("❌ Не удалось получить ссылки")
            return
        
        print(f"✅ Найдено {len(links)} ссылок")
        
        # Парсим первые 3 компании
        for i, link in enumerate(links[:3], 1):
            print(f"\n📊 КОМПАНИЯ {i}/3")
            print(f"URL: {link}")
            
            company_data = parser.extract_company_data(link)
            if company_data:
                parser.companies_data.append(company_data)
                
                print(f"✅ Название: '{company_data['название']}'")
                print(f"🏙️  Город: '{company_data['город'] if company_data['город'] else 'Не найден'}'")
                print(f"🌐 Сайт: '{company_data['сайт'] if company_data['сайт'] else 'Не найден'}'")
                print(f"📱 Соцсети: '{company_data['соцсети'] if company_data['соцсети'] else 'Не найдены'}'")
            else:
                print("❌ Не удалось извлечь данные")
        
        # Сохраняем результат
        if parser.companies_data:
            parser.save_to_excel('test_fixed_result.xlsx')
            parser.save_to_csv('test_fixed_result.csv')
            
            print(f"\n🎉 ТЕСТ ЗАВЕРШЕН!")
            print(f"Обработано компаний: {len(parser.companies_data)}")
            print("Результаты сохранены в test_fixed_result.xlsx и test_fixed_result.csv")
            
            # Статистика
            with_sites = sum(1 for c in parser.companies_data if c['сайт'])
            with_social = sum(1 for c in parser.companies_data if c['соцсети'])
            with_cities = sum(1 for c in parser.companies_data if c['город'])
            
            print(f"\n📈 СТАТИСТИКА:")
            print(f"Компаний с сайтами: {with_sites}/{len(parser.companies_data)}")
            print(f"Компаний с соцсетями: {with_social}/{len(parser.companies_data)}")
            print(f"Компаний с городами: {with_cities}/{len(parser.companies_data)}")
            
            # Показываем примеры данных
            print(f"\n📋 ПРИМЕРЫ ДАННЫХ:")
            for i, company in enumerate(parser.companies_data, 1):
                print(f"{i}. {company['название']} | {company['город']} | {company['сайт']}")
        
    finally:
        parser.close()

if __name__ == "__main__":
    test_fixed_parser()