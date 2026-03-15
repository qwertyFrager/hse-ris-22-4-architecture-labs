# Лабораторная работа №3
## Тема: Использование принципов проектирования на уровне методов и классов
### Цель работы
Получить опыт проектирования и реализации модулей с использованием принципов KISS, YAGNI, DRY, SOLID и др.

**Выбранный вариант использования:**  
Запустить анализ рекламных кампаний за выбранный период и получить список проблем и рекомендаций.

---

## Диаграмма контейнеров (C4)
На диаграмме показан общий набор контейнеров, где далее детализируется контейнер **Backend API**.

![Диаграмма контейнеров](lab3-1.png)

**Кратко:**
- Web UI обращается к Backend API по HTTPS.
- Backend API пишет/читает данные в PostgreSQL.
- Фоновая обработка выполняется Worker’ом, задачи передаются через очередь (Redis/RabbitMQ).
- Worker ходит во внешние API Яндекс Директ.

---

## Диаграмма компонентов (C4)
Ниже компоненты контейнера **Backend API**, для которых далее приводится код.

![Диаграмма компонентов](lab3-2.png)

**Компоненты:**
- `CampaignStatsService` — получение статистики (через репозиторий / адаптер)
- `KpiCalculator` — расчет KPI
- `RulesEngine` — проверка правил
- `RecommendationService` — формирование рекомендаций
- `ReportController` — API для UI
- `Repositories` — слой доступа к БД

---

## Диаграмма последовательностей
Диаграмма показывает взаимодействие компонентов при запуске анализа кампаний и получении рекомендаций.

![Диаграмма последовательностей](lab3-3.png)

**Кратко:**
Диаграмма последовательностей отражает сценарий запуска анализа рекламной кампании и последующего получения рекомендаций пользователем. Сначала маркетолог через интерфейс Web UI инициирует анализ за выбранный период. Запрос передаётся в ReportController, который создаёт запись о запуске анализа в базе данных и публикует задачу в очередь. После этого пользователь получает в интерфейсе статус о том, что анализ запущен и находится в обработке.

Далее выполняется фоновая обработка: Worker/Scheduler получает задачу из очереди, запрашивает статистику кампании из Yandex Direct API, передаёт данные в RecommendationService для расчёта метрик и формирования рекомендаций, после чего сохраняет результаты в PostgreSQL и обновляет статус анализа на завершённый.

На заключительном этапе пользователь открывает отчёт, Web UI отправляет запрос в ReportController, который загружает сохранённые рекомендации из базы данных и возвращает их в интерфейс для отображения таблицы KPI и рекомендаций.

---

## Модель БД (UML диаграмма классов)
Сущности хранилища данных. Здесь показана логическая модель.

![Модель БД (UML)](lab3-4.png)

**Сущности:**
1) `User` — пользователи системы  
2) `AdAccount` — подключенные рекламные аккаунты  
3) `Campaign` — кампании Яндекс Директ (минимальные поля)  
4) `AnalysisRun` — запуск анализа (период, статус)  
5) `MetricSnapshot` — рассчитанные KPI (по кампании и запуску)  
6) `Recommendation` — рекомендации и причины (по кампании и запуску)  

---

## Применение основных принципов разработки
Ниже — фрагменты кода (сервер + простой клиент), с пояснениями как соблюдены KISS, YAGNI, DRY и SOLID.

### 1) Сервер (FastAPI): запуск анализа и получение отчета
**KISS:** 2 эндпоинта и простой формат DTO
**YAGNI:** без сложной авторизации и без real-time оптимизации ставок
**DRY:** вынесены повторяющиеся преобразования в функции/классы 
**SOLID:** сервисы разделены, зависимости передаются через интерфейсы

