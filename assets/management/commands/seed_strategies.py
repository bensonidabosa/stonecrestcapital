from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import random

from assets.models import Asset
from strategies.models import Strategy, StrategyAllocation


class Command(BaseCommand):
    help = "Seed database with realistic investment strategies"

    def handle(self, *args, **options):
        # -----------------------------
        # Strategy templates
        # -----------------------------
        strategy_templates = [
            # ---------- LOW RISK ----------
            {"name": "Capital Preservation", "risk": "LOW", "min": 3.0, "max": 6.0, "asset_types": ["ETF"]},
            {"name": "Income Stability REIT", "risk": "LOW", "min": 4.0, "max": 7.0, "asset_types": ["REIT"]},
            {"name": "Conservative Income", "risk": "LOW", "min": 4.5, "max": 7.5, "asset_types": ["ETF", "REIT"]},

            # ---------- MEDIUM RISK ----------
            {"name": "Balanced Growth", "risk": "MEDIUM", "min": 6.0, "max": 10.0, "asset_types": ["STOCK", "ETF"]},
            {"name": "Dividend Plus REIT", "risk": "MEDIUM", "min": 6.5, "max": 10.5, "asset_types": ["STOCK", "REIT"]},
            {"name": "Core Allocation", "risk": "MEDIUM", "min": 7.0, "max": 11.0, "asset_types": ["STOCK", "ETF", "REIT"]},
            {"name": "Global Blend", "risk": "MEDIUM", "min": 7.0, "max": 12.0, "asset_types": ["ETF"]},
            {"name": "High Yield REIT", "risk": "MEDIUM", "min": 6.0, "max": 11.0, "asset_types": ["REIT"]},

            # ---------- HIGH RISK ----------
            {"name": "Aggressive Growth", "risk": "HIGH", "min": 10.0, "max": 18.0, "asset_types": ["STOCK"]},
            {"name": "Equity Accelerator", "risk": "HIGH", "min": 11.0, "max": 20.0, "asset_types": ["STOCK", "ETF"]},
            {"name": "Real Estate Alpha REIT", "risk": "HIGH", "min": 9.0, "max": 16.0, "asset_types": ["REIT"]},
            {"name": "Total Market Exposure", "risk": "HIGH", "min": 10.0, "max": 18.0, "asset_types": ["STOCK", "ETF", "REIT"]},
            {"name": "REIT Income Booster", "risk": "HIGH", "min": 8.0, "max": 15.0, "asset_types": ["REIT"]},

            # ---------- ADDITIONAL STRATEGIES ----------
            {"name": "Tech Growth", "risk": "HIGH", "min": 12.0, "max": 20.0, "asset_types": ["STOCK"]},
            {"name": "ETF Momentum", "risk": "MEDIUM", "min": 7.0, "max": 12.0, "asset_types": ["ETF"]},
            {"name": "REIT Core Income", "risk": "LOW", "min": 4.0, "max": 8.0, "asset_types": ["REIT"]},
            {"name": "Balanced Blend", "risk": "MEDIUM", "min": 6.5, "max": 11.0, "asset_types": ["STOCK", "ETF", "REIT"]},
            {"name": "Dividend Focus", "risk": "LOW", "min": 4.5, "max": 7.5, "asset_types": ["STOCK", "REIT"]},
            {"name": "High Risk REIT Growth", "risk": "HIGH", "min": 9.5, "max": 17.0, "asset_types": ["REIT"]},
            {"name": "Global REIT Exposure", "risk": "MEDIUM", "min": 6.0, "max": 12.0, "asset_types": ["REIT"]},
        ]


        created = 0

        for template in strategy_templates:
            if Strategy.objects.filter(name=template["name"]).exists():
                continue

            with transaction.atomic():
                strategy = Strategy.objects.create(
                    name=template["name"],
                    description=f"{template['name']} strategy",
                    risk_level=template["risk"],
                    target_return_min=Decimal(template["min"]),
                    target_return_max=Decimal(template["max"]),
                    is_active=True,
                )

                # -----------------------------
                # Select assets
                # -----------------------------
                eligible_assets = Asset.objects.filter(
                    asset_type__in=template["asset_types"]
                )

                allocation_count = random.randint(6, 10)
                assets = random.sample(
                    list(eligible_assets),
                    min(allocation_count, eligible_assets.count())
                )

                # -----------------------------
                # Allocate percentages to 100%
                # -----------------------------
                weights = [random.uniform(5, 20) for _ in assets]
                total_weight = sum(weights)

                allocations = []
                for asset, weight in zip(assets, weights):
                    percentage = (Decimal(weight) / Decimal(total_weight)) * Decimal(100)
                    allocations.append(
                        StrategyAllocation(
                            strategy=strategy,
                            asset=asset,
                            percentage=percentage.quantize(Decimal("0.01"))
                        )
                    )

                # Fix rounding difference
                diff = Decimal("100.00") - sum(a.percentage for a in allocations)
                allocations[0].percentage += diff

                StrategyAllocation.objects.bulk_create(allocations)

                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"{created} strategies created successfully")
        )
