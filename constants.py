help_msg = ''' 
Щоб переглянути список сусідів:

<b>по обраному будинку</b>
Тисни:
<code>Дивитись сусідів 👫 ➡ Будинок ➡ Показати всіх в цьому будинку 🏠</code>\n

<b>по обраному під\'їзду</b>
Тисни:
<code>Дивитись сусідів 👫 ➡ Будинок ➡ Під\'їзд</code>\n

<b>по своєму будинку</b>
Тисни: <code>'Мій будинок 🏠'</code>

<b>по своєму під\'їзду</b>
Тисни: <code>'Мій під\'їзд 🔢'</code>

Щоб додати або змінити свої дані:

Тисни: <code>Змінити свої дані ✏</code>,
і вибери свої <i>будинок, під\'їзд, поверх, квартиру</i>\n

Виключні ситуації:
Якщо бажаєте додати більше однієї квартири, напишіть про це <a href="tg://user?id=422485737">сюди</a>
'''

about_msg = '''
Привіт!

Я бот, який допомогає формувати список мешканців ЖК Перемога. Його можна переглянути та зв'язатися зі своїм сусідом.

Службові команди:
/start - головне меню
/help - опис функціоналу
/about - про бота

З пропозиціями та зауваженнями звертайтесь <a href="tg://user?id=422485737">сюди</a>.
'''

building_msg = '''
Поки що тут немає інформації, але згодом вона буде.
'''

greeting_msg = '''
Вітаю {}! Давайте знайомитись,
додайтесь до списку сусідів в @peremogy_susid_bot,
та прочитайте <a href="https://telegra.ph/Vazhno-06-06">важливу інформацію</a> для новачків.
'''

house_85 = {
    'section_1': [i for i in range(1, 10)] + ['8-9'],
    'section_2': [i for i in range(1, 10)] + ['8-9'],
    'section_3': [i for i in range(1, 10)] + ['8-9'],
    'section_4': [i for i in range(1, 10)] + ['8-9'],
    'section_5': [i for i in range(1, 10)] + ['8-9'],
    'section_6': [i for i in range(1, 10)] + ['8-9'],
}

house_87 = {
    'section_1': [i for i in range(1, 10)] + ['8-9'],
    'section_2': [i for i in range(1, 10)] + ['8-9'],
}

house_89 = {
    'section_1': [i for i in range(1, 10)] + ['8-9'],
    'section_2': [i for i in range(1, 10)] + ['8-9'],
    'section_3': [i for i in range(1, 10)] + ['8-9'],
    'section_4': [i for i in range(1, 10)] + ['8-9'],
    'section_5': [i for i in range(1, 10)] + ['8-9'],
    'section_6': [i for i in range(1, 10)] + ['8-9'],
}

houses_arr = {
    'house_85': house_85,
    'house_87': house_87,
    'house_89': house_89,
}