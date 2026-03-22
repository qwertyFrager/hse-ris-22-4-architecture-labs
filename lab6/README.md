# Лабораторная работа №6

## Тема: Использование шаблонов проектирования

### Цель работы

Получить практический опыт применения шаблонов проектирования при разработке программной системы.

### Связь с предыдущей работой

Данная лабораторная работа связана с предыдущей работой, в которой проектировалась система поддержки принятия решений для оптимизации рекламных кампаний в Яндекс Директ.
В той работе была определена архитектура системы, выделены основные сущности и компоненты: получение статистики, расчет KPI, применение правил анализа и формирование рекомендаций.

В данной лабораторной работе эта же система рассматривается уже с точки зрения шаблонов проектирования.
То есть если в предыдущей работе основной акцент был сделан на структуре системы и распределении ответственности между компонентами, то здесь показывается, **как именно эту систему можно реализовать в коде с помощью шаблонов GoF**.

В качестве примера рассматривается система, которая:

* получает статистику рекламных кампаний;
* рассчитывает показатели эффективности;
* анализирует данные по набору правил;
* формирует рекомендации для маркетолога.

---

# Порождающие шаблоны

## 1. Factory Method

### Что делает шаблон

Factory Method нужен для создания объектов без прямого указания конкретного класса в клиентском коде.
Проще говоря, мы не пишем везде вручную `LowCtrRule()` или `HighSpendNoConversionsRule()`, а передаем код правила на фабрику, и она сама решает, какой объект создать.

### Зачем он нужен в этом проекте

В системе анализа рекламы есть разные правила проверки кампаний.
Например:

* правило низкого CTR;
* правило высокого расхода без конверсий;
* правило слишком дорогого клика.

Если создавать такие объекты вручную в разных местах программы, код быстро станет неудобным и запутанным.
Поэтому удобнее сделать отдельную фабрику правил.

### Как используется

По строковому коду правила фабрика возвращает нужный объект.

### Код с комментариями

```python
from abc import ABC, abstractmethod

# Базовый абстрактный класс для всех правил анализа
class BaseRule(ABC):
    @abstractmethod
    def check(self, stats, kpi):
        pass


# Конкретное правило: низкий CTR
class LowCtrRule(BaseRule):
    def check(self, stats, kpi):
        if kpi["ctr"] < 0.01:
            return {
                "rule": "LOW_CTR",
                "message": "CTR рекламной кампании слишком низкий"
            }
        return None


# Конкретное правило: большой расход, но нет конверсий
class HighSpendNoConversionsRule(BaseRule):
    def check(self, stats, kpi):
        if stats["spend"] > 1000 and stats["conversions"] == 0:
            return {
                "rule": "HIGH_SPEND_NO_CONVERSIONS",
                "message": "Кампания тратит бюджет, но не приносит конверсий"
            }
        return None


# Фабрика создает нужный объект правила по его коду
class RuleFactory:
    def create_rule(self, code: str) -> BaseRule:
        if code == "LOW_CTR":
            return LowCtrRule()
        elif code == "HIGH_SPEND_NO_CONVERSIONS":
            return HighSpendNoConversionsRule()
        else:
            raise ValueError(f"Неизвестный код правила: {code}")


# Пример использования
factory = RuleFactory()
rule = factory.create_rule("LOW_CTR")
result = rule.check(
    stats={"spend": 500, "conversions": 2},
    kpi={"ctr": 0.005}
)
print(result)
```

### Что здесь происходит

В этом примере клиентский код не знает, какой именно класс будет создан.
Он просто говорит фабрике: «дай мне правило `LOW_CTR`».
Фабрика сама возвращает объект `LowCtrRule`.

### Почему это удобно

Преимущество в том, что при добавлении нового правила нужно изменить только фабрику и добавить новый класс.
Остальной код системы можно не переписывать.

---

## 2. Builder

### Что делает шаблон

Builder нужен для пошагового создания сложного объекта.
Он полезен, когда объект содержит несколько полей, которые заполняются постепенно.

