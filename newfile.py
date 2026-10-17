import asyncio
import socket
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
import aiohttp
import phonenumbers
from phonenumbers import geocoder, carrier

# ⚠️ Замените на токен вашего бота от @BotFather
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА" 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👁 **OSINT Всесильный Бот запущен.**\n\n"
        "Отправьте мне любую зацепку:\n"
        "1. **Номер телефона** (напр. `+79991112233`)\n"
        "2. **Nickname / Юзернейм** (напр. `ivanov99` или `@ivanov99`)\n"
        "3. **Автомобильный номер РФ** (напр. `А123АА77` или `у777уу777`)\n"
        "4. **E-mail** (напр. `test@mail.ru`)\n"
        "5. **Домен** (напр. `google.com`)"
    )

# 1. OSINT: Поиск по Nickname (Упрощенный аналог Sherlock)
async def check_nickname(nickname: str) -> str:
    # Удаляем @, если пользователь ввел ник как в Телеграм
    username = nickname.replace("@", "").strip()
    
    # Список сайтов для быстрой проверки существования профиля
    targets = {
        "GitHub": f"https://github.com/{username}",
        "Reddit": f"https://reddit.com{username}",
        "Steam": f"https://steamcommunity.com{username}",
        "TikTok": f"https://tiktok.com@{username}",
        "Habr": f"https://habr.com{username}"
    }
    
    found_profiles = []
    
    async with aiohttp.ClientSession() as session:
        for platform, url in targets.items():
            try:
                # Отправляем запрос, маскируясь под браузер
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                async with session.get(url, headers=headers, timeout=4) as response:
                    # Если сайт вернул 200 OK, значит профиль, скорее всего, существует
                    if response.status == 200:
                        found_profiles.append(f"• [{platform}]({url})")
            except Exception:
                continue

    if found_profiles:
        links_str = "\n".join(found_profiles)
        return (
            f"👤 **Результаты поиска никнейма `@{username}`:**\n\n"
            f"Найдены совпадения на платформах:\n{links_str}\n\n"
            f"🔗 [Глобальный поиск в Google](https://google.com\"{username}\")"
        )
    else:
        return f"🤷‍♂️ Аккаунтов с никнеймом `@{username}` на популярных сайтах не найдено (или они скрыты)."

# 2. OSINT: Анализ автомобильного номера РФ
async def check_car_plate(plate: str) -> str:
    # Приводим к верхнему регистру и заменяем латиницу на кириллицу (похожие буквы)
    plate = plate.upper().replace("A", "А").replace("B", "В").replace("E", "Е").replace("K", "К").replace("M", "М").replace("H", "Н").replace("O", "О").replace("P", "Р").replace("C", "С").replace("T", "Т").replace("X", "Х").replace("Y", "У")
    
    # Регулярное выражение для стандартных номеров РФ: Х000ХХ00 или Х000ХХ000
    match = re.search(r'([А-ЕК-МН-ПР-ТУХ])(\d{3})([А-ЕК-МН-ПР-ТУХ]{2})(\d{2,3})', plate)
    
    if not match:
        return "❌ Неверный формат автономера. Пример: `А123АА77`"
        
    number_part = f"{match.group(1)}{match.group(2)}{match.group(3)}"
    region_code = match.group(4)
    
    # Словарь популярных кодов регионов (для примера, можно расширять)
    regions = {
        "77": "г. Москва", "99": "г. Москва", "177": "г. Москва", "199": "г. Москва", "777": "г. Москва", "799": "г. Москва", "977": "г. Москва",
        "78": "г. Санкт-Петербург", "98": "г. Санкт-Петербург", "178": "г. Санкт-Петербург", "198": "г. Санкт-Петербург",
        "50": "Московская область", "90": "Московская область", "150": "Московская область", "190": "Московская область", "750": "Московская область",
        "73": "Ульяновская область", "173": "Ульяновская область",
        "16": "Республика Татарстан", "116": "Республика Татарстан", "716": "Республика Татарстан"
    }
    
    region_name = regions.get(region_code, f"Код региона {region_code} (см. полную базу ГИБДД)")
    
    report = (
        f"🚘 **Анализ госномера РФ:** `{number_part} {region_code}`\n\n"
        f"📍 **Регион регистрации:** {region_name}\n\n"
        f"🔗 *Полезные OSINT-ссылки для проверки машины:* \n"
        f"• [Поиск фото авто в Номерограм](https://nomerogram.ru{number_part}{region_code}/)\n"
        f"• [Проверка истории в Яндекс/Google](https://google.com\"{number_part}{region_code}\")"
    )
    return report

