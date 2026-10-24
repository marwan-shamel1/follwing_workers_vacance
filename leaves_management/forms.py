from django import forms
from django.contrib.auth.models import User
from .models import CivilianWorker, LeaveRequest, UserProfile

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = [
            'worker',
            'applicant_name',
            'applicant_job',
            'applicant_department',
            'applicant_phone',
            'leave_type',
            'start_date',
            'end_date',
            'days_count',
            'permission_hours',
            'reason',
            'address_during_leave',
            'substitute_worker',
        ]
        widgets = {
            'worker': forms.HiddenInput(),
            'applicant_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'applicant_job': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'applicant_department': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'applicant_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم هاتف للتواصل'}),
            'leave_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_leave_type'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_start_date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_end_date'}),
            'days_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'id': 'id_days_count'}),
            'permission_hours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: ساعتان (من 10 ص إلى 12 م)', 'id': 'id_permission_hours'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'سبب الإجازة أو الغرض منها'}),
            'address_during_leave': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'محل الإقامة والتواجد أثناء الإجازة'}),
            'substitute_worker': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الزميل القائم بالعمل أثناء الإجازة'}),
        }


class ManagerLeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = [
            'applicant_name',
            'applicant_job',
            'applicant_department',
            'applicant_phone',
            'leave_type',
            'start_date',
            'end_date',
            'days_count',
            'permission_hours',
            'reason',
            'address_during_leave',
            'substitute_worker',
        ]
        widgets = {
            'applicant_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'applicant_job': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'applicant_department': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'applicant_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم هاتف للتواصل'}),
            'leave_type': forms.Select(attrs={'class': 'form-select', 'id': 'mgr_leave_type'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'mgr_start_date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'mgr_end_date'}),
            'days_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'id': 'mgr_days_count'}),
            'permission_hours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: ساعتان', 'id': 'mgr_permission_hours'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'سبب طلب الإجازة'}),
            'address_during_leave': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'العنوان أثناء الإجازة'}),
            'substitute_worker': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم القائم بالعمل'}),
        }


class CivilianWorkerForm(forms.ModelForm):
    class Meta:
        model = CivilianWorker
        fields = [
            'name',
            'job_title',
            'national_id',
            'employee_code',
            'department',
            'phone',
            'address',
            'hire_date',
            'notes',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الرباعي للعامل'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الوظيفة أو الحرفة'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الرقم القومي (14 رقم)', 'maxlength': '14'}),
            'employee_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم السجل / كود العامل'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الورشة / القسم / الشعبة'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف المحمول'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'محل الإقامة'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'أي ملاحظات إضافية'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserProfileUpdateForm(forms.ModelForm):
    new_username = forms.CharField(max_length=150, required=False, label="اسم المستخدم الجديد", widget=forms.TextInput(attrs={'class': 'form-control'}))
    new_password = forms.CharField(max_length=128, required=False, label="كلمة المرور الجديدة (اتركها فارغة إذا لم ترغب في التغيير)", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(max_length=128, required=False, label="تأكيد كلمة المرور", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = UserProfile
        fields = ['full_name', 'job_title', 'department', 'phone', 'avatar']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("كلمتا المرور غير متطابقتين.")
        return cleaned_data
