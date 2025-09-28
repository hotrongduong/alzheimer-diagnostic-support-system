from django.contrib import admin
from .models import Patient, FileUpload, DICOMStudy

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'date_of_birth', 'patient_id', 'created_at')
    search_fields = ('full_name', 'patient_id')

@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'patient', 'user', 'status', 'uploaded_at')
    list_filter = ('status', 'file_format', 'uploaded_at')
    search_fields = ('original_filename', 'patient__full_name')

@admin.register(DICOMStudy)
class DICOMStudyAdmin(admin.ModelAdmin):
    list_display = ('patient', 'study_description', 'study_date', 'orthanc_study_id')
    search_fields = ('patient__full_name', 'study_description', 'orthanc_study_id')