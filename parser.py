from bs4 import BeautifulSoup
import requests
import json

main_url = 'https://www.alfabank.by/'
cards_url = 'https://www.alfabank.by/cards/'


def get_soup(url: str):
    res = requests.get(url)
    return BeautifulSoup(res.text, 'html.parser')


def extract_description(description_element):
    description = None

    if description_element:
        # Try different ways to get the description
        if description_element.find('p'):
            description = description_element.find('p').text.strip()
        elif description_element.text.strip():
            description = description_element.text.strip()
        elif description_element.find('b') and description_element.find('p'):
            description = description_element.find('b').text.strip() + ' ' + description_element.find('p').text.strip()
        elif description_element.find('b'):
            description = description_element.find('b').text.strip()

    return description


def parse_cards(soup):
    cards = []
    card_items = soup.find_all('div', class_='product-item')

    for item in card_items:
        title_element = item.find('h2', class_='product-item__title')
        link_element = item.find('a', class_='link-more')
        description_element = item.find('div', class_='product-item__description')
        first_item_element = item.find('div', class_='item-wrapper')
        second_item_element = item.find('div', class_='item-wrapper').find_next('div', class_='item-wrapper')

        if title_element and link_element:
            title = title_element.text.strip()
            link = main_url + link_element['href'].strip()
            description = extract_description(description_element)

            first_element = first_item_element.find('p',
                                                    class_='item-top').text.strip() + ' ' + first_item_element.find('p',
                                                                                                                    class_='item-bottom').text.strip()
            second_element = second_item_element.find('p',
                                                      class_='item-top').text.strip() + ' ' + second_item_element.find(
                'p', class_='item-bottom').text.strip()

            cards.append({
                'title': title,
                'link': link,
                'description': description,
                'first_element': first_element,
                'second_element': second_element
            })

    return cards


def parse_additional_info(soup):
    info = {}

    # Extracting the benefits
    benefits_section = soup.find('div', class_='seo-block__content js-seo-content')
    benefits_header = benefits_section.find('h3').text.strip()
    benefits_list = benefits_section.find('ul', class_='dashed-list').find('li')
    benefits = [item.text.strip() for item in benefits_list]

    # Extracting the card ordering information
    ordering_section = benefits_section.find('h3').find_next('h3')
    ordering_header = ordering_section.text.strip()
    ordering_paragraphs = ordering_section.find_next_siblings('p')
    ordering_info = [para.text.strip() for para in ordering_paragraphs]
    additional_list_section = benefits_section.find('ul', class_='dashed-list').find_next('ul', class_='dashed-list')
    additional_list_items = additional_list_section.find_all('li')
    additional_list = []
    for item in additional_list_items:
        link_element = item.find('a', class_='red-link')
        if link_element:
            title = link_element.text.strip()
            link = link_element['href'].strip()
            additional_list.append({'title': title, 'link': link})

    info['benefits_header'] = benefits_header
    info['benefits'] = benefits
    info['ordering_header'] = ordering_header
    info['ordering_info'] = ordering_info
    info['additional_list'] = additional_list

    return info


def parse_FAQ(soup):
    faqs = []
    faq_script = soup.find('script', type='application/ld+json')
    faq_json = json.loads(faq_script.string)
    if faq_json.get('@type') == 'FAQPage':
        for item in faq_json.get('mainEntity', []):
            faqs.append({
                'question': item.get('name'),
                'answer': BeautifulSoup(item.get('acceptedAnswer', {}).get('text', ''), 'html.parser').get_text()
            })
    return faqs


if __name__ == "__main__":
    # Parsing cards
    cards_page_soup = get_soup(cards_url)
    cards = parse_cards(cards_page_soup)
    additional_info = parse_additional_info(cards_page_soup)
    faqs = parse_FAQ(cards_page_soup)

    with open('data/alfabank_info.txt', 'w', encoding='utf-8') as file:
        file.write("Альфабанк Беларусь выдаёт следующие типы карт:")
        for card in cards:
            file.write(f" {card['title']},")

        for card in cards:
            file.write(
                f'Вы можете оформить карту "{card["title"]}" перейдя по ссылке {card["link"]}.\n\n')

        for card in cards:
            file.write(
                f"Для заказа кредитной карты {card['title']} в Альфабанк Беларусь нужно перейти по ссылке {card['link']}. Описание: {card['description']}. Бонусы: {card['first_element']} и {card['second_element']}.\n\n")

        if 'benefits_header' in additional_info:
            file.write(
                f"Более 200 тысяч клиентов Альфа-Банка уже оформили бесплатные банковские карты в Беларуси в рамках Пакетов решений Alfa Smart, и им доступны такие преимущества:")
            for benefit in additional_info['benefits']:
                file.write(f"{benefit}, ")

        if 'ordering_header' in additional_info:
            file.write(f"{additional_info['ordering_header']}")
            for info in additional_info['ordering_info']:
                file.write(f"{info}. ")

        if 'additional_list' in additional_info:
            for item in additional_info['additional_list']:
                file.write(f"{item['title']} (ссылка: {item['link']}). ")

        if faqs:
            file.write("\n\nОтветы на вопросы: ")
            for faq in faqs:
                file.write(f"{faq['question']}{faq['answer']}  ")
