from abc import ABC, abstractmethod


# =========================
# 1. CREATIONAL PATTERNS
# =========================

# Singleton
class AppConfig:
    _instance = None

    def __init__(self, api_key="demo"):
        self.api_key = api_key

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# Builder
class Recommendation:
    def __init__(self, campaign_id=None, rule=None, message=None, evidence=None):
        self.campaign_id = campaign_id
        self.rule = rule
        self.message = message
        self.evidence = evidence or {}

    def __repr__(self):
        return f"Recommendation(campaign_id={self.campaign_id}, rule={self.rule}, message={self.message}, evidence={self.evidence})"


class RecommendationBuilder:
    def __init__(self):
        self.obj = Recommendation()

    def set_campaign_id(self, campaign_id):
        self.obj.campaign_id = campaign_id
        return self

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


# Factory Method
class BaseRule(ABC):
    @abstractmethod
    def check(self, stats, kpi):
        pass


class LowCtrRule(BaseRule):
    def check(self, stats, kpi):
        if kpi["ctr"] < 0.01:
            return {
                "rule": "LOW_CTR",
                "message": "Низкий CTR",
                "evidence": {"ctr": kpi["ctr"]}
            }
        return None


class HighSpendNoConversionsRule(BaseRule):
    def check(self, stats, kpi):
        if stats["spend"] > 1000 and stats["conversions"] == 0:
            return {
                "rule": "HIGH_SPEND_NO_CONVERSIONS",
                "message": "Высокий расход без конверсий",
                "evidence": {"spend": stats["spend"], "conversions": stats["conversions"]}
            }
        return None


class RuleFactory:
    def create_rule(self, code):
        if code == "LOW_CTR":
            return LowCtrRule()
        if code == "HIGH_SPEND_NO_CONVERSIONS":
            return HighSpendNoConversionsRule()
        raise ValueError("Unknown rule")


# =========================
# 2. STRUCTURAL PATTERNS
# =========================

# Adapter
class StatsProvider:
    def fetch_stats(self, account_id, date_from, date_to):
        raise NotImplementedError


class YandexDirectAdapter(StatsProvider):
    def fetch_stats(self, account_id, date_from, date_to):
        print("Получение статистики из Yandex Direct API")
        return [
            {"campaign_id": "c1", "impressions": 1000, "clicks": 5, "spend": 1200, "conversions": 0},
            {"campaign_id": "c2", "impressions": 5000, "clicks": 200, "spend": 8000, "conversions": 12},
        ]


# Proxy
class CachedStatsProxy(StatsProvider):
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.cache = {}

    def fetch_stats(self, account_id, date_from, date_to):
        key = (account_id, date_from, date_to)
        if key not in self.cache:
            print("Кэш пустой, идем во внешний источник")
            self.cache[key] = self.wrapped.fetch_stats(account_id, date_from, date_to)
        else:
            print("Берем статистику из кэша")
        return self.cache[key]


# Decorator
class LoggingStatsProvider(StatsProvider):
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def fetch_stats(self, account_id, date_from, date_to):
        print(f"[LOG] fetch_stats(account_id={account_id}, from={date_from}, to={date_to})")
        return self.wrapped.fetch_stats(account_id, date_from, date_to)


# Facade
class KpiCalculator:
    def calc(self, row):
        ctr = row["clicks"] / row["impressions"] if row["impressions"] else 0
        cpc = row["spend"] / row["clicks"] if row["clicks"] else 0
        cpa = row["spend"] / row["conversions"] if row["conversions"] else None
        return {"ctr": ctr, "cpc": cpc, "cpa": cpa}


# =========================
# 3. BEHAVIORAL PATTERNS
# =========================

# Strategy
class AnalysisStrategy:
    def analyze(self, stats):
        raise NotImplementedError


class BasicAnalysisStrategy(AnalysisStrategy):
    def analyze(self, stats):
        return {"mode": "basic", "campaigns_count": len(stats)}


class ExtendedAnalysisStrategy(AnalysisStrategy):
    def analyze(self, stats):
        total_spend = sum(row["spend"] for row in stats)
        return {"mode": "extended", "campaigns_count": len(stats), "total_spend": total_spend}


class AnalyzerContext:
    def __init__(self, strategy):
        self.strategy = strategy

    def run(self, stats):
        return self.strategy.analyze(stats)


# Observer
class Observer:
    def update(self, event):
        raise NotImplementedError


class LogObserver(Observer):
    def update(self, event):
        print("[LOG OBSERVER]", event)


class NotificationObserver(Observer):
    def update(self, event):
        print("[NOTIFICATION OBSERVER]", event)


