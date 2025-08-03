import requests
from bs4 import BeautifulSoup

def debug_site_structure(url):
    """Анализирует структуру сайта для понимания как парсить данные"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"Статус ответа: {response.status_code}")
        print(f"Заголовок страницы: {soup.title.string if soup.title else 'Нет заголовка'}")
        
        # Ищем все элементы с классом developer
        developer_items = soup.find_all('li', class_='developer')
        print(f"\nНайдено компаний: {len(developer_items)}")
        
        # Ищем кнопки загрузки или пагинацию
        load_more_buttons = soup.find_all(['button', 'a'], string=re.compile(r'показать|загрузить|еще|больше|следующая|next|load|show', re.I))
        print(f"\nНайдено кнопок загрузки: {len(load_more_buttons)}")
        for btn in load_more_buttons:
            print(f"  Кнопка: {btn.get_text(strip=True)} - {btn.get('class', 'Нет классов')}")
        
        # Ищем элементы пагинации
        pagination = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'pagination|pager|page', re.I))
        print(f"\nНайдено элементов пагинации: {len(pagination)}")
        for pag in pagination:
            print(f"  Пагинация: {pag.get('class', 'Нет классов')}")
        
        # Ищем скрипты с данными
        scripts = soup.find_all('script')
        data_scripts = [s for s in scripts if 'data' in s.get_text().lower() or 'companies' in s.get_text().lower()]
        print(f"\nНайдено скриптов с данными: {len(data_scripts)}")
        
        # Ищем элементы с атрибутами ng-click или onclick
        click_elements = soup.find_all(attrs={'ng-click': True}) + soup.find_all(attrs={'onclick': True})
        print(f"\nНайдено элементов с обработчиками кликов: {len(click_elements)}")
        for elem in click_elements[:5]:
            print(f"  Элемент: {elem.name} - {elem.get('ng-click', elem.get('onclick', ''))}")
        
        # Ищем элементы с классом, содержащим "load", "more", "pagination"
        load_elements = soup.find_all(class_=re.compile(r'load|more|pagination|pager|next|prev', re.I))
        print(f"\nНайдено элементов загрузки: {len(load_elements)}")
        for elem in load_elements[:5]:
            print(f"  Элемент: {elem.name} - {elem.get('class', 'Нет классов')} - {elem.get_text(strip=True)[:50]}")
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    import re
    url = 'https://erzrf.ru/top-zastroyshchikov/rf?regionKey=0&topType=0&date=250801'
    debug_site_structure(url)