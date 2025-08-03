import requests
from bs4 import BeautifulSoup
import pandas as pd

def parse_companies(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    data = []
    # Выбираем строки таблицы на сайте (проверь селектор по сайту!)
    for row in soup.select('.table tbody tr'):
        cols = row.find_all('td')
        if len(cols) >= 3:
            name = cols[1].get_text(strip=True)
            site = cols[1].find('a')['href'] if cols[1].find('a') else ''
            city = cols[2].get_text(strip=True)

            data.append({
                'Название компании': name,
                'Сайт компании': site,
                'Город': city
            })

    return pd.DataFrame(data)

# Ссылка на рейтинг ЕРЗ
url = 'https://erzrf.ru/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250701'

# Парсим данные
df_companies = parse_companies(url)

# Сохраняем в Excel
df_companies.to_excel('top_realestate_companies.xlsx', index=False)
print("Готово, файл создан!")
