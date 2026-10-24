from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

def get_current_leave_year_info(target_date=None):
    """
    Military leave year begins on July 1st of the current year and ends on June 30th of the next year.
    (السنة تبدأ من شهر سبعة في السنة لشهر 7 في السنة التالية)
    """
    if target_date is None:
        target_date = timezone.localdate()
    
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    if target_date.month >= 7:
        start_year = target_date.year
        end_year = target_date.year + 1
    else:
        start_year = target_date.year - 1
        end_year = target_date.year
        
    year_label = f"{start_year}/{end_year}"
    start_date = date(start_year, 7, 1)
    end_date = date(end_year, 6, 30)
    return year_label, start_date, end_date


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('worker', 'العامل المدني'),
        ('hr_manager', 'مدير شئون العاملين'),
        ('commander', 'مدير المنطقة (العميد)'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="نوع الحساب")
    full_name = models.CharField(max_length=150, verbose_name="الاسم بالكامل")
    job_title = models.CharField(max_length=150, verbose_name="الوظيفة / المنصب")
    department = models.CharField(max_length=150, default="قيادة المنطقة العسكرية", verbose_name="القسم / الوحدة")
    phone = models.CharField(max_length=20, blank=True, verbose_name="رقم الهاتف")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="الصورة الشخصية")

    class Meta:
        verbose_name = "ملف المستخدم"
        verbose_name_plural = "ملفات المستخدمين"

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


class CivilianWorker(models.Model):
    name = models.CharField(max_length=150, verbose_name="اسم العامل المدني الرباعي")
    job_title = models.CharField(max_length=150, verbose_name="الوظيفة / الحرفة")
    national_id = models.CharField(max_length=14, unique=True, verbose_name="الرقم القومي")
    employee_code = models.CharField(max_length=50, blank=True, verbose_name="كود العامل / رقم السجل")
    department = models.CharField(max_length=150, default="الورش الإنتاجية والصيانة", verbose_name="الورشة / القسم / الشعبة")
    phone = models.CharField(max_length=20, blank=True, verbose_name="رقم الهاتف")
    address = models.CharField(max_length=250, blank=True, verbose_name="محل الإقامة")
    hire_date = models.DateField(default=date.today, verbose_name="تاريخ التعيين")
    is_active = models.BooleanField(default=True, verbose_name="على رأس العمل")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    class Meta:
        verbose_name = "عامل مدني"
        verbose_name_plural = "العاملون المدنيون"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.job_title}"

    def get_leaves_summary(self, leave_year=None):
        """
        Calculates leave tally for the employee:
        - اعتيادي: 30 days per year (1 July to 30 June)
        - عارضة: 7 days per year
        - إذن: 2 permissions per year
        - مستشفى: tally of days
        - مرضي: tally of days
        - مأمورية: tally of days
        """
        if not leave_year:
            leave_year, _, _ = get_current_leave_year_info()

        # Query all approved leave requests for this leave year
        requests_year = self.leave_requests.filter(leave_year=leave_year)
        
        # We consider leaves approved by commander as fully taken
        approved_year = requests_year.filter(commander_status='approved')

        # Calculate counts
        regular_taken = sum(r.days_count for r in approved_year.filter(leave_type='regular'))
        casual_taken = sum(r.days_count for r in approved_year.filter(leave_type='casual'))
        permission_taken = approved_year.filter(leave_type='permission').count()
        hospital_taken = sum(r.days_count for r in approved_year.filter(leave_type='hospital'))
        sick_taken = sum(r.days_count for r in approved_year.filter(leave_type='sick'))
        mission_taken = sum(r.days_count for r in approved_year.filter(leave_type='mission'))

        # Pending count (for info)
        pending_count = requests_year.filter(commander_status='pending').exclude(hr_status='rejected').count()

        return {
            'leave_year': leave_year,
            'regular': {
                'quota': 30,
                'taken': regular_taken,
                'remaining': max(0, 30 - regular_taken),
                'percent': min(100, int((regular_taken / 30) * 100)) if 30 > 0 else 0
            },
            'casual': {
                'quota': 7,
                'taken': casual_taken,
                'remaining': max(0, 7 - casual_taken),
                'percent': min(100, int((casual_taken / 7) * 100)) if 7 > 0 else 0
            },
            'permission': {
                'quota': 2,
                'taken': permission_taken,
                'remaining': max(0, 2 - permission_taken),
                'percent': min(100, int((permission_taken / 2) * 100)) if 2 > 0 else 0
            },
            'hospital': {
                'taken': hospital_taken
            },
            'sick': {
                'taken': sick_taken
            },
            'mission': {
                'taken': mission_taken
            },
            'total_taken_all': regular_taken + casual_taken + hospital_taken + sick_taken + mission_taken,
            'pending_count': pending_count
        }


