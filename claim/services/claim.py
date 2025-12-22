from collections import defaultdict
from decimal import Decimal
from django.core.mail import EmailMessage
import uuid
from django.core.mail import send_mail
from typing import Any
from archeota import settings
from claim.models import ActionsHoldings, ClaimAction, ClassActionLawsuit
from claim.services.holdings import HoldingService
from claim.services.reporter import ClaimReporter
from users.models import Company
from django.db import transaction

class ClaimSevice():
    def __init__(self, user, company: Company):
        self.user = user
        self.company = company
        self.holding_svc = HoldingService(self.user)

    @transaction.atomic
    def __save_bulk(self, bulk):
        ClassActionLawsuit.objects.bulk_create(bulk)

    @transaction.atomic
    def __create_class(self, claim: ClaimAction, holding: ActionsHoldings):
        return ClassActionLawsuit(
            batch_id = uuid.uuid4(),
            tycker_symbol=holding.symbol,
            company_name=claim.company_name,
            quantity_stock=holding.quantity,
            value_per_stock=claim.value_per_share,
            amount=Decimal(holding.quantity)*claim.value_per_share,
            claim_date=claim.start_eligibility_date,
            status=claim.claim_status,
            user=holding.user,
            company=self.company,
            holding=holding,
            claim=claim
        )
    
    @transaction.atomic
    def __format_sent(self, batch_id: list[uuid.UUID]):
        (ClassActionLawsuit.objects
        .filter(batch_id__in=batch_id)
        .update(send_format=True))
    
    def send_claim_email(self, user, claim: ClaimAction, holdings: list[ClassActionLawsuit]):
        pdf = ClaimReporter.build_reporter(user, claim, holdings)
        mail = EmailMessage(
            subject=f"Claim Action for {user.first_name} {user.last_name}",
            body="Archeota - Claim Action Report",
            from_email=settings.ADMIN_USER_EMAIL,
            to=[claim.email]
        )

        mail.attach(
            filename=f"ClaimAction_{user.first_name}_{user.last_name}_{claim.tycker_symbol}.pdf",
            content=pdf,
            mimetype="application/pdf"
        )
        mail.send()

        batch_ids = [h.batch_id for h in holdings]
        self.__format_sent(batch_ids)

    def __send_handle(self, claim: ClaimAction, payload: dict[Any, list[ClassActionLawsuit]]):
        method = str(claim.method_send_claim_format).strip().upper()
        match method:
            case "EMAIL":
                for user, classes in payload.items():
                    self.send_claim_email(
                        user,
                        claim,
                        classes
                    )
                return
            case _:
                return

    def process_claim(self, claim: ClaimAction):
        if self.user.role != 'SUPER_ADMIN' and self.user.profile.company.id != self.company.id:
            raise Exception("Not allowed")

        grouped_by_user: dict[Any, list[ClassActionLawsuit]] = defaultdict(list)
        
        start_date = claim.start_eligibility_date
        end_date = claim.final_eligibility_date
        company_holdings = self.holding_svc.company_holdings(self.company, claim.tycker_symbol, start_date, end_date)
        for holding in company_holdings:
            class_lawsuit = self.__create_class(claim, holding) 
            grouped_by_user[holding.user].append(class_lawsuit)

        for _, bulk in grouped_by_user.items():
            self.__save_bulk(bulk)
        
        self.__send_handle(claim, grouped_by_user)
        
        
        
        