# --- Старые функции (телефон, email, домен) ---
async def check_phone(phone_text: str) -> str:
    cleaned_phone = re.sub(r'[^\d+]', '', phone_text)
    if not cleaned_phone.startswith('+') and (cleaned_phone.startswith('7') or cleaned_phone.startswith('380') or cleaned_phone.startswith('375')):
        cleaned_phone = '+' + cleaned_phone
    try:
        parsed_number = phonenumbers.parse(cleaned_phone, None)
        if not phonenumbers.is_valid_number(parsed_number):
            return "❌ Неверный формат номера телефона."
        country = geocoder.description_for_number(parsed_number, "ru")
        operator = carrier.name_for_number(parsed_number, "ru") or "Не определен"
        formatted_num = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        return (
            f"📱 **OSINT Номер телефона:** `{formatted_num}`\n"
            f"🌍 **Страна:** {country}\n📶 **Оператор:** {operator}\n\n"
            f"• [Поиск в Яндекс](https://yandex.ru{cleaned_phone})"
        )
    except Exception as e: return f"Ошибка: {str(e)}"

async def check_email(email: str) -> str:
    url = f"https://leakcheck.io{email}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("sources"):
                        return f"⚠️ **Утечки для {email}!**\nБазы: {', '.join(data.get('sources'))}"
                    return f"✅ Email `{email}` чист."
        return "🛑 Ошибка базы."
    except Exception as e: return str(e)}

async def check_domain(domain: str) -> str:
    try: return f"🔍 **IP домена {domain}:** `{socket.gethostbyname(domain)}`"
    except: return f"❌ Ошибка домена `{domain}`"

# Распределитель сообщений (Умный роутер команд)
@dp.message(F.text)
async def handle_osint(message: Message):
    text = message.text.strip()
    
    # 1. Проверка на Email
    if "@" in text and "." in text.split("@")[-1] and not text.startswith("@"):
        await message.answer("⏳ Ищу e-mail в базах утечек...")
        result = await check_email(text)
        
    # 2. Проверка на номер телефона (начинается с + или состоит в основном из цифр)
    elif re.match(r'^\+?[\d\s\-()]{10,16}\$', text):
        await message.answer("⏳ Анализирую номер телефона...")
        result = await check_phone(text)
        
    # 3. Проверка на автомобильный номер РФ (буква, 3 цифры, 2 буквы, 2-3 цифры)
    elif re.search(r'^[А-Яа-яA-Za-z]\d{3}[А-Яа-яA-Za-z]{2}\d{2,3}\$', text.replace(" ", "")):
        await message.answer("⏳ Проверяю госномер по региональным базам...")
        result = await check_car_plate(text.replace(" ", ""))
        
    # 4. Проверка на Nickname (если в начале @ или просто короткое слово без точек)
    elif text.startswith("@") or (len(text) < 30 and "." not in text and " " not in text):
        await message.answer("⏳ Пробиваю никнейм по социальным сетям...")
        result = await check_nickname(text)
        
    # 5. Всё остальное считаем доменом/сайтом
    else:
        await message.answer("⏳ Сканирую домен...")
        result = await check_domain(text)
        
    await message.answer(result, parse_mode="Markdown", disable_web_page_preview=True)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