```python
# app/api.py
from abc import ABC, abstractmethod
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from uuid import uuid4

app = FastAPI()


# =========================================================
# DTO / API models
# KISS:
# Для MVP оставлены только необходимые модели:
# - запрос на запуск анализа
# - ответ с run_id
# - DTO рекомендации
# =========================================================
class RunRequest(BaseModel):
    account_id: str
    date_from: str
    date_to: str


class RecommendationDto(BaseModel):
    campaign_id: str
    rule: str
    message: str
    evidence: dict


class RunResponse(BaseModel):
    run_id: str


# =========================================================
# Абстракции
# DIP:
# Бизнес-логика зависит не от конкретных реализаций,
# а от абстракций.
# =========================================================
class StatsProvider(ABC):
    @abstractmethod
    def fetch_campaign_stats(self, account_id: str, date_from: str, date_to: str) -> list:
        pass


class RunRepository(ABC):
    @abstractmethod
    def save_run(self, run_id: str, payload: dict) -> None:
        pass


class RecommendationRepository(ABC):
    @abstractmethod
    def save_recommendations(self, run_id: str, recos: list) -> None:
        pass

    @abstractmethod
    def get_recommendations(self, run_id: str) -> list:
        pass


class Rule(ABC):
    """
    OCP:
    Каждое правило вынесено в отдельный класс.
    Чтобы добавить новое правило, не нужно менять RulesEngine,
    достаточно реализовать новый Rule и передать его в список.
    """
    @abstractmethod
    def check(self, stats: dict, kpi: dict) -> List[dict]:
        pass


# =========================================================
# Реализации инфраструктуры
# YAGNI:
# Для MVP не подключаем реальный Yandex Direct API и БД.
# Вместо этого используем заглушки и in-memory хранилище.
# =========================================================
class InMemoryRepo(RunRepository, RecommendationRepository):
    def __init__(self):
        self.runs = {}
        self.recos = {}

    def save_run(self, run_id: str, payload: dict) -> None:
        self.runs[run_id] = payload

    def save_recommendations(self, run_id: str, recos: list) -> None:
        self.recos[run_id] = recos

    def get_recommendations(self, run_id: str) -> list:
        return self.recos.get(run_id, [])


class FakeStatsProvider(StatsProvider):
    def fetch_campaign_stats(self, account_id: str, date_from: str, date_to: str) -> list:
        return [
            {"campaign_id": "c1", "impressions": 1000, "clicks": 10, "spend": 1200, "conversions": 0},
            {"campaign_id": "c2", "impressions": 5000, "clicks": 200, "spend": 8000, "conversions": 12},
            {"campaign_id": "c3", "impressions": 3000, "clicks": 15, "spend": 2500, "conversions": 1},
        ]


# =========================================================
# Бизнес-логика
# SRP:
# Каждый класс отвечает только за одну задачу.
# =========================================================
class KpiCalculator:
    """
    SRP:
    Этот класс отвечает только за расчет KPI.
    Он не сохраняет данные, не работает с API и не применяет правила.
    """
    def calc(self, row: dict) -> dict:
        clicks = row["clicks"]
        imps = row["impressions"]
        spend = row["spend"]
        conv = row.get("conversions", 0)

        ctr = (clicks / imps) if imps else 0
        cpc = (spend / clicks) if clicks else 0
        cpa = (spend / conv) if conv else None

        return {
            "ctr": ctr,
            "cpc": cpc,
            "cpa": cpa,
        }


class SpendWithoutConversionsRule(Rule):
    """
    SRP:
    Это правило отвечает только за одну конкретную проверку:
    расход есть, а конверсий нет.
    """
    def check(self, stats: dict, kpi: dict) -> List[dict]:
        if stats["spend"] > 1000 and stats.get("conversions", 0) == 0:
            return [{
                "rule": "SPEND_WITHOUT_CONVERSIONS",
                "message": "Высокий расход при нулевых конверсиях — проверить ключевые фразы, минус-слова и посадочную страницу.",
                "evidence": {
                    "spend": stats["spend"],
                    "conversions": stats.get("conversions", 0)
                }
            }]
        return []


class LowCtrRule(Rule):
    """
    Еще одно независимое правило.
    """
    def check(self, stats: dict, kpi: dict) -> List[dict]:
        if kpi["ctr"] < 0.01:
            return [{
                "rule": "LOW_CTR",
                "message": "Низкий CTR — проверить релевантность объявлений, заголовков и ключевых фраз.",
                "evidence": {
                    "ctr": kpi["ctr"]
                }
            }]
        return []


class HighCpaRule(Rule):
    """
    Новое правило можно просто добавить в список правил.
    Это и есть наглядная демонстрация OCP.
    """
    def check(self, stats: dict, kpi: dict) -> List[dict]:
        cpa = kpi.get("cpa")
        if cpa is not None and cpa > 2000:
            return [{
                "rule": "HIGH_CPA",
                "message": "Высокая стоимость привлечения — рекомендуется проверить ставки, аудитории и посадочную страницу.",
                "evidence": {
                    "cpa": cpa
                }
            }]
        return []


class RulesEngine:
    """
    DRY:
    Вся логика запуска набора правил собрана в одном месте.
    Не нужно дублировать одинаковые if/for по всему сервису.

    OCP:
    Движок не зависит от конкретных правил.
    Ему передают список объектов, реализующих интерфейс Rule.
    """
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def check(self, stats: dict, kpi: dict) -> List[dict]:
        issues = []
        for rule in self.rules:
            issues.extend(rule.check(stats, kpi))
        return issues


class RecommendationService:
    """
    SRP:
    Сервис координирует сценарий анализа:
    - получает статистику
    - считает KPI
    - применяет правила
    - сохраняет результат

    DIP:
    Сервис зависит от абстракций StatsProvider, RunRepository,
    RecommendationRepository и RulesEngine, а не от конкретных
    API-клиентов или БД.

    LSP:
    Любую реализацию StatsProvider или Repository можно подставить
    вместо текущей, не меняя код сервиса, если она соблюдает контракт.
    """
    def __init__(
        self,
        provider: StatsProvider,
        run_repo: RunRepository,
        reco_repo: RecommendationRepository,
        kpi_calc: KpiCalculator,
        rules_engine: RulesEngine,
    ):
        self.provider = provider
        self.run_repo = run_repo
        self.reco_repo = reco_repo
        self.kpi_calc = kpi_calc
        self.rules_engine = rules_engine

    def run_analysis(self, account_id: str, date_from: str, date_to: str) -> str:
        run_id = str(uuid4())

        self.run_repo.save_run(run_id, {
            "account_id": account_id,
            "date_from": date_from,
            "date_to": date_to,
            "status": "DONE"
        })

        stats_rows = self.provider.fetch_campaign_stats(account_id, date_from, date_to)

        recos = []
        for row in stats_rows:
            kpi = self.kpi_calc.calc(row)
            issues = self.rules_engine.check(row, kpi)

            for issue in issues:
                recos.append({
                    "campaign_id": row["campaign_id"],
                    "rule": issue["rule"],
                    "message": issue["message"],
                    "evidence": {
                        **issue["evidence"],
                        "kpi": kpi
                    },
                })

        self.reco_repo.save_recommendations(run_id, recos)
        return run_id

    def get_report(self, run_id: str) -> list:
        return self.reco_repo.get_recommendations(run_id)


# =========================================================
# Конфигурация зависимостей
# DIP:
# Конкретные реализации создаются на уровне конфигурации,
# а не внутри RecommendationService.
# =========================================================
repo = InMemoryRepo()
provider = FakeStatsProvider()
kpi_calc = KpiCalculator()
rules_engine = RulesEngine([
    SpendWithoutConversionsRule(),
    LowCtrRule(),
    HighCpaRule(),
])

service = RecommendationService(
    provider=provider,
    run_repo=repo,
    reco_repo=repo,
    kpi_calc=kpi_calc,
    rules_engine=rules_engine,
)


# =========================================================
# API layer
# SoC:
# Контроллеры не содержат бизнес-логику расчета KPI и правил,
# а только принимают запрос и вызывают сервис.
# =========================================================
@app.post("/analysis/run", response_model=RunResponse)
def start_analysis(req: RunRequest):
    run_id = service.run_analysis(req.account_id, req.date_from, req.date_to)
    return RunResponse(run_id=run_id)


@app.get("/analysis/{run_id}/recommendations", response_model=List[RecommendationDto])
def get_recommendations(run_id: str):
    recos = service.get_report(run_id)
    if not recos:
        raise HTTPException(status_code=404, detail="Результаты не найдены (проверьте run_id).")
    return recos
```