class AnalysisSubject:
    def __init__(self):
        self.observers = []

    def subscribe(self, observer):
        self.observers.append(observer)

    def notify(self, event):
        for obs in self.observers:
            obs.update(event)


# Command
class Command:
    def execute(self):
        raise NotImplementedError


# Chain of Responsibility
class RuleHandler:
    def __init__(self):
        self.next_handler = None

    def set_next(self, handler):
        self.next_handler = handler
        return handler

    def handle(self, stats, kpi):
        result = self.check(stats, kpi)
        results = []
        if result:
            results.append(result)
        if self.next_handler:
            results.extend(self.next_handler.handle(stats, kpi))
        return results

    def check(self, stats, kpi):
        raise NotImplementedError


class LowCtrHandler(RuleHandler):
    def check(self, stats, kpi):
        if kpi["ctr"] < 0.01:
            return {
                "rule": "LOW_CTR",
                "message": "Низкий CTR",
                "evidence": {"ctr": kpi["ctr"]}
            }
        return None


class HighSpendHandler(RuleHandler):
    def check(self, stats, kpi):
        if stats["spend"] > 1000 and stats["conversions"] == 0:
            return {
                "rule": "HIGH_SPEND_NO_CONVERSIONS",
                "message": "Высокий расход без конверсий",
                "evidence": {"spend": stats["spend"], "conversions": stats["conversions"]}
            }
        return None


# Template Method
class BaseAnalyzer:
    def run(self, stats):
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
        return stats

    def analyze(self, prepared):
        return {"campaigns_count": len(prepared)}

    def format_result(self, result):
        return {"status": "ok", "data": result}


class RecommendationService:
    def make_recommendations(self, row, issues):
        result = []
        for issue in issues:
            reco = (
                RecommendationBuilder()
                .set_campaign_id(row["campaign_id"])
                .set_rule(issue["rule"])
                .set_message(issue["message"])
                .set_evidence(issue.get("evidence", {}))
                .build()
            )
            result.append(reco)
        return result


class AnalysisFacade:
    def __init__(self, provider, kpi_calc, recommendation_service):
        self.provider = provider
        self.kpi_calc = kpi_calc
        self.recommendation_service = recommendation_service

    def run(self, account_id, date_from, date_to):
        stats_rows = self.provider.fetch_stats(account_id, date_from, date_to)

        # Strategy
        strategy = AnalyzerContext(ExtendedAnalysisStrategy())
        analysis_summary = strategy.run(stats_rows)
        print("Результат стратегии анализа:", analysis_summary)

        # Chain of Responsibility
        chain = LowCtrHandler()
        chain.set_next(HighSpendHandler())

        recommendations = []
        for row in stats_rows:
            kpi = self.kpi_calc.calc(row)
            issues = chain.handle(row, kpi)
            recommendations.extend(self.recommendation_service.make_recommendations(row, issues))

        return recommendations


class RunAnalysisCommand(Command):
    def __init__(self, facade, account_id, date_from, date_to):
        self.facade = facade
        self.account_id = account_id
        self.date_from = date_from
        self.date_to = date_to

    def execute(self):
        return self.facade.run(self.account_id, self.date_from, self.date_to)


def main():
    print("=== Singleton ===")
    cfg = AppConfig.get_instance()
    print("API key:", cfg.api_key)

    print("\n=== Adapter + Proxy + Decorator ===")
    provider = YandexDirectAdapter()
    provider = CachedStatsProxy(provider)
    provider = LoggingStatsProvider(provider)

    print("\n=== Observer ===")
    subject = AnalysisSubject()
    subject.subscribe(LogObserver())
    subject.subscribe(NotificationObserver())

    print("\n=== Facade + Command + Chain + Builder + Template Method ===")
    facade = AnalysisFacade(
        provider=provider,
        kpi_calc=KpiCalculator(),
        recommendation_service=RecommendationService()
    )

    command = RunAnalysisCommand(facade, "demo-account", "2026-03-01", "2026-03-07")
    recommendations = command.execute()

    for reco in recommendations:
        print(reco)

    subject.notify("Анализ завершен")

    print("\n=== Factory Method ===")
    factory = RuleFactory()
    rule = factory.create_rule("LOW_CTR")
    print("Создан объект правила:", rule.__class__.__name__)

    print("\n=== Template Method ===")
    analyzer = CampaignAnalyzer()
    print(analyzer.run([
        {"campaign_id": "c1"},
        {"campaign_id": "c2"}
    ]))

    print("\n=== Proxy second call (cache demo) ===")
    provider.fetch_stats("demo-account", "2026-03-01", "2026-03-07")


if __name__ == "__main__":
    main()