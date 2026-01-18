from django.core.management.base import BaseCommand
from assets.models import Asset
from decimal import Decimal
import random

class Command(BaseCommand):
    help = "Seed database with 60 real-world assets"

    def handle(self, *args, **options):
        assets = [
            # ---------- STOCKS (30) ----------
            ("Apple Inc.", "AAPL", "STOCK"),
            ("Microsoft Corp.", "MSFT", "STOCK"),
            ("Amazon.com Inc.", "AMZN", "STOCK"),
            ("Alphabet Inc.", "GOOGL", "STOCK"),
            ("Meta Platforms Inc.", "META", "STOCK"),
            ("Nvidia Corp.", "NVDA", "STOCK"),
            ("Tesla Inc.", "TSLA", "STOCK"),
            ("Berkshire Hathaway", "BRK.B", "STOCK"),
            ("Johnson & Johnson", "JNJ", "STOCK"),
            ("Procter & Gamble", "PG", "STOCK"),
            ("JPMorgan Chase", "JPM", "STOCK"),
            ("Visa Inc.", "V", "STOCK"),
            ("Mastercard Inc.", "MA", "STOCK"),
            ("Exxon Mobil", "XOM", "STOCK"),
            ("Chevron Corp.", "CVX", "STOCK"),
            ("Walt Disney Co.", "DIS", "STOCK"),
            ("Home Depot", "HD", "STOCK"),
            ("McDonald's Corp.", "MCD", "STOCK"),
            ("Netflix Inc.", "NFLX", "STOCK"),
            ("Adobe Inc.", "ADBE", "STOCK"),
            ("Intel Corp.", "INTC", "STOCK"),
            ("Cisco Systems", "CSCO", "STOCK"),
            ("PepsiCo Inc.", "PEP", "STOCK"),
            ("Coca-Cola Co.", "KO", "STOCK"),
            ("Pfizer Inc.", "PFE", "STOCK"),
            ("Merck & Co.", "MRK", "STOCK"),
            ("Salesforce Inc.", "CRM", "STOCK"),
            ("Oracle Corp.", "ORCL", "STOCK"),
            ("IBM", "IBM", "STOCK"),
            ("AT&T Inc.", "T", "STOCK"),

            # ---------- ETFs (15) ----------
            ("SPDR S&P 500 ETF Trust", "SPY", "ETF"),
            ("Vanguard S&P 500 ETF", "VOO", "ETF"),
            ("Invesco QQQ Trust", "QQQ", "ETF"),
            ("Vanguard Total Stock Market ETF", "VTI", "ETF"),
            ("Schwab U.S. Dividend Equity ETF", "SCHD", "ETF"),
            ("iShares Core U.S. Aggregate Bond ETF", "AGG", "ETF"),
            ("iShares Russell 2000 ETF", "IWM", "ETF"),
            ("Technology Select Sector SPDR", "XLK", "ETF"),
            ("Financial Select Sector SPDR", "XLF", "ETF"),
            ("Health Care Select Sector SPDR", "XLV", "ETF"),
            ("Energy Select Sector SPDR", "XLE", "ETF"),
            ("Vanguard FTSE Developed Markets ETF", "VEA", "ETF"),
            ("Vanguard FTSE Emerging Markets ETF", "VWO", "ETF"),
            ("iShares MSCI EAFE ETF", "EFA", "ETF"),
            ("Vanguard Real Estate ETF", "VNQ", "ETF"),

            # ---------- REITs (15) ----------
            ("Realty Income Corp.", "O", "REIT"),
            ("Prologis, Inc.", "PLD", "REIT"),
            ("Welltower Inc.", "WELL", "REIT"),
            ("Simon Property Group Inc.", "SPG", "REIT"),
            ("Equinix, Inc.", "EQIX", "REIT"),
            ("Digital Realty Trust Inc.", "DLR", "REIT"),
            ("Public Storage Inc.", "PSA", "REIT"),
            ("Ventas, Inc.", "VTR", "REIT"),
            ("Extra Space Storage Inc.", "EXR", "REIT"),
            ("VICI Properties Inc.", "VICI", "REIT"),
            ("AvalonBay Communities Inc.", "AVB", "REIT"),
            ("Equity Residential", "EQR", "REIT"),
            ("Crown Castle Inc.", "CCI", "REIT"),
            ("American Tower Corp.", "AMT", "REIT"),
            ("Healthpeak Properties Inc.", "PEAK", "REIT"),
        ]

        def random_price():
            return Decimal(str(round(random.uniform(30, 600), 2)))

        def random_volatility():
            return Decimal(str(round(random.uniform(0.8, 4.5), 2)))

        def random_yield():
            return Decimal(str(round(random.uniform(3.0, 7.5), 2)))

        created = 0

        for name, symbol, asset_type in assets:
            if Asset.objects.filter(symbol=symbol).exists():
                continue

            asset = Asset(
                name=name,
                symbol=symbol,
                asset_type=asset_type,
                price=random_price(),
                volatility=random_volatility(),
            )

            if asset_type == "REIT":
                asset.annual_yield = random_yield()
                asset.dividend_frequency = random.choice(["MONTHLY", "QUARTERLY"])

            asset.full_clean()
            asset.save()
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"{created} real assets created")
        )
