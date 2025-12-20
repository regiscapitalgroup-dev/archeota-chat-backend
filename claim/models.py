from django.db import models
from django.contrib.auth import get_user_model
import uuid

from users.models import Company


USER_MODEL = get_user_model()


class ClaimAction(models.Model):
    tycker_symbol = models.CharField(max_length=255, null=True, blank=True)
    company_name = models.TextField(null=True, blank=True)
    exchange = models.TextField(null=True, blank=True)
    lawsuit_type = models.TextField(null=True, blank=True)
    eligibility = models.CharField(max_length=255, null=True, blank=True)
    start_eligibility_date = models.CharField(max_length=30, null=True, blank=True)
    final_eligibility_date = models.CharField(max_length=30, null=True, blank=True)
    potencial_claim = models.CharField(max_length=255, null=True, blank=True)
    total_settlement_fund = models.CharField(max_length=255, null=True, blank=True)
    filing_date = models.CharField(max_length=255, null=True, blank=True)
    claim_deadline = models.CharField(max_length=255, null=True, blank=True)
    law_firm_handing_case = models.CharField(max_length=255, null=True, blank=True)
    case_docket_number = models.CharField(max_length=255, null=True, blank=True)
    value_per_share = models.DecimalField(max_digits=24, decimal_places=4, null=False, blank=False)
    jurisdiction = models.CharField(max_length=255, null=True, blank=True)
    claim_status = models.CharField(max_length=255, null=True, blank=True)
    claim_format_name = models.CharField(max_length=255, null=True, blank=True)
    method_send_claim_format = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    official_claim_filing_link = models.CharField(max_length=255, null=True, blank=True)
    last_update = models.CharField(max_length=255, null=True, blank=True)
    claimed = models.BooleanField(null=False, blank=False, default=False)
    user = models.ForeignKey(USER_MODEL, null=True, on_delete=models.CASCADE, related_name='claim_actions')
    company = models.ForeignKey(Company,  null=True, blank=True, on_delete=models.CASCADE, related_name="claim_actions")
    
    def __str__(self) -> str:
        return self.tycker_symbol

    class Meta:
        verbose_name = "Claim Action"
        verbose_name_plural = "Claim Actions"

class ActionsHoldings(models.Model):
    lot_number = models.IntegerField(null=False, blank=False, default=0)
    name = models.CharField(max_length=255, null=True, blank=True)
    start_date = models.DateField(max_length=30, null=True, blank=True)
    end_date = models.DateField(max_length=30, null=True, blank=True)
    symbol = models.CharField(max_length=20, null=False, blank=False)
    quantity = models.IntegerField(null=False, blank=False)
    cost_per_stock = models.DecimalField(max_digits=24, decimal_places=4, null=False, blank=False)
    amount = models.DecimalField(max_digits=24, decimal_places=4, null=False, blank=False)
    activity = models.CharField(max_length=255, null=True, blank=True)
    useless = models.BooleanField(null=False, blank=False, default=False)
    user = models.ForeignKey(USER_MODEL, null=True, on_delete=models.CASCADE, related_name='actions_holdings')
    company = models.ForeignKey(Company,  null=True, blank=True, on_delete=models.CASCADE, related_name="company_holdings")
    transaction = models.ForeignKey('ClaimActionTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='transaction_holdings')
    
    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Actions Holdings'
        verbose_name_plural = 'Actions Holdings'

class ClassActionLawsuit(models.Model):
    tycker_symbol = models.CharField(max_length=255, null=True, blank=True)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    quantity_stock = models.IntegerField(null=False, blank=False)
    value_per_stock = models.DecimalField(max_digits=24, decimal_places=4, null=False, blank=False)
    amount = models.DecimalField(max_digits=24, decimal_places=4, null=False, blank=False)
    claim_date = models.CharField(max_length=255, null=True, blank=True)
    status = models.TextField(null=True, blank=True)
    send_format = models.BooleanField(default=False, null=False, blank=True)
    accept_claim = models.BooleanField(default=False, null=False, blank=True)
    register_payment = models.BooleanField(default=False, null=False, blank=True)
    user = models.ForeignKey(USER_MODEL, blank=False, null=False, on_delete=models.CASCADE, related_name='class_actions_lawsuits')
    company = models.ForeignKey(Company,  null=True, blank=True, on_delete=models.CASCADE, related_name="class_actions_lawsuits")
    holding = models.ForeignKey(ActionsHoldings, null=True, blank=True, on_delete=models.CASCADE, related_name="class_actions_lawsuits")
    claim = models.ForeignKey(ClaimAction, null=True, blank=True, on_delete=models.CASCADE, related_name="class_actions_lawsuits" )
    
    def __str__(self) -> str:
        return self.tycker_symbol

    class Meta:
        verbose_name = "Class Action Lawsuit"
        verbose_name_plural = "Class Action Lawsuits"


class ClaimActionTransaction(models.Model):
    data_for = models.CharField(max_length=255, null=True, blank=True)
    trade_date = models.CharField(max_length=30, null=True, blank=True)
    account = models.CharField(max_length=255, null=True, blank=True)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    account_type = models.CharField(max_length=10, null=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    activity = models.CharField(max_length=60, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    symbol = models.CharField(max_length=20, null=True, blank=True)
    quantity = models.IntegerField(null=False, blank=False)
    amount = models.DecimalField(max_digits=24, decimal_places=4, null=False, blank=False)
    cost_per_stock = models.DecimalField(max_digits=24, decimal_places=4, null=False, blank=False)
    notes = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    company = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(USER_MODEL, null=True, on_delete=models.CASCADE, related_name='claim_actions_transactions')

    def __str__(self) -> str:
        return self.data_for

    class Meta:
        verbose_name = 'Claim Action Transaction'
        verbose_name_plural = 'Claim Action Transactions'


class ImportLog(models.Model):
    class StatusChoices(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        ERROR = 'ERROR', 'Error'

    import_job_id = models.UUIDField(default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=StatusChoices.choices)
    row_number = models.PositiveIntegerField()
    error_message = models.TextField(blank=True, null=True)
    row_data = models.JSONField(blank=True, null=True)
    user = models.ForeignKey(USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Job {self.import_job_id} - Row {self.row_number} - {self.status}"

    class Meta:
        verbose_name = 'Import Log'
        verbose_name_plural = 'Import Logs'
