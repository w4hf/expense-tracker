from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Dashboard View
    path('', views.dashboard_view, name='dashboard'),

    # Transaction Views
    path('transactions/', views.transaction_list_view, name='transaction_list'),
    path('transactions/add/', views.transaction_create_view, name='transaction_add'),
    path('transactions/<int:pk>/edit/', views.transaction_update_view, name='transaction_edit'),
    path('transactions/<int:pk>/toggle-zakatable/', views.toggle_zakatable_view, name='transaction_toggle_zakatable'),
    path('transactions/delete-selected/', views.transaction_delete_selected_view, name='transaction_delete_selected'),

    # CSV Import Views
    path('transactions/import/', views.import_csv_step1_view, name='import_csv_step1'),
    path('transactions/import/step2/', views.import_csv_step2_mapping_view, name='import_csv_step2_mapping'),
    path('transactions/import/step3/', views.import_csv_step3_preview_view, name='import_csv_step3_preview'),
    path('transactions/import/process/', views.process_csv_import_view, name='process_csv_import'),

    # Account Management Views
    path('accounts/', views.account_list_view, name='account_list'),
    path('accounts/new/', views.account_create_view, name='account_create'),
    path('accounts/<int:pk>/edit/', views.account_update_view, name='account_edit'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),

    # Category Management Views
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/new/', views.category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update_view, name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Loan Views
    path('loans/', views.LoanListView.as_view(), name='loan_list'),
    path('loans/new/', views.LoanCreateView.as_view(), name='loan_create'),
    path('loans/<int:pk>/', views.LoanDetailView.as_view(), name='loan_detail'),
    path('loans/<int:pk>/edit/', views.LoanUpdateView.as_view(), name='loan_edit'),
    path('loans/<int:pk>/delete/', views.LoanDeleteView.as_view(), name='loan_delete'),
    path('loans/operations/<int:pk>/edit/', views.LoanOperationUpdateView.as_view(), name='loan_operation_edit'),
    path('loans/operations/<int:pk>/delete/', views.LoanOperationDeleteView.as_view(), name='loan_operation_delete'),
]