### Зачем он нужен в этом проекте

В системе после анализа формируется рекомендация для маркетолога.
Она состоит не из одного значения, а сразу из нескольких частей:

* идентификатор кампании;
* код правила;
* текст рекомендации;
* доказательства или числовые данные.

Такой объект удобно собирать поэтапно.

### Как используется

Сначала создается строитель объекта, потом ему по очереди передаются нужные данные, а в конце вызывается `build()`.

### Код с комментариями

```python
# Объект рекомендации
class Recommendation:
    def __init__(self, campaign_id=None, rule=None, message=None, evidence=None):
        self.campaign_id = campaign_id
        self.rule = rule
        self.message = message
        self.evidence = evidence or {}

    def __repr__(self):
        return (
            f"Recommendation(campaign_id={self.campaign_id}, "
            f"rule={self.rule}, message={self.message}, evidence={self.evidence})"
        )


# Builder поэтапно собирает Recommendation
class RecommendationBuilder:
    def __init__(self):
        self.obj = Recommendation()

    def set_campaign_id(self, campaign_id):
        self.obj.campaign_id = campaign_id
        return self  # возвращаем self, чтобы можно было вызывать методы цепочкой

    def set_rule(self, rule):
        self.obj.rule = rule
        return self

    def set_message(self, message):
        self.obj.message = message
        return self

    def set_evidence(self, evidence):
        self.obj.evidence = evidence
        return self

    def build(self):
        return self.obj


# Пример использования
recommendation = (
    RecommendationBuilder()
    .set_campaign_id("cmp_101")
    .set_rule("LOW_CTR")
    .set_message("Нужно пересмотреть креативы или ключевые фразы")
    .set_evidence({"ctr": 0.004, "clicks": 12, "impressions": 3000})
    .build()
)

print(recommendation)
```

### Что здесь происходит

Объект рекомендации не создается сразу одной длинной строкой.
Он собирается постепенно: сначала задается кампания, потом правило, потом сообщение, потом доказательства.

### Почему это удобно

Такой подход делает код понятнее, особенно если полей много.
Кроме того, Builder хорошо подходит для ситуаций, когда некоторые поля могут быть необязательными.

---

## 3. Singleton

### Что делает шаблон

Singleton гарантирует, что у класса будет только один экземпляр на всю программу.

### Зачем он нужен в этом проекте

В системе есть конфигурация приложения:

* адрес базы данных;
* API-ключ;
* режим запуска;
* другие глобальные настройки.

Такие данные должны храниться в одном месте, чтобы все части программы использовали одинаковую конфигурацию.

### Как используется

При первом обращении объект создается, а дальше возвращается уже существующий экземпляр.

### Код с комментариями

```python
class AppConfig:
    _instance = None  # здесь будет храниться единственный экземпляр

    def __init__(self, api_key="demo_key", db_url="postgresql://localhost:5432/app"):
        self.api_key = api_key
        self.db_url = db_url

    @classmethod
    def get_instance(cls):
        # если экземпляр еще не создан — создаем
        if cls._instance is None:
            cls._instance = cls()
        # если уже создан — возвращаем существующий
        return cls._instance


# Пример использования
config1 = AppConfig.get_instance()
config2 = AppConfig.get_instance()

print(config1.api_key)
print(config1 is config2)  # True, это один и тот же объект
```

### Что здесь происходит

Метод `get_instance()` проверяет, существует ли уже объект конфигурации.
Если нет — создает его. Если да — возвращает уже существующий.

### Почему это удобно

Так система всегда работает с одной и той же конфигурацией, а не создает ее заново в разных местах кода.

---

# Структурные шаблоны

## 4. Adapter

### Что делает шаблон

Adapter приводит разные интерфейсы к единому виду.
То есть он помогает работать с разными внешними системами одинаково.

### Зачем он нужен в этом проекте

Система может получать данные из разных источников:

* из API Яндекс Директ;
* из Яндекс Метрики;
* из тестового источника;
* из локального файла.

