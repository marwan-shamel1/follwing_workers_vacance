from django.utils import timezone
from .models import get_current_leave_year_info, LeaveRequest

def system_context(request):
    leave_year, start_d, end_d = get_current_leave_year_info()
    
    pending_hr_count = 0
    pending_commander_count = 0
    profile = None

    if request.user.is_authenticated:
        try:
            profile = request.user.profile
        except Exception:
            profile = None

        pending_hr_count = LeaveRequest.objects.filter(hr_status='pending').count()
        pending_commander_count = LeaveRequest.objects.filter(hr_status='endorsed', commander_status='pending').count()

    return {
        'system_title': 'منظومة متابعة إجازات العاملين المدنيين',
        'military_command': 'القوات المسلحة المصرية - قيادة المنطقة العسكرية',
        'unit_branch': 'فرع شؤون العاملين المدنيين',
        'current_leave_year': leave_year,
        'leave_year_start': start_d,
        'leave_year_end': end_d,
        'today_date': timezone.localdate(),
        'user_profile': profile,
        'pending_hr_count': pending_hr_count,
        'pending_commander_count': pending_commander_count,
    }
