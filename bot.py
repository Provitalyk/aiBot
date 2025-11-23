import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import AsyncOpenAI
from dotenv import load_dotenv


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


bot = Bot(token=os.getenv("API_TOKEN"))
dp = Dispatcher()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Словарь для хранения истории диалогов
user_contexts = {}


def get_user_context(user_id: int) -> list:
    """Возвращает контекст диалога для пользователя или пустой список."""
    return user_contexts.get(user_id, [])

def update_user_context(user_id: int, user_msg: str, assistant_msg: str):
    """Добавляет пару сообщений в контекст пользователя."""
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    user_contexts[user_id].append({"role": "user", "content": user_msg})
    user_contexts[user_id].append({"role": "assistant", "content": assistant_msg})

def clear_user_context(user_id: int):
    """Очищает контекст диалога."""
    user_contexts[user_id] = []

@dp.message(Command("start"))
async def start(message: types.Message):
    clear_user_context(message.from_user.id)
    await message.reply(
        "Привет! Я бот с ChatGPT.\n"
        "Отправь мне текст — я сгенерирую ответ.\n\n"
        "Команды:\n"
        "/start — начать новый диалог\n"
        "/help — помощь\n\n"
        "Для нового диалога нажмите кнопку ниже:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Новый запрос")]
            ],
            resize_keyboard=True
        )
    )

@dp.message(Command("help"))
async def help(message: types.Message):
    await message.reply(
        "Я использую ChatGPT для генерации ответов.\n"
        "Все сообщения сохраняются в контексте диалога.\n"
        "Чтобы начать заново — /start или кнопка «Новый запрос»."
    )

@dp.message(F.text == "Новый запрос")
async def new_query(message: types.Message):
    clear_user_context(message.from_user.id)
    await message.reply("Контекст диалога очищен. Отправьте новый запрос.")

@dp.message(F.text)
async def chat_with_gpt(message: types.Message):
    user_id = message.from_user.id
    user_input = message.text

    context = get_user_context(user_id)

    try:
        # Отправляем запрос в OpenAI с контекстом
        response = await client.chat.completions.create(
            model="gpt-4o",  # или "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "Ты — полезный ассистент. Отвечай кратко и по делу."},
                *context,
                {"role": "user", "content": user_input}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        assistant_reply = response.choices[0].message.content

        update_user_context(user_id, user_input, assistant_reply)

        await message.reply(assistant_reply)

    except Exception as e:
        logger.error(f"Ошибка при обращении к OpenAI: {e}")
        await message.reply("Произошла ошибка при генерации ответа. Попробуйте ещё раз.")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
