import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp
from bs4 import BeautifulSoup

API_TOKEN = '7945272405:AAGKKMHbM03h8qaiYwkqsG7CGk_afJSashA'  # Укажите ваш токен
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Словарь для замены русских слов на английские
translations = {
    "Кабрио": "kabrio",
    "Купе": "kupe",
    "Хэтчбек": "xetchbek",
    "3дв.": "3dv",
    "5дв": "5dv",
    "Gran Turismo": "gran-turismo",
    "Универсал": "universal",
    "Седан": "sedan",
    "Фургон": "furgon",
    "Автобус": "avtobus"
}

# Функция для парсинга файла car_models.txt
def parse_car_models(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.readlines()

    car_data = {}
    current_brand = ''
    current_model = ''

    for line in data:
        line = line.strip()
        if line.startswith('Марка:'):
            current_brand = line.split('Марка: ')[1]
            car_data[current_brand] = {}
        elif line.startswith('Модель:'):
            current_model = line.split('Модель: ')[1]
            car_data[current_brand][current_model] = []
        elif line.startswith('Модификация:'):
            modification = line.split('Модификация: ')[1].split(', Ссылка: ')[0]
            car_data[current_brand][current_model].append(modification)
    
    return car_data

# Загружаем данные о машинах
car_models = parse_car_models('car_models.txt')  # Укажите путь к вашему файлу car_models.txt

# Функция для создания ссылки
def create_link(brand, model, modification):
    model = model.replace(" ", "-").lower()

    # Заменяем русские слова на английские
    for ru_word, en_word in translations.items():
        model = model.replace(ru_word.lower(), en_word)

    # Удаляем двойные дефисы и лишние символы для модификаций
    modification = modification.replace(",", "-").replace(" ", "-").lower()
    modification = '-'.join(filter(None, modification.split('-')))  # Удаляем лишние дефисы
    
    # Специальный случай для Land Rover Defender 110
    if brand.lower() == "land rover" and model == "defender-110":
        modification = modification.replace('ld__r', 'ldr').replace('ld__p', 'ldp')

    # Обработка дробных значений в модификации
    modification = modification.replace('.', '-')

    return f'https://www.partarium.ru/search/zapchasti-{brand}/model-{model}/{modification}/'

# Функция для парсинга названия, количества, артикула и цены детали
async def parse_part_details(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Находим все элементы <dd> с указанным классом
    part_elements = soup.find_all('dd', class_='py-2 pl-3 w-1/2 lg:w-fit lg:pl-0')
    
    # Находим элемент <a> для получения текста "Поиск"
    search_links = soup.find_all('a', class_='text-blue hover:text-blue-hover active:text-blue-active')

    parts = []
    current_part = {"Название": None, "Количество": None, "Артикул": None, "Цена": None}
    counter = 0  # Счётчик для отслеживания полей

    for element in part_elements:
        text = element.text.strip()
        
        # Заполняем поля последовательно по порядку
        if counter == 0:
            current_part["Название"] = text
        elif counter == 1:
            current_part["Количество"] = text
        elif counter == 2:
            current_part["Артикул"] = text
        elif counter == 3:
            current_part["Цена"] = text
            parts.append(current_part)
            current_part = {"Название": None, "Количество": None, "Артикул": None, "Цена": None}
        
        counter = (counter + 1) % 4  # Переходим к следующему полю (сбрасываем после 4)

    # Проверка: выводим найденные детали
    print("Parsed parts:", parts)

    # Формируем сообщение с каждой запчастью на новой строке
    if not parts:
        return "Запчасти не найдены"

    messages = []
    for part in parts:
        # Берем текст "Поиск" из последнего найденного элемента <a>
        search_text = search_links[-1].text.strip() if search_links else "Поиск"
        part_message = (
            f"🚗 Название запчасти: {part['Название']}\n"
            f"Количество: {part['Количество']}\n"
            f"Артикул: {part['Артикул']}\n"
            f"Цена: {part['Цена']}\n"
            f"{search_text}"
            f"Поиск по арикулу:@zappart_bot"
        )
        messages.append(part_message)
    
    return "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n".join(messages)



# Остальной код остается без изменений, как в вашем примере
# Функция для создания клавиатуры выбора марки
def get_brands_keyboard(car_data, page=0):
    keyboard = InlineKeyboardBuilder()
    brands = list(car_data.keys())
    for index, brand in enumerate(brands[page*5:(page+1)*5]):  # Показать по 5 брендов на странице
        keyboard.add(types.InlineKeyboardButton(text=brand, callback_data=f"brand:{page*5+index}"))

    # Добавляем кнопки для перехода по страницам
    if page > 0:
        keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_brand:{page-1}"))
    if (page+1)*5 < len(brands):
        keyboard.add(types.InlineKeyboardButton(text="➡️ Вперед", callback_data=f"next_brand:{page+1}"))

    return keyboard.as_markup()

# Функция для создания клавиатуры выбора модели
def get_models_keyboard(car_data, brand, page=0):
    keyboard = InlineKeyboardBuilder()
    models = list(car_data[brand].keys())
    for index, model in enumerate(models[page*5:(page+1)*5]):  # Показать по 5 моделей на странице
        keyboard.add(types.InlineKeyboardButton(text=model, callback_data=f"model:{brand}:{page*5+index}"))
    
    # Добавляем кнопки для перехода по страницам моделей
    if page > 0:
        keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_model:{brand}:{page-1}"))
    if (page+1)*5 < len(models):
        keyboard.add(types.InlineKeyboardButton(text="➡️ Вперед", callback_data=f"next_model:{brand}:{page+1}"))

    return keyboard.as_markup()

# Функция для создания клавиатуры выбора модификации
def get_modifications_keyboard(car_data, brand, model_index):
    keyboard = InlineKeyboardBuilder()
    models = list(car_data[brand].keys())
    modifications = car_data[brand][models[int(model_index)]]
    
    for modification in modifications:
        keyboard.add(types.InlineKeyboardButton(text=modification, callback_data=f"mod:{brand}:{model_index}:{modification}"))
    
    return keyboard.as_markup()

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Привет! Пожалуйста, выберите марку автомобиля:", reply_markup=get_brands_keyboard(car_models))

# Обработчик выбора модификации
async def handle_parts_selection(query, brand, model, modification):
    url = create_link(brand, model, modification)  # Генерация ссылки
    await query.message.answer(f"Пробуем получить данные с {url}...")  # Сообщение для отладки

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.partarium.ru/',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                await query.message.answer(f"Ошибка при запросе к {url}. Код ответа: {response.status}")
                return
            
            html_content = await response.text()

    # Используем парсер для извлечения названия и артикула
    part_message = await parse_part_details(html_content)

    # Отправляем результат пользователю
    await query.message.answer(part_message)

# Обработчик callback
@dp.callback_query(lambda c: True)
async def handle_callback(query: types.CallbackQuery):
    data = query.data.split(":")
    
    # Обработка выбора бренда
    if query.data.startswith("brand:"):
        brand_index = int(data[1])
        brand = list(car_models.keys())[brand_index]
        await query.message.edit_text(f"Выберите модель для марки {brand}:", reply_markup=get_models_keyboard(car_models, brand))
    
    # Обработка выбора модели
    elif query.data.startswith("model:"):
        if len(data) >= 3:
            brand = data[1]
            model_index = data[2]
            modifications_keyboard = get_modifications_keyboard(car_models, brand, model_index)
            
            if modifications_keyboard:
                await query.message.edit_text(f"Выберите модификацию для {brand}:", reply_markup=modifications_keyboard)
            else:
                await query.message.edit_text(f"Для {brand} нет доступных модификаций.")
        else:
            await query.message.edit_text("Ошибка: Недостаточно данных для выбора модели.")
    
    # Обработка выбора модификации
    elif query.data.startswith("mod:"):
        if len(data) >= 4:
            brand = data[1]
            model_index = data[2]
            mod = data[3]
            model = list(car_models[brand].keys())[int(model_index)]
            await handle_parts_selection(query, brand, model, mod)
        else:
            await query.message.edit_text("Ошибка: Недостаточно данных для выбора модификации.")
    
    # Обработка кнопок навигации по брендам и моделям
    elif query.data.startswith("prev_brand") or query.data.startswith("next_brand"):
        page = int(data[1])
        await query.message.edit_text("Выберите марку автомобиля:", reply_markup=get_brands_keyboard(car_models, page))

    elif query.data.startswith("prev_model") or query.data.startswith("next_model"):
        brand = data[1]
        page = int(data[2])
        await query.message.edit_text(f"Выберите модель для марки {brand}:", reply_markup=get_models_keyboard(car_models, brand, page))

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
