# Спецификация проекта: video2pptx

## 1. Назначение проекта

Нужно спроектировать и реализовать Python-приложение, которое из обучающего видео автоматически собирает основу презентации.

Входной формат видео: обучающий ролик, где на экране большую часть времени отображаются слайды, а поверх или рядом может быть говорящая голова, курсор, элементы интерфейса видеоплеера, логотипы, подписи, чат или другие динамические области.

Основная задача ПО:

1. Определить временные интервалы, в течение которых на экране находится один и тот же статичный слайд.
2. Для каждого найденного интервала сохранить representative screenshot слайда.
3. Связать каждый слайд с соответствующим фрагментом заранее подготовленного транскрипта или субтитров.
4. Сформировать структурированный JSON.
5. Сформировать Markdown-презентацию, где каждому слайду соответствует изображение слайда и описание/текст из транскрипта.

Приложение должно быть рассчитано на локальную обработку видео на компьютере пользователя. Нужно предусмотреть ускорение на NVIDIA RTX 4090 через CUDA/NVDEC, но сохранить fallback на CPU.

---

## 2. Главный принцип архитектуры

Ядро приложения не должно сразу пытаться создавать полноценный редактируемый PowerPoint.

Главный артефакт MVP:

```text
video + subtitles
  → slides/*.png
  → slides.json
  → deck.md
```

Сначала нужно добиться качественного определения слайдов, интервалов и связи с транскриптом.

Экспорт в PPTX, PDF, HTML, Marp, reveal.js и другие форматы должен быть вторичным слоем поверх `slides.json`.

---

## 3. Что не входит в MVP

На первом этапе не нужно реализовывать:

1. Автоматическое распознавание речи.
2. Полноценное восстановление редактируемого PPTX.
3. Распознавание структуры слайда: таблиц, схем, SmartArt, графиков.
4. Полную замену OCR на vision-language model.
5. Облачную обработку видео.
6. Веб-сервис с пользователями, авторизацией и очередями задач.
7. Автоматическое скачивание видео из YouTube, Zoom, Google Meet и других источников.
8. Продвинутый редактор презентаций.

На первом этапе субтитры уже есть и передаются на вход в формате SRT или VTT.

---

## 4. Основной пользовательский сценарий

Пользователь запускает команду:

```bash
video2pptx detect lesson.mp4 \
  --subtitles lesson.srt \
  --out out/lesson_01 \
  --sample-fps 2 \
  --slide-roi auto \
  --ignore-roi 1450,720,1900,1080 \
  --min-slide-duration 3.0 \
  --min-stable-duration 1.5 \
  --export-md
```

На выходе создаётся директория:

```text
out/lesson_01/
  slides/
    001.png
    002.png
    003.png

  slides.json
  deck.md

  debug/
    diff_scores.csv
    timeline.png
    contact_sheet.jpg
    sampled_frames/
```

---

## 5. Входные данные

### 5.1 Видео

Поддержать минимум:

```text
.mp4
.mkv
.mov
.webm
```

Видео может содержать:

1. Слайды на фоне.
2. Говорящую голову.
3. Курсор мыши.
4. Логотипы.
5. Элементы интерфейса проигрывателя.
6. Всплывающие уведомления.
7. Плавные анимации внутри слайда.
8. Смена слайда через резкий переход или плавный переход.
9. Повторяющиеся слайды.
10. Временные затемнения или заставки.

### 5.2 Субтитры

Поддержать:

```text
.srt
.vtt
```

Субтитры уже подготовлены пользователем. Приложение не должно на этапе MVP выполнять speech-to-text.

### 5.3 Конфигурация

Должна быть возможность передавать параметры через CLI и через YAML/JSON config.

Пример config-файла:

```yaml
video:
  sample_fps: 2
  decoder_backend: auto

detection:
  slide_roi: auto
  ignore_rois:
    - [1450, 720, 1900, 1080]
  threshold: auto
  min_slide_duration: 3.0
  min_stable_duration: 1.5
  dedupe_enabled: true

export:
  markdown_format: marp
  include_transcript_as_notes: true
  include_timecodes: true

debug:
  save_sampled_frames: false
  save_diff_scores: true
  save_timeline: true
  save_contact_sheet: true
```

---

## 6. Выходные данные

### 6.1 `slides.json`

Это главный машинно-читаемый результат.

Пример структуры:

