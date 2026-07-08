# video-slide-md

Извлечение интервалов слайдов из обучающих видео, привязка к субтитрам, LLM-обогащение (vision + correction) и экспорт в Markdown-презентацию (Marp) и PPTX.

## Назначение

Автоматическая подготовка основы презентации из лекционного видео формата «говорящая голова + слайды на фоне».

**Артефакт:** `video + subtitles → slides.json + slides/*.png + deck.md + deck.pptx → LLM enriched slides.json`

## Возможности

- **Детерминированная CV-детекция** смены слайдов: перцептивные хеши (pHash/dHash), пиксельный MAE, гистограммы
- **Выравнивание субтитров** (SRT/VTT) по интервалам слайдов через overlap-алгоритм
- **Дедупликация** соседних слайдов по visual_distance
- **Экспорт:** Marp Markdown (`deck.md`) и PPTX (`deck.pptx`) с полноэкранными скриншотами
- **Speaker notes** для PPTX: склейка фрагментов субтитров в чистый текст (basic) или через LLM (режим llm)
- **LLM Vision анализ** слайдов: распознавание содержимого и терминов на скриншотах через LM Studio
- **Коррекция транскрипта** LLM: исправление терминов и неточностей в расшифровке с учётом контекста слайда
- **GPU-ускорение:** PyAV + CUDA NVDEC на RTX 4090, CPU-фолбэк
- **LLM только для пост-обработки** — детекция слайдов остаётся детерминированной CV

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

# С LLM-обогащением (требуется LM Studio)
video-slide-md detect lesson.mp4 \
  --subtitles lesson.srt \
  --out out/lesson_01 \
  --llm \
  --export-pptx \
  --notes-mode llm
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
| `llm-process <json>` | slides.json → enriched slides.json (LLM vision анализ + коррекция транскрипта) |
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
| `--llm` | — | Запустить LLM vision анализ + коррекцию транскрипта после детекции |
| `--debug` | — | Артефакты отладки |

### Параметры `llm-process`

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `slides_json` | — | Путь к slides.json (обязательный аргумент) |
| `--out, -o` | (тот же файл) | Путь для enriched slides.json |
| `--slides-dir` | `рядом с json/slides` | Директория со скриншотами слайдов |
| `--model` | `gemma-4-26b-a4b-it@q4_k_xl` | Модель LLM |
| `--base-url` | `http://localhost:1234/v1` | URL LM Studio API |
| `--config, -c` | — | YAML конфиг с LLM настройками |

## Выходная структура

```
out/lesson_01/
  slides.json        # главный артефакт: интервалы + транскрипт + метаданные
  slides/            # репрезентативные скриншоты
    slide_001.png
    slide_002.png
    slide_001_analysis.json  # LLM vision description (при --llm)
    slide_002_analysis.json  # описание + термины со слайда
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
- **llm**: перефразирование каждой фразы через LM Studio (OpenAI-совместимый API). При наличии `--llm` использует vision-контекст слайда (термины, текст на слайде) для коррекции неточностей транскрипции.

## LLM-обогащение (LM Studio)

После детекции слайдов можно запустить LLM-пайплайн для vision-анализа скриншотов и коррекции транскрипта:

```bash
# Через флаг --llm в detect (единый запуск)
video-slide-md detect video.mp4 --subtitles subs.srt --llm

# Или отдельно для уже готового slides.json
video-slide-md llm-process out/slides.json --model gemma-4-26b-a4b-it@q4_k_xl
```

**Что происходит:**
1. Каждый скриншот слайда отправляется в vision-модель (gemma-4-26b или др.)
2. Модель возвращает: тему слайда, точные термины, текст на слайде, описание визуального контента
3. Описание сохраняется в `slide_*_analysis.json` и в поле `llm_description` в slides.json
4. Транскрипт каждого слайда перефразируется с учётом контекста — исправляются термины, оговорки, неточности
5. После обработки модель выгружается из VRAM

**Настройка через YAML конфиг:**
```yaml
llm:
  enabled: true
  provider: openai-compat
  base_url: "http://localhost:1234/v1"
  model: "gemma-4-26b-a4b-it@q4_k_xl"
  context_window: 60000
  temperature: 0.2
  max_tokens: 4096
  unload_when_done: true
```

**Требования:**
- Установленная [LM Studio](https://lmstudio.ai/)
- Загруженная vision-capable модель (например, Gemma 4, LLaVA, Qwen-VL)
- Запущенный локальный сервер (`http://localhost:1234`)

## Требования

- Python 3.10+
- OpenCV (CPU)
- httpx (для LLM-клиента)
- Опционально: PyAV 18+ с CUDA NVDEC (для RTX 4090)
- Windows / Linux / macOS

## GRACE

Проект следует методологии GRACE: модульная архитектура с явными контрактами, семантической разметкой кода и верификацией как обязательным артефактом. Подробнее — `docs/`.

## Разработка

Проект разработан с использованием **OpenCode** + **DeepSeek v4 Flash Free Opencode Zen** (автономный AI-агент с инструментальным доступом, генерацией кода и полным циклом разработки).

## Лицензия

MIT