class LeaveRequest(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('regular', 'اعتيادي (متاح 30 يوماً بالسنة)'),
        ('casual', 'عارضة (متاح 7 أيام بالسنة)'),
        ('hospital', 'مستشفى'),
        ('sick', 'مرضي'),
        ('permission', 'إذن (متاح إذنان بالسنة)'),
        ('mission', 'مأمورية'),
    ]

    HR_STATUS_CHOICES = [
        ('pending', 'قيد انتظار تصديق شؤون العاملين'),
        ('endorsed', 'مصدق من مدير شؤون العاملين'),
        ('rejected', 'غير مصدق من شؤون العاملين'),
    ]

    COMMANDER_STATUS_CHOICES = [
        ('pending', 'قيد انتظار تصديق السيد العميد'),
        ('approved', 'مصدق ومعتمد من السيد العميد'),
        ('rejected', 'مرفوض من السيد العميد'),
    ]

    worker = models.ForeignKey(
        CivilianWorker, 
        on_delete=models.CASCADE, 
        related_name='leave_requests', 
        null=True, 
        blank=True,
        verbose_name="العامل المدني"
    )
    is_manager_request = models.BooleanField(default=False, verbose_name="طلب خاص بمدير شئون العاملين")

    # Snapshot of applicant info at request time
    applicant_name = models.CharField(max_length=150, verbose_name="اسم الموظف / العامل")
    applicant_job = models.CharField(max_length=150, verbose_name="الوظيفة")
    applicant_department = models.CharField(max_length=150, blank=True, verbose_name="القسم / الورشة")
    applicant_phone = models.CharField(max_length=20, blank=True, verbose_name="رقم الهاتف")

    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, verbose_name="نوع الإجازة")
    start_date = models.DateField(verbose_name="من تاريخ")
    end_date = models.DateField(verbose_name="إلى تاريخ")
    days_count = models.PositiveIntegerField(default=1, verbose_name="المدة بالأيام")
    permission_hours = models.CharField(max_length=50, blank=True, verbose_name="مدة الإذن بالساعات (إن وجد)")
    
    leave_year = models.CharField(max_length=20, verbose_name="السنة التأمينية / الإجازات (من 1/7 إلى 30/6)")
    reason = models.TextField(blank=True, verbose_name="سبب الإجازة / جهة التوجه")
    address_during_leave = models.CharField(max_length=250, blank=True, verbose_name="عنوان الإقامة أثناء الإجازة")
    substitute_worker = models.CharField(max_length=150, blank=True, verbose_name="القائم بالعمل بدلاً منه")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ تقديم الطلب")

    # HR Manager Decision
    hr_status = models.CharField(max_length=20, choices=HR_STATUS_CHOICES, default='pending', verbose_name="حالة مدير شئون العاملين")
    hr_endorsed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ تصديق شؤون العاملين")
    hr_endorsed_by = models.CharField(max_length=150, blank=True, verbose_name="اسم مصدق شؤون العاملين")
    hr_notes = models.TextField(blank=True, verbose_name="ملاحظات شؤون العاملين")

    # Area Commander Decision
    commander_status = models.CharField(max_length=20, choices=COMMANDER_STATUS_CHOICES, default='pending', verbose_name="حالة السيد العميد")
    commander_decided_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ قرار السيد العميد")
    commander_decided_by = models.CharField(max_length=150, default="السيد العميد أ ح / عبدالحميد محمد سلامة", verbose_name="اسم القائد المصدق")
    commander_notes = models.TextField(blank=True, verbose_name="توجيهات / ملاحظات السيد العميد")

    class Meta:
        verbose_name = "طلب إجازة"
        verbose_name_plural = "طلبات الإجازات"
        ordering = ['-created_at']

    def __str__(self):
        return f"طلب {self.get_leave_type_display()} - {self.applicant_name} ({self.days_count} يوم)"

    @property
    def is_endorsed_today(self):
        """Checks if this request was endorsed by HR manager today"""
        if self.hr_status == 'endorsed' and self.hr_endorsed_at:
            return self.hr_endorsed_at.date() == timezone.localdate()
        return False

    @property
    def composite_status(self):
        """High-level status for badges and tables"""
        if self.commander_status == 'approved':
            return {
                'code': 'approved',
                'label': 'مصدق ومعتمد نهائياً من السيد العميد',
                'badge_class': 'badge-success',
                'icon': 'fa-check-double'
            }
        elif self.commander_status == 'rejected':
            return {
                'code': 'rejected_commander',
                'label': 'مرفوض من السيد العميد',
                'badge_class': 'badge-danger',
                'icon': 'fa-times-circle'
            }
        elif self.hr_status == 'rejected':
            return {
                'code': 'rejected_hr',
                'label': 'غير مصدق من شؤون العاملين',
                'badge_class': 'badge-danger',
                'icon': 'fa-ban'
            }
        elif self.hr_status == 'endorsed':
            return {
                'code': 'endorsed_hr',
                'label': 'مصدق من شؤون العاملين - بانتظار تصديق السيد العميد',
                'badge_class': 'badge-warning',
                'icon': 'fa-hourglass-half'
            }
        else:
            return {
                'code': 'pending_hr',
                'label': 'قيد انتظار تصديق مدير شؤون العاملين',
                'badge_class': 'badge-info',
                'icon': 'fa-clock'
            }

    @property
    def leave_type_badge(self):
        mapping = {
            'regular': {'label': 'اعتيادي', 'color': 'primary'},
            'casual': {'label': 'عارضة', 'color': 'secondary'},
            'hospital': {'label': 'مستشفى', 'color': 'danger'},
            'sick': {'label': 'مرضي', 'color': 'warning'},
            'permission': {'label': 'إذن', 'color': 'info'},
            'mission': {'label': 'مأمورية', 'color': 'success'},
        }
        return mapping.get(self.leave_type, {'label': self.get_leave_type_display(), 'color': 'dark'})