```json
{
  "schema_version": "1.0",
  "video": {
    "path": "lesson.mp4",
    "duration": 1842.52,
    "width": 1920,
    "height": 1080,
    "fps": 30.0
  },
  "config": {
    "sample_fps": 2,
    "slide_roi": [120, 40, 1720, 980],
    "ignore_rois": [[1450, 720, 1900, 1080]],
    "min_slide_duration": 3.0,
    "min_stable_duration": 1.5
  },
  "slides": [
    {
      "index": 1,
      "start": 12.4,
      "end": 96.8,
      "duration": 84.4,
      "image": "slides/001.png",
      "representative_timestamp": 94.5,
      "hash": {
        "phash": "f0a1b2c3d4e5f6a7",
        "dhash": "a1b2c3d4e5f6a7b8"
      },
      "ocr_text": null,
      "transcript": "Фрагмент транскрипта, относящийся к этому слайду.",
      "subtitle_cues": [
        {
          "start": 13.1,
          "end": 18.7,
          "text": "Сегодня мы разберём архитектуру решения."
        }
      ],
      "confidence": 0.93,
      "warnings": []
    }
  ],
  "debug": {
    "diff_scores_csv": "debug/diff_scores.csv",
    "timeline_png": "debug/timeline.png",
    "contact_sheet": "debug/contact_sheet.jpg"
  }
}
```

### 6.2 `slides/*.png`

Для каждого найденного слайда сохранить изображение.

Требования:

1. Изображение должно соответствовать области слайда, а не обязательно всему кадру.
2. Если задан `slide_roi`, сохранять crop этой области.
3. Если `slide_roi=full`, сохранять весь кадр.
4. Представительный кадр выбирать не в момент начала интервала, а ближе к концу стабильного интервала.
5. Для слайдов с анимациями желательно сохранять финальное состояние слайда.

### 6.3 `deck.md`

Markdown-презентация.

Базовый формат — Marp.

Пример:

```markdown
---
marp: true
paginate: true
---

![bg contain](slides/001.png)

<!--
time: 00:00:12.400 - 00:01:36.800
-->

---

# Описание

Фрагмент транскрипта, относящийся к этому слайду.

---
```

Нужно предусмотреть режимы экспорта:

```text
slide-image-only
slide-image-plus-transcript
slide-image-plus-notes
slide-image-plus-summary
```

На MVP достаточно:

```text
slide-image-plus-transcript
```

---

## 7. Архитектура проекта

Рекомендуемая структура:

```text
video2pptx/
  pyproject.toml
  README.md

  src/
    video2pptx/
      __init__.py
      cli.py
      config.py
      models.py

      video_decode.py
      roi.py
      frame_features.py
      slide_detector.py
      segmenter.py
      dedupe.py
      subtitles.py
      markdown_export.py
      debug_export.py

      backends/
        __init__.py
        opencv_backend.py
        pyav_backend.py
        decord_backend.py
        pynv_backend.py

      review/
        streamlit_app.py

  tests/
    test_subtitles.py
    test_segmenter.py
    test_dedupe.py
    test_markdown_export.py
    test_synthetic_video.py

  examples/
    config.example.yaml
```

---

## 8. Модули

### 8.1 `cli.py`

CLI-интерфейс.

Команды:

```bash
video2pptx detect <video>
video2pptx export-md <slides.json>
video2pptx debug <slides.json>
video2pptx review <slides.json>
```

Минимальная обязательная команда:

```bash
video2pptx detect lesson.mp4 --subtitles lesson.srt --out out/lesson_01
```

Параметры:

```text
--subtitles PATH
--out PATH
--config PATH
--sample-fps FLOAT
--decoder-backend auto|opencv|pyav|decord|pynv
--slide-roi auto|full|x1,y1,x2,y2
--ignore-roi x1,y1,x2,y2
--threshold FLOAT|auto
--min-slide-duration FLOAT
--min-stable-duration FLOAT
--dedupe / --no-dedupe
--export-md
--debug
```

---

### 8.2 `models.py`

Описать строгие модели данных.

Можно использовать `pydantic`.

Основные модели:

```python
class VideoInfo:
    path: str
    duration: float
    width: int
    height: int
    fps: float

class Roi:
    x1: int
    y1: int
    x2: int
    y2: int

class SubtitleCue:
    start: float
    end: float
    text: str

class SlideSegment:
    index: int
    start: float
    end: float
    duration: float
    image: str
    representative_timestamp: float
    phash: str | None
    dhash: str | None
    ocr_text: str | None
    transcript: str
    subtitle_cues: list[SubtitleCue]
    confidence: float
    warnings: list[str]

class SlidesDocument:
    schema_version: str
    video: VideoInfo
    config: dict
    slides: list[SlideSegment]
    debug: dict
```