## Принципы разработки, реализованные в прототипе системы

Ниже приведено описание ключевых принципов проектирования и разработки, реализованных в прототипе системы поддержки принятия решений для оптимизации рекламных кампаний в Яндекс Директ. Для каждого принципа показано, как он проявляется в коде, и приведены соответствующие фрагменты реализации.

---

## KISS

Принцип **KISS (Keep It Simple, Stupid)** означает, что система должна оставаться максимально простой и решать только основные задачи без лишнего усложнения.

В данном примере принцип KISS реализован следующим образом:

- в системе предусмотрены только два основных пользовательских действия: запуск анализа и получение рекомендаций;
- API содержит только два конечных маршрута;
- используются только минимально необходимые модели данных: запрос на запуск анализа, ответ с `run_id` и DTO рекомендации.

Это делает архитектуру понятной, компактной и удобной для дальнейшего развития.

### Проявление в коде

```python
@app.post("/analysis/run", response_model=RunResponse)
def start_analysis(req: RunRequest):
    run_id = service.run_analysis(req.account_id, req.date_from, req.date_to)
    return RunResponse(run_id=run_id)

@app.get("/analysis/{run_id}/recommendations", response_model=List[RecommendationDto])
def get_recommendations(run_id: str):
    recos = service.get_report(run_id)
    if not recos:
        raise HTTPException(status_code=404, detail="Результаты не найдены (проверьте run_id).")
    return recos
```

