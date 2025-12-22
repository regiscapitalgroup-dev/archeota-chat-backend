from weasyprint import HTML
from archeota import settings
from claim.models import ClaimAction, ClassActionLawsuit
from django.template.loader import render_to_string

class ClaimReporter():
    def build_reporter(user, claim: ClaimAction, classes: list[ClassActionLawsuit]) -> bytes:
        context = {
            "company": claim.company_name,
            "law_firm": claim.law_firm_handing_case,
            "client": {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "address": user.profile.address,
                "country": user.profile.country,
                "phone": user.profile.phone_number,
                "email": user.email
            },
            "transactions": [
                {
                    "date": "2023-01-15",
                    "type": "BUY",
                    "symbol": "AAPL",
                    "quantity": 50,
                    "price": 150,
                    "amount": 7500
                }
            ],
            "stocks": classes
        }

        html = render_to_string(
            "claim.html",
            context
        )

        pdf = HTML(
            string=html,
            base_url=settings.SITE_URL
        ).write_pdf()
        return pdf