---

### 8.3 `video_decode.py`

Задача: декодировать видео и отдавать sampled frames.

Требования:

1. Поддержать выбор backend.
2. Backend `auto` должен выбирать лучший доступный вариант:

   * сначала GPU/NVDEC backend;
   * затем Decord;
   * затем PyAV;
   * затем OpenCV.
3. При недоступности GPU не падать, а переходить на CPU.
4. Возвращать кадры с timestamp.
5. Не загружать всё видео в память.
6. Обрабатывать видео потоково или батчами.

Интерфейс:

```python
@dataclass
class VideoFrame:
    timestamp: float
    image: np.ndarray

class VideoDecoder:
    def iter_frames(self, video_path: str, sample_fps: float) -> Iterator[VideoFrame]:
        ...
```

---

### 8.4 `roi.py`

Задача: определить область слайда и области, которые нужно игнорировать.

Поддерживаемые режимы:

```text
slide_roi=full
slide_roi=x1,y1,x2,y2
slide_roi=auto
```

Для MVP режим `auto` может быть простым:

1. Взять несколько кадров из видео.
2. Найти наиболее стабильную крупную прямоугольную область.
3. Исключить динамическую область говорящей головы.
4. Если auto не уверен, fallback на `full`.

Но в первой реализации допустимо честно сделать:

```text
auto = full
```

и оставить TODO с интерфейсом под будущую реализацию.

Обязательно поддержать ручной `slide_roi`, потому что это даст качество быстрее, чем сложный auto-detection.

`ignore_rois` нужны для исключения:

1. Вебкамеры.
2. Лица.
3. Чата.
4. Логотипа.
5. Таймера.
6. Панели управления плеером.
7. Области с курсором, если она предсказуема.

---

### 8.5 `frame_features.py`

Задача: извлекать признаки кадра для сравнения.

Для каждого кадра нужно считать:

1. Downscaled grayscale image.
2. Perceptual hash.
3. Difference hash.
4. Цветовую гистограмму.
5. Среднюю яркость.
6. Optional: OCR text hash.

MVP-функция:

```python
class FrameFeatures:
    timestamp: float
    phash: str
    dhash: str
    gray_small: np.ndarray
    hist: np.ndarray
```

Метрики различия:

```python
visual_distance = weighted_sum(
    phash_distance,
    dhash_distance,
    grayscale_mse,
    histogram_distance
)
```

Начальные веса:

```text
phash_distance: 0.40
dhash_distance: 0.30
grayscale_mse: 0.20
histogram_distance: 0.10
```

Порог должен быть настраиваемым.

Для `threshold=auto` можно оценивать распределение diff score по видео и выбирать порог как:

```text
median + k * MAD
```

где `MAD` — median absolute deviation.

---

### 8.6 `slide_detector.py`

Задача: найти кандидаты смены слайда.

Алгоритм MVP:

1. Пройти по sampled frames.
2. Для каждого кадра:

   * crop `slide_roi`;
   * применить маски `ignore_rois`;
   * извлечь признаки;
   * сравнить с предыдущим стабильным состоянием.
3. Если отличие выше порога — зафиксировать candidate change.
4. Не принимать candidate change сразу.
5. Проверить, что новое состояние держится минимум `min_stable_duration`.
6. Если состояние устойчиво — закрыть предыдущий сегмент и открыть новый.

Нужно избегать ложных срабатываний из-за:

1. Курсора мыши.
2. Лица преподавателя.
3. Компрессии.
4. Моргающего элемента интерфейса.
5. Временной плашки.
6. Незначительной анимации.
7. Переходного кадра между слайдами.

---

### 8.7 `segmenter.py`

Задача: превратить события смены слайда в интервалы.

Вход:

```text
timestamps of candidate changes
features
video duration
```

Выход:

```text
list[SlideSegment]
```

Требования:

1. Первый слайд начинается с `0.0`, если не задано иначе.
2. Последний слайд заканчивается на `video.duration`.
3. Сегменты короче `min_slide_duration` нужно:

   * либо объединять с соседними;
   * либо помечать как warning;
   * либо удалять, если это явно переходный мусор.
4. В каждом сегменте выбрать representative timestamp.
5. Representative timestamp брать:

   * не в самом начале;
   * не во время перехода;
   * предпочтительно в последней трети стабильного сегмента;
   * для короткого сегмента — в середине.