Простыми словами: пользователь может сделать только два понятных действия — запустить анализ и получить результат.

---

## YAGNI

Принцип **YAGNI (You Aren’t Gonna Need It)** означает, что в систему не следует заранее добавлять функциональность, которая пока не нужна.

В прототипе этот принцип реализован тем, что вместо реальной интеграции с API Яндекс Директа и полноценной базы данных используются:

* `FakeStatsProvider` — заглушка для получения статистики;
* `InMemoryRepo` — простое хранилище в памяти.

Это позволяет сосредоточиться на проверке основной бизнес-идеи: можно ли на основе статистики и набора правил формировать рекомендации.

### Проявление в коде

```python
class FakeStatsProvider(StatsProvider):
    def fetch_campaign_stats(self, account_id: str, date_from: str, date_to: str) -> list:
        return [
            {"campaign_id": "c1", "impressions": 1000, "clicks": 10, "spend": 1200, "conversions": 0},
            {"campaign_id": "c2", "impressions": 5000, "clicks": 200, "spend": 8000, "conversions": 12},
            {"campaign_id": "c3", "impressions": 3000, "clicks": 15, "spend": 2500, "conversions": 1},
        ]
```

Простыми словами: пока не нужен реальный внешний API, достаточно заглушки, чтобы проверить работоспособность логики.

---

## DRY

Принцип **DRY (Don’t Repeat Yourself)** означает, что одинаковая логика не должна дублироваться в нескольких местах.

В данном примере DRY реализован за счет того, что:

* расчет KPI вынесен в отдельный класс `KpiCalculator`;
* запуск набора правил централизован в `RulesEngine`;
* каждое правило описывается один раз и затем переиспользуется движком правил.

### Проявление в коде

```python
class KpiCalculator:
    def calc(self, row: dict) -> dict:
        clicks = row["clicks"]
        imps = row["impressions"]
        spend = row["spend"]
        conv = row.get("conversions", 0)

        ctr = (clicks / imps) if imps else 0
        cpc = (spend / clicks) if clicks else 0
        cpa = (spend / conv) if conv else None

        return {
            "ctr": ctr,
            "cpc": cpc,
            "cpa": cpa,
        }
```

```python
class RulesEngine:
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def check(self, stats: dict, kpi: dict) -> List[dict]:
        issues = []
        for rule in self.rules:
            issues.extend(rule.check(stats, kpi))
        return issues
```

Простыми словами: расчет метрик и логика применения правил написаны один раз в одном месте и не копируются по проекту.

---

## SOLID

### SRP — Single Responsibility Principle

Принцип **единственной ответственности** означает, что каждый класс должен отвечать только за одну задачу.

В прототипе это реализовано следующим образом:

* `KpiCalculator` отвечает только за расчет KPI;
* `SpendWithoutConversionsRule`, `LowCtrRule`, `HighCpaRule` отвечают только за отдельные правила;
* `RulesEngine` отвечает только за запуск набора правил;
* `RecommendationService` координирует сценарий анализа;
* `FakeStatsProvider` получает статистику;
* `InMemoryRepo` хранит данные.

