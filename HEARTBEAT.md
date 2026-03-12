# HEARTBEAT

## Протокол (каждые 3 часа)
1. Проверить RESEARCH_PROTOCOL.md — текущий приоритет
2. Проверить `results/` — есть ли новые данные
3. Если нет активной задачи — начать следующую по приоритету
4. Отчитаться: что сделано, что дальше

## Лог
<!-- Записи добавляются сверху -->

### 2026-03-06 14:15 — P2, P3, P4 COMPLETE

**P2: M-axis Validation — FAIL (важный negative result)**
- 20 prompts x 3 repeats = 60 runs (46 успешных, 14 JSON parse errors)
- Гипотеза delta_M > 0.15: PASS только 3/10 пар
- Mean delta_M = 0.073 — judge не различает shallow vs deep промпты по M
- Вывод: M-axis нуждается в доработке rubric или judge нечувствителен к глубине
- Данные: `results/tri_tfm_gemini-2.5-flash_20260306_141031.csv`

**P3: Sensitivity Analysis — Bal устойчив**
- 4 конфигурации весов на 76 точках (P1+P2)
- Spearman rho > 0.97 между всеми парами конфигураций
- Вывод: ранжирование ответов по Bal НЕ зависит от выбора весов
- Данные: `results/p3_sensitivity_analysis.csv`

**P4: Литобзор — 15+ работ**
- 3 направления: LLM-as-Judge, Multi-axis evaluation, Prompt steering
- Ключевые gaps: single judge, no calibration correction, M-axis weakness
- Отчёт: `reports/P4_literature_review.md`

---

### 2026-03-06 14:00 — P1 COMPLETE
- Запущено 30 runs (10 prompts x 3 repeats), gemini-2.5-flash, Balance, temp=0.7
- Результат: `results/tri_tfm_gemini-2.5-flash_20260306_135909.csv`
- Отчёт: `reports/tri_tfm_20260306_140004_report.md`
- **F-иерархия: PASS во всех 5 доменах** (delta_F от 0.453 до 0.533, все >= 0.30)
- Factual F mean = 0.896, Phil/Ethical F mean = 0.400, Overall delta = 0.496
- Bal: 93% STABLE, 7% DRIFTING, mean=0.829
- Дисперсия между повторами очень низкая (sigma_F < 0.05)
- Следующая задача: P2
