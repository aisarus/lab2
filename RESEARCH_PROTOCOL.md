# RESEARCH PROTOCOL — TRI·TFM v3.0

## Лаба
- Путь: `/mnt/c/Users/ariel/projects/tri_tfm_v3/` (WSL) / `C:\Users\ariel\projects\tri_tfm_v3\` (Windows)
- Скрипты: `experiment_runner.py`, `analyzer.py`
- Результаты: `results/`
- Отчёты: `reports/`

## Приоритеты

### P1: Domain Generalization
- 10 промптов: медицина, право, финансы, образование, маркетинг (по 2 на домен: factual + philosophical/ethical)
- `experiment_runner.py --repeats 3`
- Гипотеза: F-иерархия сохраняется (factual F > philosophical F) во всех доменах
- Метрика успеха: delta_F >= 0.30 в каждом домене

### P2: M-axis Validation
- 10 пар промптов (поверхностный vs глубокий на ту же тему)
- Гипотеза: delta_M > 0.15 между shallow и deep вариантами
- 20 промптов, repeats=3

### P3: Sensitivity Analysis
- Пересчёт Bal с альтернативными весами: (0.6/0.4), (0.75/0.25), (0.85/0.15), (0.5/0.5)
- На данных из P1+P2
- Корреляция Spearman между конфигурациями

### P4: Литобзор
- arxiv 2025-2026: LLM evaluation, LLM-as-judge, prompt steering
- Ключевые работы для related work секции статьи

## Правила
- Не больше 20 промптов за один запуск
- `git commit` после каждого эксперимента
- Отчёт после каждой задачи
- API ключ только из `.env`, никогда не коммитить

## Статус
- [x] P1: Domain Generalization — PASS all 5 domains, delta_F=0.496
- [x] P2: M-axis Validation — FAIL: 3/10 PASS, mean delta_M=0.073 (порог 0.15)
- [x] P3: Sensitivity Analysis — Spearman rho > 0.97 все пары, ранжирование устойчиво
- [x] P4: Литобзор — 15+ работ, позиционирование определено