У всех этих источников формат и методы могут быть разными.
Чтобы основной код не зависел от этих различий, используется адаптер.

### Как используется

Каждый источник оборачивается в класс с одинаковым методом `fetch_stats()`.

### Код с комментариями

```python
# Общий интерфейс поставщика статистики
class StatsProvider:
    def fetch_stats(self, account_id, date_from, date_to):
        raise NotImplementedError


# Адаптер для источника Яндекс Директ
class YandexDirectAdapter(StatsProvider):
    def fetch_stats(self, account_id, date_from, date_to):
        # Здесь в реальном проекте был бы запрос к API Яндекс Директ
        return [
            {
                "campaign_id": "cmp_1",
                "impressions": 1000,
                "clicks": 10,
                "spend": 1200,
                "conversions": 0
            }
        ]


# Адаптер для источника Метрики
class MetricaAdapter(StatsProvider):
    def fetch_stats(self, account_id, date_from, date_to):
        # Здесь в реальном проекте был бы запрос к API Метрики
        return [
            {
                "campaign_id": "cmp_2",
                "impressions": 500,
                "clicks": 20,
                "spend": 900,
                "conversions": 3
            }
        ]


# Основной код работает одинаково с любым адаптером
def load_and_print(provider: StatsProvider):
    stats = provider.fetch_stats("acc_1", "2026-03-01", "2026-03-10")
    print(stats)


load_and_print(YandexDirectAdapter())
load_and_print(MetricaAdapter())
```

### Что здесь происходит

Несмотря на то что источники данных разные, основной код вызывает у них один и тот же метод `fetch_stats()`.

### Почему это удобно

Если позже появится новый источник данных, достаточно будет написать еще один адаптер.
Остальная система останется без изменений.

---

## 5. Facade

### Что делает шаблон

Facade предоставляет один простой интерфейс для работы со сложной системой.

### Зачем он нужен в этом проекте

Полный анализ кампании включает несколько шагов:

* загрузка статистики;
* расчет KPI;
* проверка правил;
* создание рекомендаций.

Если вызывать все это вручную из контроллера, код станет громоздким.
Поэтому удобнее сделать фасад, который запускает весь процесс одной командой.

### Как используется

Внешний код вызывает только один метод `run()`.

### Код с комментариями

```python
class KpiCalculator:
    def calc(self, row):
        ctr = row["clicks"] / row["impressions"] if row["impressions"] else 0
        cpc = row["spend"] / row["clicks"] if row["clicks"] else 0
        cpa = row["spend"] / row["conversions"] if row["conversions"] else None
        return {"ctr": ctr, "cpc": cpc, "cpa": cpa}


class RulesEngine:
    def __init__(self, rules):
        self.rules = rules

    def check_all(self, row, kpi):
        issues = []
        for rule in self.rules:
            result = rule.check(row, kpi)
            if result:
                issues.append(result)
        return issues


class RecommendationService:
    def make_recommendations(self, row, issues):
        recommendations = []
        for issue in issues:
            reco = (
                RecommendationBuilder()
                .set_campaign_id(row["campaign_id"])
                .set_rule(issue["rule"])
                .set_message(issue["message"])
                .set_evidence(issue.get("evidence", {}))
                .build()
            )
            recommendations.append(reco)
        return recommendations


class AnalysisFacade:
    def __init__(self, provider, kpi_calc, rules_engine, recommendation_service):
        self.provider = provider
        self.kpi_calc = kpi_calc
        self.rules_engine = rules_engine
        self.recommendation_service = recommendation_service

    def run(self, account_id, date_from, date_to):
        # 1. Получаем статистику
        stats_rows = self.provider.fetch_stats(account_id, date_from, date_to)

        result = []

        # 2. Для каждой кампании рассчитываем KPI
        # 3. Проверяем правила
        # 4. Формируем рекомендации
        for row in stats_rows:
            kpi = self.kpi_calc.calc(row)
            issues = self.rules_engine.check_all(row, kpi)
            recommendations = self.recommendation_service.make_recommendations(row, issues)
            result.extend(recommendations)

        return result
```

