from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from .models import (
    UserProfile, 
    CivilianWorker, 
    LeaveRequest, 
    get_current_leave_year_info
)

class MilitaryLeavesSystemTests(TestCase):

    def setUp(self):
        self.client = Client()

        # 1. Setup Worker User
        self.worker_user = User.objects.create_user(username='مدنى', password='مدنى')
        self.worker_profile = UserProfile.objects.create(
            user=self.worker_user,
            role='worker',
            full_name='بوابة العامل المدني',
            job_title='بوابة خدمة العاملين المدنيين'
        )

        # 2. Setup HR Manager User
        self.hr_user = User.objects.create_user(username='مدير شئون العاملين', password='1234')
        self.hr_profile = UserProfile.objects.create(
            user=self.hr_user,
            role='hr_manager',
            full_name='محمود أحمد حسن',
            job_title='مدير إدارة شؤون العاملين المدنيين'
        )

        # 3. Setup Commander User
        self.commander_user = User.objects.create_user(username='مدير المنطقة', password='0000')
        self.commander_profile = UserProfile.objects.create(
            user=self.commander_user,
            role='commander',
            full_name='السيد العميد أ ح / عبدالحميد محمد سلامة',
            job_title='مدير المنطقة'
        )

        # 4. Setup Civilian Worker
        self.worker = CivilianWorker.objects.create(
            name='أحمد محمود إبراهيم',
            job_title='فني ميكانيكا ديزل',
            national_id='28503120104512',
            employee_code='CIV-1001',
            department='ورشة الصيانة الميكانيكية المركزية',
            phone='01012345671'
        )

    def test_leave_year_calculation(self):
        # Date in October 2026 -> Leave year 2026/2027 (starts 2026-07-01, ends 2027-06-30)
        oct_date = date(2026, 10, 23)
        year_str, start_d, end_d = get_current_leave_year_info(oct_date)
        self.assertEqual(year_str, '2026/2027')
        self.assertEqual(start_d, date(2026, 7, 1))
        self.assertEqual(end_d, date(2027, 6, 30))

        # Date in May 2026 -> Leave year 2025/2026 (starts 2025-07-01, ends 2026-06-30)
        may_date = date(2026, 5, 10)
        year_str_may, start_d_may, end_d_may = get_current_leave_year_info(may_date)
        self.assertEqual(year_str_may, '2025/2026')
        self.assertEqual(start_d_may, date(2025, 7, 1))
        self.assertEqual(end_d_may, date(2026, 6, 30))

    def test_worker_login_and_api(self):
        login_success = self.client.login(username='مدنى', password='مدنى')
        self.assertTrue(login_success)

        # Fetch worker summary API
        response = self.client.get(reverse('api_worker_summary', kwargs={'worker_id': self.worker.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['worker']['name'], self.worker.name)
        self.assertEqual(data['summary']['regular']['quota'], 30)
        self.assertEqual(data['summary']['regular']['remaining'], 30)
        self.assertEqual(data['summary']['casual']['quota'], 7)
        self.assertEqual(data['summary']['permission']['quota'], 2)

    def test_worker_leave_submission_workflow(self):
        self.client.login(username='مدنى', password='مدنى')
        today = timezone.localdate()
        
        post_data = {
            'worker_id': self.worker.id,
            'leave_type': 'regular',
            'start_date': (today + timedelta(days=2)).isoformat(),
            'end_date': (today + timedelta(days=5)).isoformat(),
            'days_count': 4,
            'applicant_phone': '01012345671',
            'reason': 'ظروف عائلية خاصة',
            'substitute_worker': 'محمد علي',
            'address_during_leave': 'محل الإقامة بالإسماعيلية'
        }
        response = self.client.post(reverse('worker_dashboard'), post_data)
        self.assertEqual(response.status_code, 302)

        # Check request created with pending status
        leave_req = LeaveRequest.objects.get(applicant_name=self.worker.name)
        self.assertEqual(leave_req.hr_status, 'pending')
        self.assertEqual(leave_req.commander_status, 'pending')
        self.assertEqual(leave_req.days_count, 4)

        # HR Manager logs in and endorses request
        self.client.logout()
        self.client.login(username='مدير شئون العاملين', password='1234')
        endorse_response = self.client.post(
            reverse('hr_endorse_request', kwargs={'request_id': leave_req.id}),
            {'hr_notes': 'تم التأكد من الرصيد والبديل'}
        )
        self.assertEqual(endorse_response.status_code, 302)
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.hr_status, 'endorsed')
        self.assertTrue(leave_req.is_endorsed_today)

        # Commander logs in and approves request
        self.client.logout()
        self.client.login(username='مدير المنطقة', password='0000')
        decide_response = self.client.post(
            reverse('commander_decide', kwargs={'request_id': leave_req.id}),
            {'decision': 'approve', 'commander_notes': 'يصدق بعد التنسيق'}
        )
        self.assertEqual(decide_response.status_code, 302)
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.commander_status, 'approved')

        # Balance check after approval: 30 - 4 = 26 remaining
        summary = self.worker.get_leaves_summary()
        self.assertEqual(summary['regular']['taken'], 4)
        self.assertEqual(summary['regular']['remaining'], 26)

    def test_hr_add_worker(self):
        self.client.login(username='مدير شئون العاملين', password='1234')
        post_data = {
            'name': 'محمود سمير عبد القادر',
            'job_title': 'كهربائي سيارات',
            'national_id': '29505121402234',
            'employee_code': 'CIV-1008',
            'department': 'ورشة الصيانة الكهربائية',
            'phone': '01122334455',
            'address': 'السويس',
            'hire_date': '2020-01-01',
            'is_active': True
        }
        response = self.client.post(reverse('hr_manage_workers'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CivilianWorker.objects.filter(national_id='29505121402234').exists())

    def test_commander_all_leaves_search(self):
        self.client.login(username='مدير المنطقة', password='0000')
        response = self.client.get(reverse('commander_all_leaves'), {'search': 'أحمد محمود'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'أحمد محمود إبراهيم')
        self.assertContains(response, 'فني ميكانيكا ديزل')
