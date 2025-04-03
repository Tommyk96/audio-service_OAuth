# Audio File Service

Сервис для загрузки и хранения аудиофайлов с авторизацией через Яндекс.

## Требования

- Docker
- Docker Compose
- Yandex OAuth приложение (для авторизации)

## Установка

Клонируйте репозиторий:

```bash
git clone https://github.com/yourusername/audio-service.git
cd audio-service
```


### Запустите сервер:

Copy

```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

```

### Запуск через Docker (рекомендуется)

Copy

```
docker-compose up -d --build
```

### Доступные endpoints

После запуска документация API будет доступна:

* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
