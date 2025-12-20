from collections import defaultdict
from decimal import Decimal
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
    
    def send_claim_email(self, user, claim: ClaimAction, holdings: list[ClassActionLawsuit]):
        html_content = f"""
            <h1>Join the {claim.company_name} Class Action</h1>
            <h2>{claim.company_name} Securities Class Action Certification</h2>

            <p>
            The individual or institution listed below (the "Plaintiff") authorizes,
            and, upon execution of the accompanying retainer agreement by {claim.law_firm_handing_case}, retains {claim.law_firm_handing_case} to file an action under the federal securities
            laws.
            </p>

            <div class="section">

            <h3>Personal Information</h3>

            <p><span class="label">First Name:</span> {user.first_name}</p>
            <p><span class="label">Last Name:</span> {user.last_name }</p>
            <p><span class="label">Mailing Address:</span> { user.profile.address }</p>
            <p><span class="label">Country:</span> { user.profile.country }</p>
            <p><span class="label">Phone:</span> { user.profile.phone_number }</p>
            <p><span class="label">Email:</span> { user.email }</p>

            <p>
                If Representing an Entity: [] Yes [X] No
            </p>

            <p>
                Are you a current or former employee of the company? [] Yes [X] No
            </p>
            </div>

            <div class="section">
            <h3>Plaintiff Certifies That:</h3>
            <ol>
                <li>Has reviewed and authorized the filing of the complaint.</li>
                <li>Did not acquire securities at the direction of counsel.</li>
                <li>Is willing to serve as a class representative.</li>
                <li>Is fully authorized to execute this certification.</li>
                <li>Will not accept improper compensation.</li>
            </ol>
            </div>


            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                <thead>
                    <tr>
                        <th>Lot</th>
                        <th>Start date</th>
                        <th>Final date</th>
                        <th>Company</th>
                        <th>Symbol</th>
                        <th>Quantity</th>
                        <th>Amount</th>
                        <th>Cost per stock</th>
                    </tr>
                </thead>
            <tbody>
                
            """
        for hold in holdings:
            html_content += f"""
                <tr>
                    <td>{hold.holding.lot_number}</td>
                    <td>{hold.holding.start_date}</td>
                    <td>{hold.holding.end_date}</td>
                    <td>{hold.holding.company}</td>
                    <td>{hold.holding.symbol}</td>
                    <td>{hold.holding.quantity}</td>
                    <td>{hold.holding.amount}</td>
                    <td>{hold.holding.cost_per_stock}</td>
                </tr>
            """


        html_content += """
                </tbody>
            </table>
            <div class="section">
                <h3>Additional Disclosures</h3>
                </div>

                <div class="signature-box">
                <p>
                    [] I declare under penalty of perjury that the information is accurate.
                </p>

                <p><strong>Signature:</strong> </p>
                <p><strong>Date:</strong> </p>
            </div>
            """

        send_mail(
            subject=f"Claim Action for {user.first_name} {user.last_name}",
            message="Claim reporter",
            from_email=settings.ADMIN_USER_EMAIL,
            recipient_list=[claim.email],
            html_message=html_content,
        )
        pass

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
        
        if claim.method_send_claim_format != 'Email':
            return
        
        for user, classes in grouped_by_user.items():
            self.send_claim_email(
                user,
                claim,
                classes
            )
        
        