Пример:

```python
def choose_representative_timestamp(start, end):
    duration = end - start
    if duration >= 6:
        return start + duration * 0.80
    return start + duration * 0.50
```

---

### 8.8 `dedupe.py`

Задача: удалить или объединить дубли слайдов.

Ситуации:

1. Слайд случайно разбился на два из-за курсора.
2. Слайд изменился только из-за небольшой анимации.
3. Лектор вернулся к предыдущему слайду.
4. Один и тот же слайд встретился несколько раз в разных местах.

На MVP dedupe должен работать для соседних сегментов.

Правила:

1. Если соседние изображения имеют близкий pHash/dHash — объединить.
2. Если SSIM выше заданного порога — объединить.
3. Если OCR-текст почти одинаковый — объединить.
4. Если различие маленькое, но сегмент длинный — не удалять автоматически, а поставить warning.

Пример warning:

```json
{
  "warnings": [
    "possible_duplicate_with_previous_slide"
  ]
}
```

---

### 8.9 `subtitles.py`

Задача: прочитать SRT/VTT и привязать subtitle cues к слайдам.

Правило пересечения:

```text
slide interval: [slide_start, slide_end)
cue interval:   [cue_start, cue_end)

overlap = max(0, min(slide_end, cue_end) - max(slide_start, cue_start))
```

Если `overlap > 0`, cue относится к слайду.

Если cue пересекает несколько слайдов:

1. Назначить cue тому слайду, где overlap максимальный.
2. В debug можно сохранить информацию о пересечении.
3. Не дублировать cue по умолчанию.

Требования:

1. Поддержать SRT.
2. Поддержать VTT.
3. Сохранять исходный текст cue.
4. Убирать технические переносы строк.
5. Не ломать русский текст.
6. Сохранять порядок фраз.

---

### 8.10 `markdown_export.py`

Задача: сформировать Markdown-презентацию.

Основной формат — Marp.

Минимальный экспорт:

```markdown
---
marp: true
paginate: true
---

![bg contain](slides/001.png)

<!--
time: 00:00:12.400 - 00:01:36.800
-->

---

# Транскрипт

Текст, относящийся к слайду.

---
```

Нужно предусмотреть режимы:

```text
image_as_background=true|false
transcript_location=notes|body|comment
include_timecodes=true|false
```

Для MVP можно реализовать:

```text
image_as_background=true
transcript_location=body
include_timecodes=true
```

---

### 8.11 `debug_export.py`

Задача: сохранить отладочные артефакты.

Минимум:

```text
debug/diff_scores.csv
debug/timeline.png
debug/contact_sheet.jpg
```

`diff_scores.csv`:

```csv
timestamp,score,phash_distance,dhash_distance,mse,hist_distance,is_change
12.0,0.03,1,2,0.01,0.02,false
12.5,0.87,22,20,0.55,0.70,true
```

`timeline.png`:

* горизонтальная шкала видео;
* отмечены смены слайдов;
* показан diff score;
* показан threshold.

`contact_sheet.jpg`:

* сетка всех найденных слайдов;
* под каждым слайдом номер и таймкод.

---

## 9. CUDA и RTX 4090

Приложение должно быть спроектировано так, чтобы эффективно использовать RTX 4090, но не зависеть жёстко от неё.

### 9.1 Где использовать GPU

1. Аппаратное декодирование видео через NVDEC.
2. Batch-обработка кадров.
3. Возможный OCR.
4. Возможные embedding/vision-модели на следующих этапах.

### 9.2 Backend-и декодирования

Поддержать архитектурно:

```text
pynv     - NVIDIA PyNvVideoCodec / NVDEC
decord   - Decord with GPU support
pyav     - PyAV / FFmpeg
opencv   - OpenCV fallback
```

Логика `auto`:

```text
1. попробовать pynv
2. если недоступен — decord
3. если недоступен — pyav
4. если недоступен — opencv
```

Ошибки GPU backend не должны останавливать выполнение. Нужно логировать warning и переключаться на CPU.

---

## 10. Логирование

Использовать стандартный `logging`.

Уровни:

```text
INFO    - основные этапы обработки
WARNING - fallback, сомнительные сегменты, короткие слайды
ERROR   - невозможность обработать файл
DEBUG   - подробная информация по кадрам и score
```

Пример логов:

