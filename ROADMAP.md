# Roadmap

## MVP (v0.1–v0.4) — надёжное ядро

### Phase 1: Foundation (v0.1)
- [ ] Pydantic-модели: `VideoInfo`, `SlideSegment`, `SlidesDocument`, `SubtitleCue`
- [ ] Загрузка конфига: YAML + CLI merge (pydantic + pyyaml)
- [ ] CLI: `detect`, `export-md`, `debug` (typer + rich)
- [ ] Логирование: loguru, двойной вывод в stderr + файл

### Phase 2: Video decoding (v0.2)
- [ ] OpenCV backend: `cv2.VideoCapture`, metadata, итерация кадров
- [ ] Sampling по `sample_fps`, возврат `(timestamp, np.ndarray)`
- [ ] Backend selection stub: `auto` → OpenCV (другие бэкенды позже)
- [ ] Debug: сохранение sampled frames

### Phase 3: Slide detection (v0.3)
- [ ] ROI: crop `slide_roi`, mask `ignore_rois`
- [ ] Feature extraction: pHash, dHash, grayscale, histogram
- [ ] Visual distance: взвешенная сумма (0.4/0.3/0.2/0.1)
- [ ] Threshold: `auto` = median + k*MAD, или ручной
- [ ] Debounce: `min_stable_duration` — не принимать смену без стабилизации
- [ ] Segment builder: интервалы, min_slide_duration, representative timestamp (80%/50%)
- [ ] Dedupe: объединение соседей по pHash/SSIM, warnings при сомнениях

### Phase 4: Subtitles + Export (v0.4)
- [ ] SRT парсер (pysubs2)
- [ ] VTT парсер
- [ ] Overlap-алгоритм: пересечение интервалов, max overlap при конфликте
- [ ] Marp Markdown export: bg-изображения, транскрипт в body, timecode в comment
- [ ] Debug artifacts: `diff_scores.csv`, `timeline.png`, `contact_sheet.jpg`
- [ ] Метрики качества на synthetic dataset

### GPU backend (v0.5)
- [ ] Decord backend
- [ ] PyNvVideoCodec backend (NVDEC)
- [ ] PyAV backend (fallback)
- [ ] Auto-detection: pynv → decord → pyav → opencv
- [ ] Graceful degradation: CUDA missing → WARNING + CPU

---

## Post-MVP (v0.6+)

| Версия | Фича |
|--------|------|
| v0.6 | Auto slide_roi detection (наиболее стабильная область кадра) |
| v0.7 | OCR текста слайдов (Tesseract/PaddleOCR) |
| v0.8 | Review UI (Streamlit): просмотр, merge/split/delete слайдов |
| v0.9 | PPTX export: python-pptx с картинками + speaker notes |
| v1.0 | LLM-описания: тезисы, заголовки, speaker notes, группировка по темам |
| v1.1 | PDF export (через Marp CLI) |
| v1.2 | Batch-обработка директории с видео |
| v1.3 | Chapter markers из метаданных видео |
| v1.4 | HTML/reveal.js export |
| v1.5 | Поиск по слайдам и транскрипту |

---

## Что НЕ входит (сознательно)

- ASR / speech-to-text
- Восстановление редактируемых PPTX-объектов (таблиц, диаграмм, SmartArt)
- Облачная обработка
- Веб-сервис с пользователями и очередями
- Автоматическое скачивание видео из YouTube/Zoom/Meet
- Full редактор презентаций
- Распознавание структуры слайда (схемы, графики)
