from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views
urlpatterns = [
 path('', views.dashboard, name='dashboard'), path('login/', views.login_view, name='login'), path('logout/', LogoutView.as_view(), name='logout'),
 path('jenkins/', views.jenkins_list, name='jenkins_list'), path('jenkins/new/', views.configuration, {'kind':'jenkins'}, name='jenkins_new'), path('jenkins/<int:pk>/edit/', views.configuration, {'kind':'jenkins'}, name='jenkins_edit'), path('jenkins/<int:pk>/validate/', views.validate_connection, {'kind':'jenkins'}, name='jenkins_validate'),
 path('github/', views.github_list, name='github_list'), path('github/new/', views.configuration, {'kind':'github'}, name='github_new'), path('github/<int:pk>/edit/', views.configuration, {'kind':'github'}, name='github_edit'), path('github/<int:pk>/validate/', views.validate_connection, {'kind':'github'}, name='github_validate'),
 path('mappings/', views.mapping_list, name='mapping_list'), path('mappings/new/', views.configuration, {'kind':'mapping'}, name='mapping_new'), path('mappings/<int:pk>/edit/', views.configuration, {'kind':'mapping'}, name='mapping_edit'), path('mappings/<int:pk>/sync/', views.synchronize, name='mapping_sync'),
 path('reports/', views.reports, name='reports'), path('settings/', views.settings_view, name='settings'), path('settings/users/', views.create_managed_user, name='create_managed_user'), path('settings/display-preferences/', views.update_display_preferences, name='display_preferences'), path('settings/backup/', views.database_backup, name='database_backup'), path('settings/restore/', views.database_restore, name='database_restore'),
]