```text
INFO  Loaded video lesson.mp4 duration=1842.52 width=1920 height=1080 fps=30
INFO  Decoder backend selected: pynv
INFO  Sampling frames at 2.0 fps
INFO  Slide ROI: [120, 40, 1720, 980]
INFO  Detected 42 slide segments
WARNING Segment 17 is too short: 1.2s
INFO  Saved slides.json
INFO  Saved deck.md
```

---

## 11. Тестирование

### 11.1 Unit tests

Обязательные тесты:

1. Парсинг SRT.
2. Парсинг VTT.
3. Расчёт overlap subtitle cue со slide interval.
4. Выбор representative timestamp.
5. Объединение коротких сегментов.
6. Dedupe похожих соседних слайдов.
7. Markdown export.
8. JSON schema validation.

### 11.2 Synthetic video tests

Нужно сгенерировать искусственные видео для тестов.

Сценарии:

1. Видео из 3 статичных слайдов.
2. Видео с вебкамерой в углу.
3. Видео с мигающим курсором.
4. Видео с плавной анимацией на слайде.
5. Видео с кратким переходным кадром.
6. Видео с повторяющимся слайдом.
7. Видео с чёрной заставкой в начале.
8. Видео с очень коротким слайдом.

Для synthetic tests можно генерировать кадры через OpenCV.

### 11.3 Метрики качества

Считать:

```text
missed_slide_rate
false_split_rate
duplicate_rate
timestamp_error_seconds
```

Минимальные критерии MVP на synthetic dataset:

```text
missed_slide_rate <= 5%
false_split_rate <= 10%
timestamp_error_seconds <= 1.5 sec при sample_fps=2
```

---

## 12. Review UI

Review UI не входит в ядро, но нужно заложить под него структуру.

Минимальный будущий интерфейс:

```text
[thumbnail] [start - end] [duration] [transcript preview]
[merge previous] [split] [delete] [edit time] [edit transcript]
```

Рекомендуемый стек:

```text
Streamlit
или
Gradio
```

На MVP можно не реализовывать UI, но `slides.json` должен быть таким, чтобы его было удобно редактировать вручную или через UI.

---

## 13. Этапы реализации

### Этап 1. Каркас проекта

Сделать:

1. `pyproject.toml`.
2. CLI.
3. Pydantic-модели.
4. Загрузка config.
5. Логирование.
6. Пустые backend-интерфейсы.

Критерий готовности:

```bash
video2pptx --help
video2pptx detect --help
```

работают.

---

### Этап 2. Декодирование видео

Сделать:

1. OpenCV backend.
2. Получение video metadata.
3. Sampling кадров по `sample_fps`.
4. Возврат timestamp + frame.

Критерий готовности:

```bash
video2pptx detect lesson.mp4 --out out/test --debug
```

создаёт sampled debug frames.

---

### Этап 3. Детекция слайдов

Сделать:

1. Crop по `slide_roi`.
2. Mask по `ignore_rois`.
3. Feature extraction.
4. Расчёт diff score.
5. Threshold.
6. Debounce.
7. Segment generation.
8. Representative screenshot.

Критерий готовности:

```text
slides/*.png
slides.json
debug/diff_scores.csv
```

создаются.

---

### Этап 4. Привязка субтитров

Сделать:

1. SRT parser.
2. VTT parser.
3. Alignment subtitle cues к слайдам.
4. Запись transcript в `slides.json`.

Критерий готовности:

```text
slides.json содержит transcript для каждого слайда
```

---

### Этап 5. Markdown export

Сделать:

1. Marp export.
2. Timecodes.
3. Изображение слайда.
4. Транскрипт.

Критерий готовности:

```text
deck.md создаётся и открывается как Markdown-презентация
```

---

### Этап 6. Debug output

Сделать:

1. `timeline.png`.
2. `contact_sheet.jpg`.
3. Расширенный `diff_scores.csv`.

Критерий готовности:

```text
по debug-артефактам можно понять, где и почему были найдены смены слайдов
```

---

### Этап 7. GPU backend

Сделать после рабочего CPU MVP.

1. Добавить Decord backend.
2. Добавить NVIDIA/PyNvVideoCodec backend, если доступен.
3. Реализовать `decoder_backend=auto`.
4. Добавить fallback на CPU.

Критерий готовности:

```text
на машине с RTX4090 используется GPU backend,
на машине без GPU приложение работает через CPU
```

---

## 14. Критерии приёмки MVP

MVP считается готовым, если:

