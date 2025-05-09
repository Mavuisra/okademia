from django.urls import path, re_path
from . import views
from . import secure_views
from . import notifications
from .offline_views import synchronize_offline_data, offline_queue_status

app_name = 'belletin'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Offline page
    path('offline/', views.offline_view, name='offline'),
    
    # Admin Dashboard 
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Faculty
    path('faculty/', views.faculty_list, name='faculty_list'),
    path('faculty/create/', views.faculty_create, name='faculty_create'),
    
    # Department
    path('department/', views.department_list, name='department_list'),
    path('department/create/', views.department_create, name='department_create'),
    
    # Student
    path('student/', views.student_list, name='student_list'),
    path('student/<int:pk>/', views.student_detail, name='student_detail'),
    path('student/create/', views.student_create, name='student_create'),
    
    # Grade
    path('grade/create/<int:student_id>/<int:ue_id>/', views.grade_create, name='grade_create'),
    
    # UE
    path('ue/', views.ue_list, name='ue_list'),
    path('ue/create/', views.ue_create, name='ue_create'),
    
    # Report
    path('report/generate/<int:student_id>/<int:year_id>/', views.generate_annual_report, name='generate_annual_report'),
    
    # Professor
    path('professor/dashboard/', views.professor_dashboard, name='professor_dashboard'),
    path('professor/course/<int:course_id>/quick-grade/', views.quick_grade, name='quick_grade'),
    path('professor/course/<int:course_id>/grade/<int:student_id>/', views.grade_detail, name='grade_detail'),
    path('professor/grades/', views.professor_grades, name='professor_grades'),
    
    # API
    path('api/search-students/<int:course_id>/', views.api_search_students, name='api_search_students'),
    
    # Jury Dashboard
    path('jury/dashboard/', views.jury_dashboard, name='jury_dashboard'),
    path('jury/deliberations/', views.jury_deliberations_list, name='jury_deliberations_list'),
    path('jury/deliberation/create/', views.jury_create_deliberation, name='jury_create_deliberation'),
    
    # Routes sécurisées avec tokens chiffrés
    # Le pattern accepte des chaînes alphanumériques avec des caractères spéciaux, typiques d'un token encoded+signé
    re_path(r'^jury/deliberation/(?P<deliberation_token>[A-Za-z0-9_\-\.=]+)/$', 
            secure_views.jury_deliberation_detail, name='jury_deliberation_detail'),
    
    re_path(r'^jury/deliberation/(?P<deliberation_token>[A-Za-z0-9_\-\.=]+)/student/(?P<student_token>[A-Za-z0-9_\-\.=]+)/$', 
            secure_views.jury_student_detail, name='jury_student_detail'),
    
    re_path(r'^jury/deliberation/(?P<deliberation_token>[A-Za-z0-9_\-\.=]+)/bulk-decision/$', 
            secure_views.jury_bulk_decision, name='jury_bulk_decision'),
    
    re_path(r'^jury/deliberation/(?P<deliberation_token>[A-Za-z0-9_\-\.=]+)/complete/$', 
            secure_views.jury_complete_deliberation, name='jury_complete_deliberation'),
    
    re_path(r'^jury/deliberation/(?P<deliberation_token>[A-Za-z0-9_\-\.=]+)/export-pv/$', 
            secure_views.jury_export_pv, name='jury_export_pv'),
    
    re_path(r'^jury/deliberation/(?P<deliberation_token>[A-Za-z0-9_\-\.=]+)/export-data/$', 
            secure_views.jury_export_data, name='jury_export_data'),
    
    # Student Bulletin
    path('student/bulletin/', views.student_bulletin, name='student_bulletin'),
    
    re_path(r'^student/bulletin/(?P<deliberation_token>[A-Za-z0-9_\-\.=]+)/download/$', 
            secure_views.student_download_bulletin, name='student_download_bulletin'),
    
    re_path(r'^student/bulletin/(?P<deliberation_token>[A-Za-z0-9_\-\.=]+)/coupon/$', 
            secure_views.student_download_bulletin_coupon, name='student_download_bulletin_coupon'),
    
    # URLs Admin pour la promotion des étudiants
    path('admin/new-academic-year/', views.admin_new_academic_year, name='admin_new_academic_year'),
    path('admin/promote-students/<int:year_id>/', views.admin_promote_students, name='admin_promote_students'),
    
    # Notifications Push
    path('notifications/', notifications.notifications_settings, name='notifications'),
    path('notifications/<int:notification_id>/read/', notifications.mark_notification_read, name='mark_notification_read'),
    path('notifications/<int:notification_id>/delete/', notifications.delete_notification, name='delete_notification'),
    path('notifications/mark-all-read/', notifications.mark_all_read, name='mark_all_read'),
    path('notifications/clear-all/', notifications.clear_all_notifications, name='clear_all_notifications'),
    path('notifications/test/', notifications.send_test_notification, name='send_test_notification'),
    
    # API Notifications Push
    path('api/push/vapid-public-key/', notifications.vapid_public_key, name='vapid_public_key'),
    path('api/push/subscription/', notifications.subscription, name='push_subscription'),
    path('api/push/subscription/delete/', notifications.delete_subscription, name='delete_push_subscription'),
    path('api/push/update-status/', notifications.update_subscription_status, name='update_subscription_status'),
    path('api/push/preferences/', notifications.update_preferences, name='update_notification_preferences'),
    path('api/notifications/<int:notification_id>/read/', notifications.mark_notification_read, name='api_mark_notification_read'),
    
    # URLs for offline functionality
    path('api/synchronize-offline-data/', synchronize_offline_data, name='synchronize_offline_data'),
    path('offline/status/', offline_queue_status, name='offline_queue_status'),
] 