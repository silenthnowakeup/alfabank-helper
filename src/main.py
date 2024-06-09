from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.vectorstores import Chroma
from langchain.llms import GPT4All, LlamaCpp
import chromadb
import os
import sys
from aiogram import Bot, types, Dispatcher
import asyncio
import logging
from langchain import PromptTemplate
from chromadb.config import Settings

if not load_dotenv():
    print("Could not load .env file or it is empty. Please check if it exists and is readable.")
    exit(1)

TEMPLATE = """Используй следующий контекст, чтобы ответить на вопрос в конце. Если ты не знаешь ответ, просто скажи, что не знаешь, не пытайся придумать ответ.

{context}

Вопрос: {question}
Ответ на русском языке:"""

# Load environment variables
embeddings_model_name = os.environ.get("EMBEDDINGS_MODEL_NAME")
persist_directory = os.environ.get('PERSIST_DIRECTORY')
token = os.environ.get('ATOKEN')
model_type = os.environ.get('MODEL_TYPE')
model_path = os.environ.get('MODEL_PATH')
model_n_ctx = os.environ.get('MODEL_N_CTX')
model_n_batch = int(os.environ.get('MODEL_N_BATCH', 8))
target_source_chunks = int(os.environ.get('TARGET_SOURCE_CHUNKS', 4))

# Settings for ChromaDB
CHROMA_SETTINGS = Settings(
    persist_directory=persist_directory,
    anonymized_telemetry=False
)

embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)

# ChromaDB client
chroma_client = chromadb.PersistentClient(settings=CHROMA_SETTINGS, path=persist_directory)
db = Chroma(persist_directory=persist_directory, embedding_function=embeddings, client_settings=CHROMA_SETTINGS,
            client=chroma_client)
retriever = db.as_retriever(search_kwargs={"k": target_source_chunks})
callbacks = [StreamingStdOutCallbackHandler()]

match model_type:
    case "LlamaCpp":
        llm = LlamaCpp(model_path=model_path, max_tokens=model_n_ctx, n_batch=model_n_batch, callbacks=callbacks,
                       verbose=False)
    case "GPT4All":
        llm = GPT4All(model=model_path, max_tokens=model_n_ctx, backend='gptj', n_batch=model_n_batch,
                      callbacks=callbacks, verbose=False)
    case _default:
        raise Exception(
            f"Model type {model_type} is not supported. Please choose one of the following: LlamaCpp, GPT4All")

# QA Chain
qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type='stuff',
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={
        'prompt': PromptTemplate(
            template=TEMPLATE,
            input_variables=['context', 'question']
        ),
    },
)

# Initialize bot
bot = Bot(token)
dp = Dispatcher(bot=bot)


# Start and help command
@dp.message_handler(commands=['start', 'help'])
async def process_start_command(message: types.Message):
    await message.reply(
        "Привет! Я чатбот-помощник Альфа Банка на основе общедоступной информации с сайта. Список команд:\n"
        "/about - О боте\n"
        "/commands - Список команд\n"
        "/contact - Контактная информация\n"
        "С вопросами обращайтесь к @silenthnowakeup."
    )


# About command
@dp.message_handler(commands=['about'])
async def process_about_command(message: types.Message):
    await message.reply(
        "Я создан для помощи пользователям, предоставляя ответы на вопросы, используя доступную информацию. Просто спросите интересующий вас вопрос :)"
    )


# Commands command
@dp.message_handler(commands=['commands'])
async def process_commands_command(message: types.Message):
    await message.reply(
        "Доступные команды:\n"
        "/start, /help - Начальная информация\n"
        "/about - О боте\n"
        "/commands - Список команд\n"
        "/contact - Контактная информация"
    )


# Contact command
@dp.message_handler(commands=['contact'])
async def process_contact_command(message: types.Message):
    await message.reply(
        "Для связи с поддержкой обращайтесь к @silenthnowakeup."
    )


# Answer user queries
@dp.message_handler()
async def answer_message(message: types.Message):
    waiting_message = await message.answer("Пожалуйста, подождите, я ищу ответ...")
    try:
        ans = qa({'query': message.text})
        logging.info(ans['source_documents'])
        await bot.delete_message(chat_id=message.chat.id, message_id=waiting_message.message_id)
        await message.answer(ans['result'])
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        await bot.delete_message(chat_id=message.chat.id, message_id=waiting_message.message_id)
        await message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


# Main function to run the bot
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
