# video-slide-md

Извлечение интервалов слайдов из обучающих видео, привязка к субтитрам и экспорт в Markdown-презентацию (Marp) и PPTX.

## Назначение

Автоматическая подготовка основы презентации из лекционного видео формата «говорящая голова + слайды на фоне».

**Артефакт:** `video + subtitles → slides.json + slides/*.png + deck.md + deck.pptx`

## Возможности

- **Детерминированная CV-детекция** смены слайдов: перцептивные хеши (pHash/dHash), пиксельный MAE, гистограммы
- **Выравнивание субтитров** (SRT/VTT) по интервалам слайдов через overlap-алгоритм
- **Дедупликация** соседних слайдов по visual_distance
- **Экспорт:** Marp Markdown (`deck.md`) и PPTX (`deck.pptx`) с полноэкранными скриншотами
- **Speaker notes** для PPTX: склейка фрагментов субтитров в чистый текст (basic) или через LLM (режим llm)
- **GPU-ускорение:** PyAV + CUDA NVDEC на RTX 4090, CPU-фолбэк
- **Без LLM в критическом пути** — LLM только для пост-обработки текста заметок

## Быстрый старт

```bash
# Установка
pip install video-slide-md

# Базовый запуск
video-slide-md detect lesson.mp4 \
  --subtitles lesson.srt \
  --out out/lesson_01 \
  --sample-fps 0.5 \
  --export-md \
  --export-pptx \
  --notes-mode basic
```

## Установка (локальная разработка)

```bash
git clone https://github.com/tvoi-username/video-slide-md.git
cd video-slide-md
pip install -e .
# Или через hatch
pip install hatch
hatch shell
```

## Команды CLI

| Команда | Описание |
|---------|----------|
| `detect <video>` | Основная: детекция слайдов + субтитры → slides.json, картинки, опционально экспорт |
| `export-md <json>` | slides.json → deck.md (Marp) |
| `export-pptx <json>` | slides.json → deck.pptx (PPTX) |
| `debug <json>` | slides.json → отладочные артефакты |

### Параметры `detect`

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `--subtitles` | — | Путь к SRT/VTT |
| `--out` | `./out` | Выходная директория |
| `--sample-fps` | `0.5` | Частота сэмплирования кадров |
| `--decoder-backend` | `auto` | `auto`, `opencv`, `pyav` |
| `--slide-roi` | `auto` | ROI слайда: `auto`, `full`, `x1,y1,x2,y2` |
| `--ignore-roi` | — | Область игнорирования (вебкамера/интерфейс) |
| `--threshold` | `auto` | Порог детекции (`auto` или число) |
| `--min-slide-duration` | `10` | Минимальная длина слайда, сек |
| `--min-stable-duration` | `5` | Минимальная стабилизация, сек |
| `--no-dedupe` | — | Отключить дедупликацию |
| `--export-md` | — | Экспорт deck.md после детекции |
| `--export-pptx` | — | Экспорт deck.pptx после детекции |
| `--notes-mode` | `basic` | Режим заметок: `basic` или `llm` |
| `--debug` | — | Артефакты отладки |

## Выходная структура

```
out/lesson_01/
  slides.json        # главный артефакт: интервалы + транскрипт + метаданные
  slides/            # репрезентативные скриншоты
    slide_001.png
    slide_002.png
    ...
  deck.md            # Marp-презентация
  deck.pptx          # PPTX с картинками + speaker notes
  debug/             # опционально: diff_scores.csv, timeline.png, contact_sheet.jpg
```

## Входные форматы

| Тип | Форматы |
|-----|---------|
| Видео | `.mp4`, `.mkv`, `.mov`, `.webm` |
| Субтитры | `.srt`, `.vtt` |
| Конфиг | `.yaml`, `.json`, CLI-аргументы |

## Режимы заметок (notes)

- **basic**: склейка фрагментов субтитров, исправление пунктуации, капитализация, дедупликация повторов. Работает без внешних зависимостей.
- **llm**: перефразирование каждой фразы через LM Studio (OpenAI-совместимый API). Требует запущенного LM Studio с загруженной моделью.

## Требования

- Python 3.10+
- OpenCV (CPU)
- Опционально: PyAV 18+ с CUDA NVDEC (для RTX 4090)
- Windows / Linux / macOS

## GRACE

Проект следует методологии GRACE: модульная архитектура с явными контрактами, семантической разметкой кода и верификацией как обязательным артефактом. Подробнее — `docs/`.

## Лицензия

MIT