### Что здесь происходит

Фасад скрывает всю внутреннюю последовательность действий.
Снаружи это выглядит как один простой вызов: «выполни анализ».

### Почему это удобно

Контроллер или API-слой не знает деталей реализации.
Он просто обращается к фасаду, а тот координирует работу всех компонентов.

---

## 6. Decorator

### Что делает шаблон

Decorator позволяет добавить объекту новую функциональность, не меняя его исходный код.

### Зачем он нужен в этом проекте

При работе с источником статистики полезно логировать обращения:

* когда был запрос;
* к какому аккаунту;
* за какой период.

Не хочется встраивать логирование внутрь каждого адаптера.
Поэтому поверх поставщика статистики можно добавить декоратор.

### Как используется

Декоратор оборачивает объект и передает вызов дальше, добавляя перед этим или после этого дополнительное поведение.

### Код с комментариями

```python
class LoggingStatsProvider(StatsProvider):
    def __init__(self, wrapped):
        self.wrapped = wrapped  # объект, который мы декорируем

    def fetch_stats(self, account_id, date_from, date_to):
        # Добавляем дополнительное поведение
        print(f"[LOG] Запрос статистики: account_id={account_id}, period={date_from}..{date_to}")

        # Передаем выполнение исходному объекту
        return self.wrapped.fetch_stats(account_id, date_from, date_to)


# Пример использования
provider = LoggingStatsProvider(YandexDirectAdapter())
stats = provider.fetch_stats("acc_1", "2026-03-01", "2026-03-10")
print(stats)
```

### Что здесь происходит

Класс `LoggingStatsProvider` не заменяет адаптер, а оборачивает его.
Он сначала печатает лог, а потом вызывает реальный метод `fetch_stats()` у вложенного объекта.

### Почему это удобно

Можно добавлять логирование, не меняя исходный код адаптера.
Точно так же можно добавлять и другие функции, например замер времени или проверку прав доступа.

---

## 7. Proxy

### Что делает шаблон

Proxy — это объект-заместитель, который контролирует доступ к другому объекту.

### Зачем он нужен в этом проекте

Внешние API не стоит вызывать лишний раз, потому что это:

* медленнее;
* может расходовать лимиты;
* создает лишнюю нагрузку.

Поэтому можно использовать прокси с кэшем: если данные уже были запрошены ранее, повторно обращаться к API не нужно.

### Как используется

Прокси проверяет, есть ли уже результат в кэше.
Если есть — возвращает его. Если нет — идет к реальному объекту.

### Код с комментариями

```python
class CachedStatsProxy(StatsProvider):
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.cache = {}  # словарь для хранения уже полученных результатов

    def fetch_stats(self, account_id, date_from, date_to):
        key = (account_id, date_from, date_to)

        # Если данные уже есть в кэше — сразу возвращаем их
        if key in self.cache:
            print("[CACHE] Данные взяты из кэша")
            return self.cache[key]

        # Иначе обращаемся к реальному поставщику
        print("[CACHE] Данных нет в кэше, выполняем реальный запрос")
        result = self.wrapped.fetch_stats(account_id, date_from, date_to)
        self.cache[key] = result
        return result


# Пример использования
provider = CachedStatsProxy(YandexDirectAdapter())

provider.fetch_stats("acc_1", "2026-03-01", "2026-03-10")
provider.fetch_stats("acc_1", "2026-03-01", "2026-03-10")  # второй раз пойдет из кэша
```

### Что здесь происходит

Первый вызов обращается к настоящему поставщику.
Второй вызов с теми же параметрами возвращает уже сохраненный результат.

### Почему это удобно

Система работает быстрее и делает меньше внешних запросов.

---

# Поведенческие шаблоны

## 8. Strategy

### Что делает шаблон

Strategy позволяет выбирать один из нескольких алгоритмов и менять его без изменения основного кода.

### Зачем он нужен в этом проекте

В системе можно использовать разные режимы анализа:

