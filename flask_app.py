# импортируем библиотеки
from flask import Flask, request
import logging
import pymorphy2

# библиотека, которая нам понадобится для работы с JSON
import json

import os

# создаём приложение
# мы передаём __name__, в нем содержится информация,
# в каком модуле мы находимся.
# В данном случае там содержится '__main__',
# так как мы обращаемся к переменной из запущенного модуля.
# если бы такое обращение, например,
# произошло внутри модуля logging, то мы бы получили 'logging'
app = Flask(__name__)

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

# Создадим словарь, чтобы для каждой сессии общения
# с навыком хранились подсказки, которые видел пользователь.
# Это поможет нам немного разнообразить подсказки ответов
# (buttons в JSON ответа).
# Когда новый пользователь напишет нашему навыку,
# то мы сохраним в этот словарь запись формата
# sessionStorage[user_id] = {'suggests': ["Не хочу.", "Не буду.", "Отстань!" ]}
# Такая запись говорит, что мы показали пользователю эти три подсказки.
# Когда он откажется купить слона,
# то мы уберем одну подсказку. Как будто что-то меняется :)
sessionStorage = {}

animals = [
    'слон',
    'кролик'
]
animal_index = 0

morph = pymorphy2.MorphAnalyzer()


@app.route('/post', methods=['POST'])
# Функция получает тело запроса и возвращает ответ.
# Внутри функции доступен request.json - это JSON,
# который отправила нам Алиса в запросе POST
def main():
    logging.info(f'Request: {request.json!r}')

    # Начинаем формировать ответ, согласно документации
    # мы собираем словарь, который потом при помощи
    # библиотеки json преобразуем в JSON и отдадим Алисе
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    # Отправляем request.json и response в функцию handle_dialog.
    # Она сформирует оставшиеся поля JSON, которые отвечают
    # непосредственно за ведение диалога
    handle_dialog(request.json, response)

    logging.info(f'Response:  {response!r}')

    # Преобразовываем в JSON и возвращаем
    return json.dumps(response)


def handle_dialog(req, res):
    global animal_index
    user_id = req['session']['user_id']

    if req['session']['new']:
        # Это новый пользователь.
        # Инициализируем сессию и поприветствуем его.
        # Запишем подсказки, которые мы ему покажем в первый раз

        sessionStorage[user_id] = {
            'suggests': [
                "Не хочу.",
                "Не буду.",
                "Отстань!",
            ]
        }
        # Заполняем текст ответа
        animal = animals[animal_index]
        parse = morph.parse(animal)[0]
        word = parse.inflect({'sing', 'gent'}).word
        res['response']['text'] = f'Привет! Купи {word}!'
        # Получим подсказки
        res['response']['buttons'] = get_suggests(user_id)
        return

    # Сюда дойдем только, если пользователь не новый,
    # и разговор с Алисой уже был начат
    # Обрабатываем ответ пользователя.
    # В req['request']['original_utterance'] лежит весь текст,
    # что нам прислал пользователь
    # Если он написал 'ладно', 'куплю', 'покупаю', 'хорошо',
    # то мы считаем, что пользователь согласился.
    # Подумайте, всё ли в этом фрагменте написано "красиво"?
    if any(map(lambda word: word in req['request']['original_utterance'].lower(), ['ладно',
                                                                                   'куплю',
                                                                                   'покупаю',
                                                                                   'хорошо'])):
        # Пользователь согласился, прощаемся.
        animal = animals[animal_index]
        parse = morph.parse(animal)[0]
        word = parse.inflect({'sing', 'gent'}).word
        res['response']['text'] = f'{word} можно найти на Яндекс.Маркете!'.capitalize()
        animal_index += 1
        if animal_index >= len(animals):
            res['response']['end_session'] = True
            animal_index = 0
            return
        else:
            sessionStorage[user_id] = {
                'suggests': [
                    "Не хочу.",
                    "Не буду.",
                    "Отстань!",
                ]
            }
            animal = animals[animal_index]
            parse = morph.parse(animal)[0]
            word = parse.inflect({'sing', 'gent'}).word
            res['response']['text'] += f'\nА теперь купи {word}!'
            res['response']['buttons'] = get_suggests(user_id)
    else:
        # Если нет, то убеждаем его купить слона!
        animal = animals[animal_index]
        parse = morph.parse(animal)[0]
        word = parse.inflect({'sing', 'gent'}).word
        res['response']['text'] = \
            f"Все говорят '{req['request']['original_utterance']}', а ты купи {word}!"
        res['response']['buttons'] = get_suggests(user_id)


# Функция возвращает две подсказки для ответа.
def get_suggests(user_id):
    session = sessionStorage[user_id]

    # Выбираем две первые подсказки из массива.
    suggests = [
        {'title': suggest, 'hide': True}
        for suggest in session['suggests'][:2]
    ]

    # Убираем первую подсказку, чтобы подсказки менялись каждый раз.
    session['suggests'] = session['suggests'][1:]
    sessionStorage[user_id] = session

    # Если осталась только одна подсказка, предлагаем подсказку
    # со ссылкой на Яндекс.Маркет.
    if len(suggests) < 2:
        animal = animals[animal_index]
        suggests.append({
            "title": "Ладно",
            "url": f"https://market.yandex.ru/search?text={animal}",
            "hide": True
        })

    return suggests


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
