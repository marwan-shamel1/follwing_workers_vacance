from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='root'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Worker Portal
    path('worker/', views.worker_dashboard, name='worker_dashboard'),
    path('api/worker/<int:worker_id>/summary/', views.api_worker_summary, name='api_worker_summary'),

    # HR Manager Portal
    path('hr/', views.hr_dashboard, name='hr_dashboard'),
    path('hr/endorse/<int:request_id>/', views.hr_endorse_request, name='hr_endorse_request'),
    path('hr/reject/<int:request_id>/', views.hr_reject_request, name='hr_reject_request'),
    path('hr/today-endorsed/', views.hr_today_endorsed, name='hr_today_endorsed'),
    path('hr/all-approved/', views.hr_all_approved, name='hr_all_approved'),
    path('hr/workers/', views.hr_manage_workers, name='hr_manage_workers'),
    path('hr/workers/edit/<int:worker_id>/', views.hr_edit_worker, name='hr_edit_worker'),
    path('hr/workers/delete/<int:worker_id>/', views.hr_delete_worker, name='hr_delete_worker'),
    path('hr/manager-leave/', views.hr_manager_leave, name='hr_manager_leave'),
    path('hr/profile/', views.hr_profile, name='hr_profile'),

    # Commander Portal
    path('commander/', views.commander_dashboard, name='commander_dashboard'),
    path('commander/requests/', views.commander_requests, name='commander_requests'),
    path('commander/decide/<int:request_id>/', views.commander_decide, name='commander_decide'),
    path('commander/all-leaves/', views.commander_all_leaves, name='commander_all_leaves'),
    path('commander/profile/', views.commander_profile, name='commander_profile'),

    # Printable Official Permit
    path('leaves/print/<int:request_id>/', views.print_leave_order, name='print_leave_order'),
]
