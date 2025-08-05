#!/usr/bin/env python3
"""
Запуск исправленного парсера для всех 250 компаний
"""

from fixed_erzrf_parser import FixedERZRFParser
import sys

def main():
    print("🔧 ЗАПУСК ИСПРАВЛЕННОГО ПАРСЕРА ERZRF.RU")
    print("Парсим ТОП-250 застройщиков России")
    print("="*60)
    print("✨ ИСПРАВЛЕНИЯ:")
    print("- Улучшена очистка текста от переносов строк")
    print("- Улучшены паттерны поиска сайтов")
    print("- Улучшены паттерны поиска соцсетей")
    print("- Улучшены паттерны поиска городов")
    print("- Добавлена фильтрация нерелевантных ссылок")
    print("="*60)
    print("⚠️  ВНИМАНИЕ: Процесс займет 2-3 часа!")
    print("📊 Будет обработано ~250 компаний с 13 страниц")
    print("💾 Промежуточные сохранения каждые 20 компаний")
    print("="*60)
    
    # Подтверждение запуска
    try:
        response = input("Начать полный парсинг исправленной версией? (y/N): ").strip().lower()
        if response not in ['y', 'yes', 'да']:
            print("Парсинг отменен.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\nПарсинг отменен.")
        sys.exit(0)
    
    # Запуск парсера
    parser = FixedERZRFParser()
    
    try:
        print("\n🎯 НАЧИНАЕМ ПОЛНЫЙ ПАРСИНГ ИСПРАВЛЕННОЙ ВЕРСИЕЙ...")
        companies = parser.parse_all_pages(max_pages=15)
        
        # Сохраняем финальные результаты
        parser.save_to_excel('erzrf_companies_fixed_final.xlsx')
        parser.save_to_csv('erzrf_companies_fixed_final.csv')
        parser.save_failed_urls('failed_urls_fixed_final.txt')
        
        print(f"\n🎉 ПАРСИНГ ЗАВЕРШЕН УСПЕШНО!")
        print(f"📊 Обработано компаний: {len(companies)}")
        print(f"📁 Результаты сохранены в:")
        print(f"   - erzrf_companies_fixed_final.xlsx")
        print(f"   - erzrf_companies_fixed_final.csv")
        if parser.failed_urls:
            print(f"   - failed_urls_fixed_final.txt ({len(parser.failed_urls)} неудачных URL)")
        
        # Показываем статистику
        if companies:
            with_sites = sum(1 for c in companies if c['сайт'])
            with_social = sum(1 for c in companies if c['соцсети'])
            with_cities = sum(1 for c in companies if c['город'])
            
            print(f"\n📈 ФИНАЛЬНАЯ СТАТИСТИКА:")
            print(f"Компаний с сайтами: {with_sites}/{len(companies)} ({with_sites/len(companies)*100:.1f}%)")
            print(f"Компаний с соцсетями: {with_social}/{len(companies)} ({with_social/len(companies)*100:.1f}%)")
            print(f"Компаний с городами: {with_cities}/{len(companies)} ({with_cities/len(companies)*100:.1f}%)")
        
    except KeyboardInterrupt:
        print("\n⚠️ Парсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_partial_fixed.xlsx')
            parser.save_to_csv('erzrf_companies_partial_fixed.csv')
            parser.save_failed_urls('failed_urls_partial_fixed.txt')
            print(f"💾 Частичные данные сохранены ({len(parser.companies_data)} компаний)")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_error_fixed.xlsx')
            parser.save_to_csv('erzrf_companies_error_fixed.csv')
            parser.save_failed_urls('failed_urls_error_fixed.txt')
            print(f"💾 Данные до ошибки сохранены ({len(parser.companies_data)} компаний)")
        sys.exit(1)
        
    finally:
        parser.close()

if __name__ == "__main__":
    main()