* базовый анализ;
* расширенный анализ;
* более строгий анализ для крупных рекламных аккаунтов.

Это разные алгоритмы, но вызываются они одинаково.

### Как используется

Контекст хранит ссылку на стратегию и вызывает ее метод.

### Код с комментариями

```python
class AnalysisStrategy:
    def analyze(self, stats):
        raise NotImplementedError


# Простая стратегия анализа
class BasicAnalysisStrategy(AnalysisStrategy):
    def analyze(self, stats):
        return {
            "mode": "basic",
            "campaigns_count": len(stats)
        }


# Расширенная стратегия анализа
class ExtendedAnalysisStrategy(AnalysisStrategy):
    def analyze(self, stats):
        total_spend = sum(row["spend"] for row in stats)
        total_clicks = sum(row["clicks"] for row in stats)

        return {
            "mode": "extended",
            "campaigns_count": len(stats),
            "total_spend": total_spend,
            "total_clicks": total_clicks
        }


# Контекст использует выбранную стратегию
class AnalyzerContext:
    def __init__(self, strategy: AnalysisStrategy):
        self.strategy = strategy

    def set_strategy(self, strategy: AnalysisStrategy):
        self.strategy = strategy

    def run(self, stats):
        return self.strategy.analyze(stats)


# Пример использования
stats = [
    {"spend": 500, "clicks": 10},
    {"spend": 900, "clicks": 30}
]

context = AnalyzerContext(BasicAnalysisStrategy())
print(context.run(stats))

context.set_strategy(ExtendedAnalysisStrategy())
print(context.run(stats))
```

### Что здесь происходит

Объект `AnalyzerContext` сам не знает деталей анализа.
Он просто вызывает текущую стратегию.

### Почему это удобно

Можно легко менять логику анализа, не переписывая остальной код.

---

## 9. Observer

### Что делает шаблон

Observer нужен для уведомления подписчиков о событии.

### Зачем он нужен в этом проекте

После завершения анализа можно выполнить дополнительные действия:

* записать событие в лог;
* отправить уведомление;
* сохранить информацию о завершении процесса.

Все это удобно делать через подписчиков.

### Как используется

Один объект рассылает событие всем наблюдателям.

### Код с комментариями

```python
class Observer:
    def update(self, event):
        raise NotImplementedError


# Наблюдатель для логирования
class LogObserver(Observer):
    def update(self, event):
        print("[LOG]", event)


# Наблюдатель для уведомлений
class NotificationObserver(Observer):
    def update(self, event):
        print("[NOTIFICATION]", event)


# Объект, за которым наблюдают
class AnalysisSubject:
    def __init__(self):
        self.observers = []

    def subscribe(self, observer):
        self.observers.append(observer)

    def notify(self, event):
        for observer in self.observers:
            observer.update(event)


# Пример использования
subject = AnalysisSubject()
subject.subscribe(LogObserver())
subject.subscribe(NotificationObserver())

subject.notify("Анализ рекламных кампаний завершен")
```

### Что здесь происходит

Объект `AnalysisSubject` не знает, что именно делают подписчики.
Он просто отправляет им событие.

### Почему это удобно

Можно добавлять новые реакции на событие, не меняя основной код анализа.

---

## 10. Command

### Что делает шаблон

Command превращает действие в отдельный объект.

### Зачем он нужен в этом проекте

Запуск анализа можно представить как отдельную команду.
Это удобно, если анализ нужно:

* ставить в очередь;
* запускать позже;
* повторять;
* логировать отдельно.

### Как используется

Создается объект команды, в котором уже есть все данные для выполнения анализа.

### Код с комментариями

```python
class Command:
    def execute(self):
        raise NotImplementedError


class RunAnalysisCommand(Command):
    def __init__(self, facade, account_id, date_from, date_to):
        self.facade = facade
        self.account_id = account_id
        self.date_from = date_from
        self.date_to = date_to

    def execute(self):
        # Команда инкапсулирует весь запрос на выполнение анализа
        return self.facade.run(self.account_id, self.date_from, self.date_to)
```

