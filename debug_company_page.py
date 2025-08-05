#!/usr/bin/env python3
"""
Отладочный скрипт для детального изучения структуры страницы компании
"""

from requests_html import HTMLSession
import re

def debug_company_page():
    """Детальная отладка страницы компании"""
    session = HTMLSession()
    
    # URL из примера в задаче
    url = "https://erzrf.ru/zastroyschiki/brand/profi-invest-3732427001?region=vse-regiony&regionKey=0&organizationId=3732427001&costType=1"
    
    print(f"Отладка страницы компании: {url}")
    
    try:
        r = session.get(url)
        
        # Рендерим JavaScript
        print("Рендерим JavaScript...")
        r.html.render(timeout=20, wait=5)
        
        # Сохраняем полный HTML для анализа
        with open('company_page_rendered.html', 'w', encoding='utf-8') as f:
            f.write(r.html.html)
        print("Отрендеренный HTML сохранен в company_page_rendered.html")
        
        # Ищем все ссылки
        print("\n=== ВСЕ ССЫЛКИ НА СТРАНИЦЕ ===")
        all_links = r.html.find('a[href]')
        for i, link in enumerate(all_links, 1):
            href = link.attrs.get('href', '')
            text = link.text.strip()
            if href and 'http' in href:
                print(f"{i}. {href} - {text[:50]}")
        
        # Ищем элементы с id org-site
        print("\n=== ЭЛЕМЕНТЫ С ID ORG-SITE ===")
        org_site = r.html.find('#org-site')
        if org_site:
            print("Найден элемент #org-site:")
            print(org_site[0].html)
        else:
            print("Элемент #org-site не найден")
        
        # Ищем элементы с id org-social
        print("\n=== ЭЛЕМЕНТЫ С ID ORG-SOCIAL ===")
        org_social = r.html.find('#org-social')
        if org_social:
            print("Найден элемент #org-social:")
            print(org_social[0].html)
        else:
            print("Элемент #org-social не найден")
        
        # Ищем app-org-social
        print("\n=== ЭЛЕМЕНТЫ APP-ORG-SOCIAL ===")
        app_org_social = r.html.find('app-org-social')
        if app_org_social:
            print("Найден элемент app-org-social:")
            print(app_org_social[0].html)
        else:
            print("Элемент app-org-social не найден")
        
        # Ищем текст "Сайт" на странице
        print("\n=== ПОИСК ТЕКСТА 'САЙТ' ===")
        page_text = r.html.text
        site_matches = re.finditer(r'сайт.*?(\S+)', page_text, re.IGNORECASE)
        for match in site_matches:
            print(f"Найдено: {match.group(0)}")
        
        # Ищем div с классами, содержащими site или website
        print("\n=== ЭЛЕМЕНТЫ С КЛАССАМИ SITE/WEBSITE ===")
        site_elements = r.html.find('[class*="site"], [class*="website"]')
        for element in site_elements:
            print(f"Класс: {element.attrs.get('class')}")
            print(f"HTML: {element.html}")
            print("---")
        
        # Показываем весь текст страницы (первые 3000 символов)
        print(f"\n=== ТЕКСТ СТРАНИЦЫ (первые 3000 символов) ===")
        print(page_text[:3000])
        
    finally:
        session.close()

if __name__ == "__main__":
    debug_company_page()