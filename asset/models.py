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
    acquisition_value = models.CharField(max_length=30, null=True, blank=True)
    estimated_value = models.CharField(max_length=50, null=False, blank=False, default='0')
    low_value = models.CharField(max_length=50, null=True, blank=True)
    high_value = models.CharField(max_length=50, null=True, blank=True)
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

