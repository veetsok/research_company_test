import pandas as pd

def view_results():
    """Просматривает результаты парсинга"""
    try:
        # Загружаем данные из Excel файла
        df = pd.read_excel('top_250_realestate_companies.xlsx')
        
        print(f"Всего компаний в файле: {len(df)}")
        print("\nПервые 10 компаний:")
        print(df.head(10).to_string(index=False))
        
        print("\nПоследние 5 компаний:")
        print(df.tail(5).to_string(index=False))
        
        # Статистика по городам
        print("\nТоп-10 городов по количеству компаний:")
        city_counts = df['Город'].value_counts().head(10)
        for city, count in city_counts.items():
            print(f"  {city}: {count} компаний")
        
        # Компании с соцсетями
        companies_with_social = df[df['Соцсети'].notna() & (df['Соцсети'] != '')]
        print(f"\nКомпаний с найденными соцсетями: {len(companies_with_social)}")
        
        # Компании с сайтами
        companies_with_website = df[df['Сайт'].notna() & (df['Сайт'] != '')]
        print(f"Компаний с сайтами: {len(companies_with_website)}")
        
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")

if __name__ == "__main__":
    view_results()