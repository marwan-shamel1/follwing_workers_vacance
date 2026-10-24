import os
import sys
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from leaves_management.models import UserProfile, CivilianWorker, LeaveRequest, get_current_leave_year_info

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


class Command(BaseCommand):
    help = 'Initialize default military leave management system accounts and sample civilian workers'

    def handle(self, *args, **options):
        self.stdout.write("Initializing system users and seed data...")

        # 1. User: Civilian Worker Portal (مدنى / مدنى)
        worker_user, created = User.objects.get_or_create(username='مدنى')
        worker_user.set_password('مدنى')
        worker_user.save()
        UserProfile.objects.update_or_create(
            user=worker_user,
            defaults={
                'role': 'worker',
                'full_name': 'بوابة العامل المدني',
                'job_title': 'بوابة خدمة العاملين المدنيين',
                'department': 'فرع شؤون العاملين المدنيين',
                'phone': '01000000001'
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Civilian Worker account (مدنى / مدنى) verified."))

        # Also create alias user 'مدني' in case
        alias_worker, _ = User.objects.get_or_create(username='مدني')
        alias_worker.set_password('مدني')
        alias_worker.save()
        UserProfile.objects.update_or_create(
            user=alias_worker,
            defaults={
                'role': 'worker',
                'full_name': 'بوابة العامل المدني',
                'job_title': 'بوابة خدمة العاملين المدنيين',
                'department': 'فرع شؤون العاملين المدنيين',
                'phone': '01000000001'
            }
        )

        # 2. User: HR Manager (مدير شئون العاملين / 1234)
        hr_user, created = User.objects.get_or_create(username='مدير شئون العاملين')
        hr_user.set_password('1234')
        hr_user.is_staff = True
        hr_user.save()
        UserProfile.objects.update_or_create(
            user=hr_user,
            defaults={
                'role': 'hr_manager',
                'full_name': 'الأستاذ / محمود أحمد حسن',
                'job_title': 'مدير إدارة شؤون العاملين المدنيين',
                'department': 'فرع شؤون العاملين المدنيين',
                'phone': '01123456789'
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] HR Manager account (مدير شئون العاملين / 1234) verified."))

        # 3. User: Commander (مدير المنطقة / 0000)
        commander_user, created = User.objects.get_or_create(username='مدير المنطقة')
        commander_user.set_password('0000')
        commander_user.is_staff = True
        commander_user.is_superuser = True
        commander_user.save()
        UserProfile.objects.update_or_create(
            user=commander_user,
            defaults={
                'role': 'commander',
                'full_name': 'السيد العميد أ ح / عبدالحميد محمد سلامة',
                'job_title': 'مدير المنطقة',
                'department': 'قيادة المنطقة العسكرية',
                'phone': '01234567890'
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Commander account (مدير المنطقة / 0000) verified."))

        # 4. Seed Civilian Workers
        workers_data = [
            {
                'name': 'أحمد محمود إبراهيم السيد',
                'job_title': 'فني ميكانيكا ديزل ومحركات',
                'national_id': '28503120104512',
                'employee_code': 'CIV-1001',
                'department': 'ورشة الصيانة الميكانيكية المركزية',
                'phone': '01012345671',
                'address': 'الإسماعيلية - حي السلام',
                'hire_date': date(2014, 5, 10),
            },
            {
                'name': 'محمد حسن علي عثمان',
                'job_title': 'كاتب سكرتارية وتنظيم أول',
                'national_id': '29011151203498',
                'employee_code': 'CIV-1002',
                'department': 'شعبة التنظيم والإدارة والشؤون العامة',
                'phone': '01198765432',
                'address': 'السويس - حي الأربعين',
                'hire_date': date(2017, 9, 1),
            },
            {
                'name': 'إبراهيم مصطفى خليل الدسوقي',
                'job_title': 'كهربائي قوى ومولدات طوارئ',
                'national_id': '28704200109987',
                'employee_code': 'CIV-1003',
                'department': 'محطة القدرة الكهربائية وشبكات التغذية',
                'phone': '01233445566',
                'address': 'الشرقية - الزقازيق',
                'hire_date': date(2015, 3, 15),
            },
            {
                'name': 'خالد عبد الفتاح رضوان منصور',
                'job_title': 'سائق نقل ثقيل ومعدات درجة أولى',
                'national_id': '28108051402231',
                'employee_code': 'CIV-1004',
                'department': 'سرايا النقل والمركبات التكتيكية',
                'phone': '01055667788',
                'address': 'القاهرة - المرج',
                'hire_date': date(2011, 11, 20),
            },
            {
                'name': 'طارق كمال الدين عبد العال',
                'job_title': 'فني تشغيل مخارط ومصنعات حديدية',
                'national_id': '29302181604567',
                'employee_code': 'CIV-1005',
                'department': 'ورشة الخراطة والحدادة والإنتاج',
                'phone': '01144556677',
                'address': 'بورسعيد - حي المناخ',
                'hire_date': date(2019, 2, 1),
            },
            {
                'name': 'سامح رشاد توفيق غانم',
                'job_title': 'مهندس مدني منشآت وصيانة مرافق',
                'national_id': '28906250106789',
                'employee_code': 'CIV-1006',
                'department': 'فرع الأشغال العسكرية والهندسية',
                'phone': '01288990011',
                'address': 'الإسماعيلية - الشيخ زايد',
                'hire_date': date(2016, 7, 15),
            },
            {
                'name': 'ياسر فوزي عبد الغني النجار',
                'job_title': 'أمين مخزن قطع غيار ومهمات فنية',
                'national_id': '28409101803321',
                'employee_code': 'CIV-1007',
                'department': 'مستودع التعيينات والمهمات الفنية',
                'phone': '01077889900',
                'address': 'القاهرة - حلوان',
                'hire_date': date(2013, 8, 25),
            }
        ]

        created_workers = []
        for w_data in workers_data:
            w, created = CivilianWorker.objects.update_or_create(
                national_id=w_data['national_id'],
                defaults=w_data
            )
            created_workers.append(w)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(created_workers)} Civilian Workers seeded."))

        # 5. Create realistic sample leave requests
        leave_year, _, _ = get_current_leave_year_info()
        today = timezone.localdate()

        # Worker 1: Ahmed Mahmoud -> Approved Regular Leave (5 days)
        w1 = created_workers[0]
        LeaveRequest.objects.get_or_create(
            worker=w1,
            start_date=today - timedelta(days=25),
            end_date=today - timedelta(days=21),
            defaults={
                'applicant_name': w1.name,
                'applicant_job': w1.job_title,
                'applicant_department': w1.department,
                'applicant_phone': w1.phone,
                'leave_type': 'regular',
                'days_count': 5,
                'leave_year': leave_year,
                'reason': 'قضاء ظروف عائلية والتزامات شخصية',
                'address_during_leave': 'محل الإقامة بالإسماعيلية',
                'substitute_worker': 'إبراهيم مصطفى خليل',
                'hr_status': 'endorsed',
                'hr_endorsed_at': timezone.now() - timedelta(days=26),
                'hr_endorsed_by': 'محمود أحمد حسن (مدير شئون العاملين)',
                'hr_notes': 'رصيد العامل يسمح وتم التنسيق مع رئيس الورشة',
                'commander_status': 'approved',
                'commander_decided_at': timezone.now() - timedelta(days=26),
                'commander_decided_by': 'السيد العميد أ ح / عبدالحميد محمد سلامة',
                'commander_notes': 'يصدق بعد التنسيق التام في نوبتجية الصيانة'
            }
        )

        # Worker 1: Casual Leave (2 days)
        LeaveRequest.objects.get_or_create(
            worker=w1,
            start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=9),
            defaults={
                'applicant_name': w1.name,
                'applicant_job': w1.job_title,
                'applicant_department': w1.department,
                'applicant_phone': w1.phone,
                'leave_type': 'casual',
                'days_count': 2,
                'leave_year': leave_year,
                'reason': 'ظرف عائلي طارئ',
                'address_during_leave': 'محل الإقامة بالإسماعيلية',
                'substitute_worker': 'إبراهيم مصطفى خليل',
                'hr_status': 'endorsed',
                'hr_endorsed_at': timezone.now() - timedelta(days=11),
                'hr_endorsed_by': 'محمود أحمد حسن (مدير شئون العاملين)',
                'hr_notes': 'تم التأكد من استحقاق العارضة',
                'commander_status': 'approved',
                'commander_decided_at': timezone.now() - timedelta(days=10),
                'commander_decided_by': 'السيد العميد أ ح / عبدالحميد محمد سلامة',
                'commander_notes': 'يصدق'
            }
        )

        # Worker 2: Mohammad Hassan -> Pending HR manager approval (New incoming request)
        w2 = created_workers[1]
        LeaveRequest.objects.get_or_create(
            worker=w2,
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=5),
            defaults={
                'applicant_name': w2.name,
                'applicant_job': w2.job_title,
                'applicant_department': w2.department,
                'applicant_phone': w2.phone,
                'leave_type': 'regular',
                'days_count': 4,
                'leave_year': leave_year,
                'reason': 'إجازة اعتيادية لحضور مناسبة عائلية وإجراء معاملات بنكية',
                'address_during_leave': 'السويس - حي الأربعين',
                'substitute_worker': 'سامح رشاد توفيق',
                'hr_status': 'pending',
                'commander_status': 'pending',
            }
        )

        # Worker 3: Ibrahim Mustafa -> Endorsed by HR today, Pending Commander Approval!
        w3 = created_workers[2]
        LeaveRequest.objects.get_or_create(
            worker=w3,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=3),
            defaults={
                'applicant_name': w3.name,
                'applicant_job': w3.job_title,
                'applicant_department': w3.department,
                'applicant_phone': w3.phone,
                'leave_type': 'regular',
                'days_count': 3,
                'leave_year': leave_year,
                'reason': 'مرافقة والدتي لإجراء فحوصات طبية تخصصية',
                'address_during_leave': 'الشرقية - الزقازيق',
                'substitute_worker': 'أحمد محمود إبراهيم',
                'hr_status': 'endorsed',
                'hr_endorsed_at': timezone.now(),  # Today!
                'hr_endorsed_by': 'محمود أحمد حسن (مدير شئون العاملين)',
                'hr_notes': 'الرصيد الاعتيادي يسمح (متبقي 30 يوم) وتم تعيين بديل فني',
                'commander_status': 'pending',
            }
        )

        # Worker 4: Khalid Abdel Fattah -> Hospital leave (مستشفى 4 أيام)
        w4 = created_workers[3]
        LeaveRequest.objects.get_or_create(
            worker=w4,
            start_date=today - timedelta(days=15),
            end_date=today - timedelta(days=12),
            defaults={
                'applicant_name': w4.name,
                'applicant_job': w4.job_title,
                'applicant_department': w4.department,
                'applicant_phone': w4.phone,
                'leave_type': 'hospital',
                'days_count': 4,
                'leave_year': leave_year,
                'reason': 'دخول المستشفى العسكري لإجراء جراحة صغرى بالركبة',
                'address_during_leave': 'المستشفى العسكري العام',
                'substitute_worker': 'طارق كمال الدين',
                'hr_status': 'endorsed',
                'hr_endorsed_at': timezone.now() - timedelta(days=16),
                'hr_endorsed_by': 'محمود أحمد حسن (مدير شئون العاملين)',
                'commander_status': 'approved',
                'commander_decided_at': timezone.now() - timedelta(days=15),
                'commander_decided_by': 'السيد العميد أ ح / عبدالحميد محمد سلامة',
                'commander_notes': 'مع تمنياتنا بالشفاء العاجل وموافاتنا بتقرير الخروج'
            }
        )

        self.stdout.write(self.style.SUCCESS("[OK] Sample leave requests and workflows initialized successfully."))