### Проявление в коде

```python
class KpiCalculator:
    def calc(self, row: dict) -> dict:
        ...
```

```python
class LowCtrRule(Rule):
    def check(self, stats: dict, kpi: dict) -> List[dict]:
        ...
```

```python
class RecommendationService:
    def run_analysis(self, account_id: str, date_from: str, date_to: str) -> str:
        ...
```

Простыми словами: каждый класс делает одну понятную вещь, поэтому код легче читать, тестировать и изменять.

---

### DIP — Dependency Inversion Principle

Принцип **инверсии зависимостей** означает, что высокоуровневая бизнес-логика должна зависеть не от конкретных реализаций, а от абстракций.

В данном случае `RecommendationService` не создает внутри себя конкретные классы работы с API или хранилищем, а получает их извне через конструктор. Это позволяет подменять реализации без изменения логики сервиса.

### Проявление в коде

```python
class RecommendationService:
    def __init__(
        self,
        provider: StatsProvider,
        run_repo: RunRepository,
        reco_repo: RecommendationRepository,
        kpi_calc: KpiCalculator,
        rules_engine: RulesEngine,
    ):
        self.provider = provider
        self.run_repo = run_repo
        self.reco_repo = reco_repo
        self.kpi_calc = kpi_calc
        self.rules_engine = rules_engine
```

```python
repo = InMemoryRepo()
provider = FakeStatsProvider()
kpi_calc = KpiCalculator()
rules_engine = RulesEngine([
    SpendWithoutConversionsRule(),
    LowCtrRule(),
    HighCpaRule(),
])

service = RecommendationService(
    provider=provider,
    run_repo=repo,
    reco_repo=repo,
    kpi_calc=kpi_calc,
    rules_engine=rules_engine,
)
```

Простыми словами: сервис анализа зависит не от «конкретной базы» или «конкретного API», а от общего контракта.

---

### OCP — Open/Closed Principle

Принцип **открытости/закрытости** означает, что система должна быть открыта для расширения, но закрыта для изменения уже работающего кода.

В прототипе это реализовано через абстракцию `Rule` и `RulesEngine`. Чтобы добавить новое правило, достаточно создать новый класс, реализующий интерфейс `Rule`, и подключить его в список правил. Код движка правил и сервиса анализа при этом менять не требуется.

### Проявление в коде

```python
class Rule(ABC):
    @abstractmethod
    def check(self, stats: dict, kpi: dict) -> List[dict]:
        pass
```

```python
class HighCpaRule(Rule):
    def check(self, stats: dict, kpi: dict) -> List[dict]:
        cpa = kpi.get("cpa")
        if cpa is not None and cpa > 2000:
            return [{
                "rule": "HIGH_CPA",
                "message": "Высокая стоимость привлечения — рекомендуется проверить ставки, аудитории и посадочную страницу.",
                "evidence": {"cpa": cpa}
            }]
        return []
```

```python
rules_engine = RulesEngine([
    SpendWithoutConversionsRule(),
    LowCtrRule(),
    HighCpaRule(),
])
```

Простыми словами: чтобы расширить систему новым правилом, не нужно переписывать уже работающий механизм анализа.

---

### ISP — Interface Segregation Principle

Принцип **разделения интерфейсов** означает, что не нужно заставлять класс зависеть от методов, которые ему не нужны.

Вместо одного большого интерфейса репозитория в коде используются два более узких интерфейса:

* `RunRepository` — для операций с запуском анализа;
* `RecommendationRepository` — для работы с рекомендациями.

Это делает зависимости более точными и понятными.

### Проявление в коде

```python
class RunRepository(ABC):
    @abstractmethod
    def save_run(self, run_id: str, payload: dict) -> None:
        pass
```

```python
class RecommendationRepository(ABC):
    @abstractmethod
    def save_recommendations(self, run_id: str, recos: list) -> None:
        pass

    @abstractmethod
    def get_recommendations(self, run_id: str) -> list:
        pass
```

Простыми словами: каждый интерфейс содержит только те методы, которые действительно относятся к одной задаче.

