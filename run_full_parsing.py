#!/usr/bin/env python3
"""
Запуск полного парсинга всех 250 компаний
"""

from final_erzrf_parser import FinalERZRFParser
import sys

def main():
    print("🚀 ЗАПУСК ПОЛНОГО ПАРСИНГА ERZRF.RU")
    print("Парсим ТОП-250 застройщиков России")
    print("="*60)
    print("⚠️  ВНИМАНИЕ: Процесс займет 2-3 часа!")
    print("📊 Будет обработано ~250 компаний с 13 страниц")
    print("💾 Промежуточные сохранения каждые 20 компаний")
    print("="*60)
    
    # Подтверждение запуска
    try:
        response = input("Начать полный парсинг? (y/N): ").strip().lower()
        if response not in ['y', 'yes', 'да']:
            print("Парсинг отменен.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\nПарсинг отменен.")
        sys.exit(0)
    
    # Запуск парсера
    parser = FinalERZRFParser()
    
    try:
        print("\n🎯 НАЧИНАЕМ ПОЛНЫЙ ПАРСИНГ...")
        companies = parser.parse_all_pages(max_pages=15)
        
        # Сохраняем финальные результаты
        parser.save_to_excel('erzrf_companies_final.xlsx')
        parser.save_to_csv('erzrf_companies_final.csv')
        parser.save_failed_urls('failed_urls.txt')
        
        print(f"\n🎉 ПАРСИНГ ЗАВЕРШЕН УСПЕШНО!")
        print(f"📊 Обработано компаний: {len(companies)}")
        print(f"📁 Результаты сохранены в:")
        print(f"   - erzrf_companies_final.xlsx")
        print(f"   - erzrf_companies_final.csv")
        if parser.failed_urls:
            print(f"   - failed_urls.txt ({len(parser.failed_urls)} неудачных URL)")
        
    except KeyboardInterrupt:
        print("\n⚠️ Парсинг прерван пользователем")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_partial.xlsx')
            parser.save_to_csv('erzrf_companies_partial.csv')
            parser.save_failed_urls('failed_urls_partial.txt')
            print(f"💾 Частичные данные сохранены ({len(parser.companies_data)} компаний)")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        if parser.companies_data:
            parser.save_to_excel('erzrf_companies_error.xlsx')
            parser.save_to_csv('erzrf_companies_error.csv')
            parser.save_failed_urls('failed_urls_error.txt')
            print(f"💾 Данные до ошибки сохранены ({len(parser.companies_data)} компаний)")
        sys.exit(1)
        
    finally:
        parser.close()

if __name__ == "__main__":
    main()