1. Приложение принимает видео и SRT/VTT.
2. Приложение создаёт `slides.json`.
3. Приложение сохраняет изображения найденных слайдов.
4. Приложение определяет интервалы слайдов с приемлемой точностью.
5. Приложение связывает транскрипт со слайдами.
6. Приложение создаёт `deck.md`.
7. Есть debug-артефакты для проверки качества.
8. Можно вручную задать `slide_roi` и `ignore_rois`.
9. Приложение не падает при отсутствии CUDA.
10. Есть unit tests для ключевой логики.

---

## 15. Важные инженерные требования

1. Не хранить всё видео в памяти.
2. Обрабатывать видео потоково.
3. Все пути должны быть кроссплатформенными.
4. Поддержать Windows.
5. Поддержать кириллицу в путях и субтитрах.
6. Не делать жёсткой зависимости от CUDA.
7. Не смешивать ядро обработки и UI.
8. Не смешивать детекцию слайдов и генерацию описаний LLM.
9. Не использовать LLM для определения смены слайдов в MVP.
10. Все эвристики должны быть настраиваемыми.

---

## 16. Будущие расширения

После MVP можно добавить:

1. OCR текста слайдов.
2. Автоматическое определение `slide_roi`.
3. Автоматическое определение области говорящей головы.
4. Review UI.
5. Экспорт в PPTX.
6. Экспорт в PDF.
7. Генерацию кратких тезисов по каждому слайду через LLM.
8. Группировку слайдов по темам.
9. Поиск по слайдам и транскрипту.
10. Извлечение оглавления видео.
11. Сборку полноценного учебного конспекта.
12. Поддержку batch-обработки директории с видео.
13. Поддержку chapter markers.
14. Поддержку HTML/reveal.js.
15. Распознавание слайдов, которые повторяются в разных местах видео.

---

## 17. Разделение ответственности между алгоритмами и LLM

Важно:

Детекция слайдов должна быть детерминированной CV-задачей.

LLM можно использовать только после того, как слайды и интервалы уже найдены.

Правильное разделение:

```text
Computer Vision:
  - найти интервалы;
  - сохранить картинки;
  - удалить дубли;
  - посчитать confidence;
  - подготовить debug.

Subtitle alignment:
  - привязать текст по timestamp.

LLM:
  - сделать краткое описание слайда;
  - выделить тезисы;
  - сформировать speaker notes;
  - сделать учебный конспект;
  - предложить заголовок слайда;
  - сгруппировать слайды по темам.
```

Нельзя использовать LLM как основной механизм определения смены слайда.

---

## 18. Рекомендуемые зависимости

Минимальный MVP:

```toml
opencv-python
numpy
pydantic
typer
rich
pysubs2
pillow
imagehash
scikit-image
matplotlib
pyyaml
```

Дополнительно:

```toml
decord
av
torch
pynvvideocodec
streamlit
python-pptx
```

Зависимости GPU должны быть optional.

---

## 19. Пример конечного результата

После запуска:

```bash
video2pptx detect lesson.mp4 \
  --subtitles lesson.srt \
  --out out/lesson_01 \
  --sample-fps 2 \
  --slide-roi 100,50,1800,1000 \
  --ignore-roi 1450,720,1900,1080 \
  --export-md \
  --debug
```

Должно получиться:

```text
out/lesson_01/
  slides/
    001.png
    002.png
    003.png

  slides.json
  deck.md

  debug/
    diff_scores.csv
    timeline.png
    contact_sheet.jpg
```

`slides.json` содержит интервалы:

```json
[
  {
    "index": 1,
    "start": 0.0,
    "end": 42.5,
    "image": "slides/001.png",
    "transcript": "..."
  },
  {
    "index": 2,
    "start": 42.5,
    "end": 118.0,
    "image": "slides/002.png",
    "transcript": "..."
  }
]
```

`deck.md` содержит Markdown-презентацию, которую можно открыть, проверить, отредактировать и затем преобразовать в PDF/PPTX через отдельный инструмент.

---

## 20. Главная цель агента

Сначала реализовать надёжное ядро:

```text
video + subtitles → slides.json + slides/*.png + deck.md
```

Не уходить в лишнюю сложность.

Не начинать с PowerPoint.

Не начинать с OCR.

Не начинать с LLM.

Не начинать с UI.

Сначала нужен проверяемый, воспроизводимый, отлаживаемый pipeline определения слайдов и интервалов.

После этого можно расширять проект экспортёрами, OCR, LLM-описанием, review-интерфейсом и генерацией полноценной презентации.
