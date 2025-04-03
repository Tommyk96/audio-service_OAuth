#!/bin/bash

# Создаем виртуальное окружение
python3 -m venv .venv

# Активируем его
source .venv/bin/activate

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt


# Создаем .env файл если его нет
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Файл .env создан. Пожалуйста, заполните его!"
fi

echo "Виртуальное окружение настроено. Для активации выполните:"
echo "source .venv/bin/activate"

