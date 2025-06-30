from django.db import models
from django.contrib.auth import get_user_model


USER_MODEL = get_user_model()


class AssetCategory(models.Model):
    category_name = models.CharField(max_length=100, null=False, blank=False)
    attributes = models.JSONField(null=True, blank=True)


    def __str__(self) -> str:
        return self.category_name
    
    class Meta:
        verbose_name = "Asset Category"
        verbose_name_plural = "Assets Categories"


class Asset(models.Model):
    owner = models.ForeignKey(USER_MODEL, 
                              on_delete=models.CASCADE, 
                              related_name='chat_asset')
    name = models.CharField(max_length=250)
    value = models.CharField(max_length=30, null=True, blank=True)
    value_over_time = models.CharField(max_length=50, null=True, blank=True)
    photo = models.ImageField(upload_to='assets_photos/', null=True, blank=True)
    syntasis_summary = models.TextField(blank=True, null=True)
    full_conversation_history = models.TextField(blank=True, null=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE, blank=True, null=True)
    attributes = models.JSONField(null=True, blank=True)
    asset_date = models.DateField(null=True, blank=True, auto_now=True)

    def __str__(self) -> str:
        return self.name
    
    class Meta:
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'


class ClaimAction(models.Model):
    tycker_symbol = models.CharField(max_length=255, null=True, blank=True)
    company_name = models.TextField(null=True, blank=True)
    exchange = models.TextField(null=True, blank=True)
    lawsuit_type = models.TextField(null=True, blank=True)
    eligibility	= models.CharField(max_length=255, null=True, blank=True)
    potencial_claim	= models.CharField(max_length=255, null=True, blank=True)
    total_settlement_fund = models.CharField(max_length=255, null=True, blank=True)
    filing_date = models.CharField(max_length=255, null=True, blank=True)
    claim_deadline = models.CharField(max_length=255, null=True, blank=True)
    law_firm_handing_case = models.CharField(max_length=255, null=True, blank=True)
    case_docket_number = models.CharField(max_length=255, null=True, blank=True)
    jurisdiction = models.CharField(max_length=255, null=True, blank=True)
    claim_status = models.CharField(max_length=255, null=True, blank=True)
    official_claim_filing_link = models.CharField(max_length=255, null=True, blank=True)
    last_update = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self) -> str:
        return self.tycker_symbol
    
    class Meta:
        verbose_name = "Claim Action"
        verbose_name_plural = "Claim Actions"


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
    quantity = models.CharField(max_length=255, null=True, blank=True) 
    amount = models.CharField(max_length=255, null=True, blank=True) 
    notes = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    company = models.CharField(max_length=255, null=True, blank=True)
    user = models.CharField(max_length=255, null=True, blank=True)
    

    def __str__(self) -> str:
        return self.data_for
    
    class Meta:
        verbose_name = 'Claim Action Transaction'
        verbose_name_plural = 'Claim Action Transactions'