---

### LSP — Liskov Substitution Principle

Принцип **подстановки Лисков** означает, что объект дочернего класса должен без проблем заменять объект базового класса, если он соблюдает тот же контракт.

В данном примере это означает, что вместо `FakeStatsProvider` можно использовать другой класс, например реальный клиент Яндекс Директа, а вместо `InMemoryRepo` — реализацию на PostgreSQL. При этом `RecommendationService` менять не придется, если новые классы реализуют те же интерфейсы.

### Проявление в коде

```python
service = RecommendationService(
    provider=provider,
    run_repo=repo,
    reco_repo=repo,
    kpi_calc=kpi_calc,
    rules_engine=rules_engine,
)
```

Простыми словами: если новый класс реализует тот же контракт, он может заменить старый без изменения клиентского кода.

---

## SoC — Separation of Concerns

Принцип **разделения ответственности между уровнями системы** реализован на уровне архитектуры приложения.

В коде можно выделить следующие уровни:

* API-слой принимает HTTP-запросы;
* сервисный слой координирует сценарий анализа;
* слой расчета KPI отвечает за вычисления;
* слой правил отвечает за проверку бизнес-условий;
* инфраструктурный слой отвечает за получение данных и хранение результатов.

### Проявление в коде

```python
@app.post("/analysis/run", response_model=RunResponse)
def start_analysis(req: RunRequest):
    run_id = service.run_analysis(req.account_id, req.date_from, req.date_to)
    return RunResponse(run_id=run_id)
```

```python
class RecommendationService:
    def run_analysis(self, account_id: str, date_from: str, date_to: str) -> str:
        run_id = str(uuid4())

        self.run_repo.save_run(run_id, {
            "account_id": account_id,
            "date_from": date_from,
            "date_to": date_to,
            "status": "DONE"
        })

        stats_rows = self.provider.fetch_campaign_stats(account_id, date_from, date_to)

        recos = []
        for row in stats_rows:
            kpi = self.kpi_calc.calc(row)
            issues = self.rules_engine.check(row, kpi)

            for issue in issues:
                recos.append({
                    "campaign_id": row["campaign_id"],
                    "rule": issue["rule"],
                    "message": issue["message"],
                    "evidence": {
                        **issue["evidence"],
                        "kpi": kpi
                    },
                })

        self.reco_repo.save_recommendations(run_id, recos)
        return run_id
```

Простыми словами: разные части системы отвечают за разные типы задач и не смешивают обязанности.

---

### 2) Минимальный клиентский код

**KISS:** запрос на запуск и получение рекомендаций

```python
# client/run_demo.py
import requests

BASE = "http://localhost:8000"

run = requests.post(f"{BASE}/analysis/run", json={
    "account_id": "demo-account",
    "date_from": "2026-03-01",
    "date_to": "2026-03-07"
}).json()

run_id = run["run_id"]
print("run_id:", run_id)

recos = requests.get(f"{BASE}/analysis/{run_id}/recommendations").json()
for r in recos:
    print(r["campaign_id"], r["rule"], "-", r["message"])
```

---

## Дополнительные принципы разработки

### BDUF

**Отказ от полного BDUF**.
В дипломе важно быстро получить работающий MVP. Полное проектирование всего наперед повышает риск потратить время на детали, которые не понадобятся. Вместо этого применяем умеренный подход: фиксируем ключевые решения (C4 + правила + сущности) и развиваем итеративно.

### SoC

**Применяется.**
Разделены уровни ответственности: API-контроллеры, бизнес-сервисы, правила/расчеты KPI, репозиторий, интеграции

### MVP

Принцип **MVP (Minimum Viable Product)** реализован в том, что в системе присутствует только минимально необходимый набор функций:

* запуск анализа;
* получение статистики;
* расчет KPI;
* применение правил;
* сохранение рекомендаций;
* выдача результата по `run_id`.

Система не перегружена второстепенными возможностями, такими как полноценная авторизация, очередь сообщений, асинхронная обработка, реальная интеграция с внешними сервисами и расширенная аналитика.

Простыми словами: реализован минимально жизнеспособный прототип, который уже демонстрирует основную ценность системы.

### PoC

**Не применяется.**
Нечего доказывать.