# video-slide-md

Извлечение интервалов слайдов из обучающих видео, привязка к субтитрам и экспорт в Markdown-презентацию.

## Назначение

Инструмент для автоматической подготовки основы презентации из лекционного видео формата «говорящая голова + слайды на фоне».

**Главный артефакт MVP:** `video + subtitles → slides.json + slides/*.png + deck.md`

Не делает ASR, PPTX, OCR, LLM-описания — только детерминированная CV-детекция слайдов и выравнивание субтитров.

## Быстрый старт

```bash
pip install video-slide-md

video-slide-md detect lesson.mp4 \
  --subtitles lesson.srt \
  --out out/lesson_01 \
  --sample-fps 2 \
  --slide-roi 100,50,1800,1000 \
  --ignore-roi 1450,720,1900,1080 \
  --export-md \
  --debug
```

## Выход

```
out/lesson_01/
  slides/           # representative screenshots
    001.png
    002.png
  slides.json       # главный артефакт: интервалы, транскрипт, метаданные
  deck.md           # Marp-презентация
  debug/            # опционально: diff_scores.csv, timeline.png, contact_sheet.jpg
```

## Входные форматы

| Тип | Форматы |
|-----|---------|
| Видео | `.mp4`, `.mkv`, `.mov`, `.webm` |
| Субтитры | `.srt`, `.vtt` |
| Конфиг | `.yaml`, `.json`, CLI-аргументы |

## Команды

```bash
video-slide-md detect <video>    # основная: видео + субтитры → slides.json + картинки
video-slide-md export-md <json>  # slides.json → deck.md
video-slide-md debug <json>      # slides.json → отладочные артефакты
video-slide-md review <json>     # (будущее) Streamlit review UI
```

## Принципы

- **CV — первичен.** Детекция смены слайдов строго детерминированная: перцептивные хеши, SSIM, гистограммы. LLM — только для пост-MVP описаний.
- **Локальная обработка.** Видео не покидает машину. CUDA-ускорение опционально, CPU-фолбэк всегда работает.
- **Потоково.** Видео не загружается в память целиком — кадры итерируются.
- **Проверяемо.** slides.json — машиночитаемый артефакт с confidence и warnings.

## Требования

- Python 3.10+
- OpenCV (CPU), опционально: CUDA Toolkit + Decord/PyNvVideoCodec (для RTX 4090)
- Windows / Linux / macOS

## Лицензия

MIT
