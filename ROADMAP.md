# Roadmap

## MVP (v0.1–v0.4) — стабильное ядро ✓

### Phase 1: Foundation (v0.1) ✓
- [x] Pydantic-модели: `VideoInfo`, `SlideSegment`, `SlidesDocument`, `SubtitleCue`
- [x] Загрузка конфига: YAML + CLI merge (pydantic + pyyaml)
- [x] CLI: `detect`, `export-md`, `debug` (typer + rich)
- [x] Логирование: loguru, двойной вывод в stderr + файл

### Phase 2: Video decoding (v0.2) ✓
- [x] OpenCV backend: `cv2.VideoCapture`, metadata, итерация кадров
- [x] Sampling по `sample_fps`, возврат `(timestamp, np.ndarray)`
- [x] Backend selection stub: `auto` → OpenCV (другие бэкенды позже)
- [x] Debug: сохранение sampled frames

### Phase 3: Slide detection (v0.3) ✓
- [x] ROI: crop `slide_roi`, mask `ignore_rois`
- [x] Feature extraction: pHash, dHash, grayscale, histogram, pixel MAE
- [x] Visual distance: взвешенная сумма (pixel MAE 80%, hash+hist 20%)
- [x] Threshold: `auto` = медиана + k×MAD, или ручной
- [x] Debounce: `min_stable_duration` — не принимать смену без стабилизации
- [x] Segment builder: интервалы, min_slide_duration, representative timestamp (80%/50%)
- [x] Dedupe: объединение соседей по visual_distance, warnings при сомнениях
- [x] Дедупликация по `representative_timestamp`, не по `vf.timestamp`

### Phase 4: Subtitles + Export (v0.4) ✓
- [x] SRT парсер (pysubs2)
- [x] VTT парсер
- [x] Overlap-алгоритм: пересечение интервалов, max overlap при конфликте
- [x] Marp Markdown export: bg-изображения, транскрипт в body, timecode в comment
- [x] Debug artifacts: `diff_scores.csv`, `timeline.png`, `contact_sheet.jpg`

### Phase 5: GPU backend ✓
- [x] PyAV backend с CUDA NVDEC hwaccel (RTX 4090)
- [ ] Decord backend
- [ ] PyNvVideoCodec backend (NVDEC)
- [x] Auto-detection: pyav → opencv
- [x] Graceful degradation: CUDA missing → WARNING + CPU

---

## Текущая версия — v0.5 (реализовано, но не задокументировано в плане)

| Фича | Статус |
|------|--------|
| PPTX export: python-pptx с картинками + speaker notes | ✓ Реализовано |
| Notes processor (basic): склейка, пунктуация, капитализация | ✓ Реализовано |
| Notes processor (llm): перефразирование через LM Studio | ✓ Реализовано (требуется LM Studio) |
| `--notes-mode basic\|llm` | ✓ Реализовано |
| `export-pptx` команда + `--export-pptx` флаг | ✓ Реализовано |
| Google Colab ноутбук с T4 GPU | ✓ Реализовано |

## Post-MVP (v0.6+)

| Версия | Фича | Статус |
|--------|------|--------|
| v0.6 | Auto slide_roi detection (наиболее стабильная область кадра) | 🟡 Планируется |
| v0.7 | OCR текста слайдов (Tesseract/PaddleOCR) | 🟡 Планируется |
| v0.8 | Review UI (Streamlit): просмотр, merge/split/delete слайдов | 🟡 Заглушка |
| v0.9 | Decord backend | 🟡 Заглушка |
| v1.0 | PyNvVideoCodec backend | 🟡 Заглушка |
| v1.1 | PDF export (через Marp CLI) | 🟡 Планируется |
| v1.2 | Batch-обработка директории с видео | 🟡 Планируется |
| v1.3 | Chapter markers из метаданных видео | 🟡 Планируется |
| v1.4 | HTML/reveal.js export | 🟡 Планируется |
| v1.5 | Поиск по слайдам и транскрипту | 🟡 Планируется |

---

## Что НЕ входит (сознательно)

- ASR / speech-to-text
- Восстановление редактируемых PPTX-объектов (таблиц, диаграмм, SmartArt)
- Облачная обработка
- Веб-сервис с пользователями и очередями
- Автоматическое скачивание видео из YouTube/Zoom/Meet
- Full редактор презентаций
- Распознавание структуры слайда (схемы, графики)