### Что здесь происходит

Команда хранит в себе все, что нужно для запуска анализа: фасад и параметры периода.

### Почему это удобно

Команду можно передавать в очередь, сохранять, повторять и обрабатывать отдельно от вызывающего кода.

---

## 11. Chain of Responsibility

### Что делает шаблон

Этот шаблон позволяет передавать запрос по цепочке обработчиков.

### Зачем он нужен в этом проекте

В системе есть несколько правил анализа.
Они могут проверяться последовательно одно за другим.
Каждый обработчик проверяет свое условие.

### Как используется

Правила связываются в цепочку, и данные проходят через нее.

### Код с комментариями

```python
class RuleHandler:
    def __init__(self):
        self.next_handler = None

    def set_next(self, handler):
        self.next_handler = handler
        return handler

    def handle(self, stats, kpi):
        result = self.check(stats, kpi)

        # Если текущий обработчик что-то нашел — возвращаем результат
        if result:
            return [result]

        # Иначе передаем запрос дальше по цепочке
        if self.next_handler:
            return self.next_handler.handle(stats, kpi)

        return []

    def check(self, stats, kpi):
        raise NotImplementedError


class LowCtrHandler(RuleHandler):
    def check(self, stats, kpi):
        if kpi["ctr"] < 0.01:
            return {
                "rule": "LOW_CTR",
                "message": "Низкий CTR"
            }


class HighSpendHandler(RuleHandler):
    def check(self, stats, kpi):
        if stats["spend"] > 1000 and stats["conversions"] == 0:
            return {
                "rule": "HIGH_SPEND_NO_CONVERSIONS",
                "message": "Высокий расход без конверсий"
            }


# Пример использования
handler1 = LowCtrHandler()
handler2 = HighSpendHandler()

handler1.set_next(handler2)

result = handler1.handle(
    stats={"spend": 1500, "conversions": 0},
    kpi={"ctr": 0.02}
)

print(result)
```

### Что здесь происходит

Если первое правило не срабатывает, управление передается следующему.
Так можно организовать последовательную проверку набора условий.

### Почему это удобно

Каждое правило оформлено отдельно, и цепочку можно легко менять: добавлять новые звенья, убирать старые, менять порядок.

---

## 12. Template Method

### Что делает шаблон

Template Method задает общий каркас алгоритма, а отдельные шаги оставляет подклассам.

### Зачем он нужен в этом проекте

Процесс анализа обычно состоит из одинаковых этапов:

* подготовить данные;
* выполнить анализ;
* оформить результат.

Но конкретная реализация этих шагов может отличаться в зависимости от типа анализа.

### Как используется

Базовый класс определяет общий порядок действий, а дочерний класс реализует конкретные шаги.

### Код с комментариями

```python
class BaseAnalyzer:
    def run(self, stats):
        # Общий алгоритм всегда одинаковый
        prepared = self.prepare(stats)
        result = self.analyze(prepared)
        return self.format_result(result)

    def prepare(self, stats):
        raise NotImplementedError

    def analyze(self, prepared):
        raise NotImplementedError

    def format_result(self, result):
        raise NotImplementedError


class CampaignAnalyzer(BaseAnalyzer):
    def prepare(self, stats):
        # На этом этапе можно очищать или фильтровать входные данные
        return stats

    def analyze(self, prepared):
        # Здесь выполняется конкретный анализ
        return {"campaigns_count": len(prepared)}

    def format_result(self, result):
        # Здесь оформляется результат в нужном виде
        return {"status": "ok", "data": result}


# Пример использования
analyzer = CampaignAnalyzer()
result = analyzer.run([
    {"campaign_id": "c1"},
    {"campaign_id": "c2"},
    {"campaign_id": "c3"}
])

print(result)
```

### Что здесь происходит

Метод `run()` уже задает готовую последовательность действий.
Подкласс только подставляет свою реализацию отдельных этапов.

### Почему это удобно

Общий алгоритм не дублируется, но при этом конкретные шаги можно менять в дочерних классах.
