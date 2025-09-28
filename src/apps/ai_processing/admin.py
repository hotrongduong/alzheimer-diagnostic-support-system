from django.contrib import admin
from .models import AIModel, AIReport, ReviewSession

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'model_version', 'created_at')
    search_fields = ('model_name', 'description')

@admin.register(AIReport)
class AIReportAdmin(admin.ModelAdmin):
    list_display = ('report_id', 'study', 'model', 'created_at')
    list_filter = ('model', 'created_at')
    search_fields = ('study__patient__full_name', 'report_id')

@admin.register(ReviewSession)
class ReviewSessionAdmin(admin.ModelAdmin):
    list_display = ('report', 'user', 'reviewer_status', 'reviewed_at')
    list_filter = ('reviewer_status', 'user')
    search_fields = ('report__report_id', 'user__username')