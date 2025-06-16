# tracker/views.py

import pandas as pd # Keep if used elsewhere, not strictly needed for this change
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin 
from django.contrib.auth.decorators import login_required 
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, TemplateView, DetailView, DeleteView
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.http import require_POST, require_http_methods
import os
import uuid
from decimal import Decimal, InvalidOperation 
from django.db.models import Sum, ProtectedError, Q, OuterRef, Subquery, F, Max
from django.utils import timezone
import json 
from datetime import datetime, timedelta # Ensure datetime is imported
from django.db.models import Sum, ProtectedError, Q # <--- IMPORT Q HERE

from .models import Transaction, Account, Category, Loan, LoanOperation
from .forms import ( # Assuming these are still relevant for other views in the file
    TransactionForm, AccountForm, CategoryForm, 
    CSVImportStep1Form, CSVImportHeaderMappingForm,
    LoanForm, LoanOperationForm
)

# Helper function (no changes)
def clean_decimal(value_str, decimal_separator='.'):
    if not isinstance(value_str, str): value_str = str(value_str)
    value_str = value_str.replace(' ', '') 
    if decimal_separator == ',': value_str = value_str.replace('.', '').replace(',', '.') 
    else: value_str = value_str.replace(',', '')
    try: return Decimal(value_str.strip())
    except InvalidOperation: return None

# --- Dashboard View ---
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tracker/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # --- Date Range Handling for Account Balance Evolution ---
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        default_end_date = timezone.now().date()
        default_start_date = default_end_date - timedelta(days=89) 

        start_date = default_start_date
        end_date = default_end_date
        
        valid_range = True
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.warning(request, "Invalid date format for balance evolution. Showing default date range.")
            valid_range = False 
            start_date = default_start_date 
            end_date = default_end_date

        if valid_range and start_date > end_date:
            messages.warning(request, "Start date cannot be after end date for balance evolution. Showing default date range.")
            start_date = default_start_date 
            end_date = default_end_date
            
        context['request_start_date'] = start_date.isoformat()
        context['request_end_date'] = end_date.isoformat()

        # Expenses by Category Chart - No date range applied here for simplicity
        expenses_by_category = Transaction.objects.filter(amount__lt=0)\
            .values('category__name')\
            .annotate(total_expenses=Sum('amount'))\
            .order_by('category__name')
        category_labels = [item['category__name'] if item['category__name'] else "Uncategorized" for item in expenses_by_category]
        category_data = [float(item['total_expenses'] * -1) if item['total_expenses'] else 0.0 for item in expenses_by_category]
        context['expenses_by_category_labels'] = json.dumps(category_labels)
        context['expenses_by_category_data'] = json.dumps(category_data)

        # Account Balance Evolution (Line Chart) - Apply date range
        individual_account_datasets_data = [] # To store data for individual accounts temporarily
        accounts = Account.objects.all()

        # Determine the overall date range for the x-axis
        all_dates_in_window = []
        if start_date and end_date and start_date <= end_date:
            num_days = (end_date - start_date).days + 1
            all_dates_in_window = sorted(list(set(
                [start_date + timedelta(days=i) for i in range(num_days)]
            )))
        
        # Prepare datasets for individual accounts
        for account in accounts:
            # Get transactions within the selected date range for this account
            acc_transactions_in_range = Transaction.objects.filter(
                account=account, 
                date__gte=start_date, 
                date__lte=end_date,   
                balance_after_transaction__isnull=False
            ).order_by('date', 'created_at').values('date', 'balance_after_transaction')

            daily_last_balance_for_account = {
                t['date']: float(t['balance_after_transaction']) 
                for t in acc_transactions_in_range if t['balance_after_transaction'] is not None
            }
            
            last_known_balance_val = None
            last_transaction_before_window = Transaction.objects.filter(
                account=account, 
                date__lt=start_date, 
                balance_after_transaction__isnull=False
            ).order_by('-date', '-created_at').first()

            if last_transaction_before_window and last_transaction_before_window.balance_after_transaction is not None: 
                last_known_balance_val = float(last_transaction_before_window.balance_after_transaction)
            
            current_balance_points = {}
            # Use the common all_dates_in_window for iteration
            for date_point in all_dates_in_window:
                if date_point in daily_last_balance_for_account:
                    last_known_balance_val = daily_last_balance_for_account[date_point]
                
                if last_known_balance_val is not None: 
                    current_balance_points[date_point.strftime('%Y-%m-%d')] = last_known_balance_val
            
            if current_balance_points: 
                 individual_account_datasets_data.append({
                    'label': account.name, 
                    'data': current_balance_points, # This map contains date_str: balance_float
                    'fill': False, 
                    'tension': 0.1
                })
        
        # Calculate "Total All Accounts" dataset
        total_balance_data_points = {}
        if all_dates_in_window:
            for date_obj in all_dates_in_window:
                date_str = date_obj.strftime('%Y-%m-%d')
                sum_for_date = 0.0
                # Check each individual account's data for this date
                for acc_dataset_data in individual_account_datasets_data:
                    sum_for_date += acc_dataset_data['data'].get(date_str, 0.0) # Assume 0 if no data for that account on that day
                total_balance_data_points[date_str] = sum_for_date
        
        final_chart_datasets = list(individual_account_datasets_data) # Start with individual accounts

        if total_balance_data_points:
            final_chart_datasets.append({
                'label': 'Total All Accounts',
                'data': total_balance_data_points,
                'fill': False,
                'borderColor': '#800080', # Purple for distinction
                'backgroundColor': '#800080', # For point fill on hover
                'tension': 0.1,
                'borderWidth': 3, # Make it a bit thicker
                'pointRadius': 1, # Small points
                'pointHoverRadius': 7,
                'order': -1 # Attempt to draw it on top or first in legend
            })
            
        context['balance_evolution_datasets'] = json.dumps(final_chart_datasets)
        
        # --- Current Balances for each Account ---
        account_current_balances = []
        for account_obj in Account.objects.all().order_by('name'):
            latest_transaction = Transaction.objects.filter(
                account=account_obj,
                balance_after_transaction__isnull=False
            ).order_by('-date', '-created_at').first() 
            
            current_balance = latest_transaction.balance_after_transaction if latest_transaction else Decimal('0.00')
            account_current_balances.append({
                'name': account_obj.name,
                'balance': current_balance,
                'last_updated_date': latest_transaction.date if latest_transaction else None
            })
        context['account_current_balances'] = account_current_balances

        # Summary Stats - No date range applied here
        total_income = Transaction.objects.filter(amount__gt=0).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        total_expenses = Transaction.objects.filter(amount__lt=0).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        context['total_income'] = total_income
        context['total_expenses'] = total_expenses 
        context['net_savings'] = total_income + total_expenses
        
        context['recent_transactions'] = Transaction.objects.select_related('account', 'category').all().order_by('-date', '-created_at')[:5]
        return context

dashboard_view = DashboardView.as_view()

# --- Transaction Views ---
class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'tracker/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 25 
    
    def get_queryset(self): 
        queryset = super().get_queryset().select_related('account', 'category').order_by('-date', '-created_at')
        
        # Get filter parameters from request
        account_id = self.request.GET.get('account')
        category_id = self.request.GET.get('category')
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        search_query = self.request.GET.get('search_query')

        if account_id:
            queryset = queryset.filter(account_id=account_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass # Or add a message for invalid date format
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_date)
            except ValueError:
                pass # Or add a message

        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_accounts'] = Account.objects.all().order_by('name')
        context['all_categories'] = Category.objects.all().order_by('name')
        # Pass current filter values back to template for pre-filling form
        # request.GET is already available in template, but being explicit can be clearer for complex cases
        # context['current_filters'] = self.request.GET 
        return context

transaction_list_view = TransactionListView.as_view()

class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction; form_class = TransactionForm; template_name = 'tracker/transaction_form.html'; success_url = reverse_lazy('tracker:transaction_list')
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context['form_title'] = "Add New Transaction"; return context
    def form_valid(self, form): messages.success(self.request, "Transaction added successfully."); return super().form_valid(form)
transaction_create_view = TransactionCreateView.as_view()

class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction; form_class = TransactionForm; template_name = 'tracker/transaction_form.html'; success_url = reverse_lazy('tracker:transaction_list')
    def get_context_data(self, **kwargs): context = super().get_context_data(**kwargs); context['form_title'] = f"Edit Transaction"; context['form_subtitle'] = f"ID: {self.object.pk} | Date: {self.object.date.strftime('%Y-%m-%d')}"; return context
    def form_valid(self, form): messages.success(self.request, "Transaction updated successfully."); return super().form_valid(form)
transaction_update_view = TransactionUpdateView.as_view()

@login_required
@require_POST 
def transaction_delete_selected_view(request):
    transaction_ids = request.POST.getlist('transaction_ids')
    if not transaction_ids: messages.warning(request, "No transactions selected for deletion."); return redirect('tracker:transaction_list')
    try: transactions_to_delete = Transaction.objects.filter(pk__in=transaction_ids); count = transactions_to_delete.count(); transactions_to_delete.delete(); messages.success(request, f"Successfully deleted {count} transaction(s).")
    except Exception as e: messages.error(request, f"Error deleting transactions: {e}")
    return redirect('tracker:transaction_list')

@login_required
@require_POST
def toggle_zakatable_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    transaction.is_zakatable = not transaction.is_zakatable
    transaction.save(update_fields=['is_zakatable'])
    return JsonResponse({'status': 'success', 'is_zakatable': transaction.is_zakatable})

# --- Account Views ---
class AccountListView(LoginRequiredMixin, ListView): # New View
    model = Account
    template_name = 'tracker/account_list.html'
    context_object_name = 'accounts'
    paginate_by = 15

    def get_queryset(self):
        return Account.objects.all().order_by('name') # Or any other preferred ordering

account_list_view = AccountListView.as_view()

class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'tracker/account_form.html' # Reusing the form
    success_url = reverse_lazy('tracker:account_list') # Redirect to the list view

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Add New Account"
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Account '{form.instance.name}' created successfully.")
        return super().form_valid(form)
account_create_view = AccountCreateView.as_view()

class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'tracker/account_form.html' # Reusing the form
    success_url = reverse_lazy('tracker:account_list') # Redirect to the list view

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Edit Account: {self.object.name}"
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Account '{form.instance.name}' updated successfully.")
        return super().form_valid(form)
account_update_view = AccountUpdateView.as_view()

class AccountDeleteView(LoginRequiredMixin, DeleteView): # New View
    model = Account
    template_name = 'tracker/account_confirm_delete.html' # New template for confirmation
    success_url = reverse_lazy('tracker:account_list')
    context_object_name = 'account' # For the template

    def post(self, request, *args, **kwargs):
        try:
            account_name = self.get_object().name
            response = super().post(request, *args, **kwargs)
            messages.success(request, f"Account '{account_name}' deleted successfully.")
            return response
        except ProtectedError:
            messages.error(request, f"Cannot delete account '{self.get_object().name}' because it has associated transactions. Please reassign or delete those transactions first.")
            return redirect('tracker:account_list')
        except Exception as e:
            messages.error(request, f"An error occurred while trying to delete the account: {e}")
            return redirect('tracker:account_list')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_message'] = f"Are you sure you want to delete the account '{self.object.name}'?"
        # Check if account has transactions
        if Transaction.objects.filter(account=self.object).exists():
            context['has_transactions'] = True
            context['delete_message'] += " This account has associated transactions. Deleting it might cause issues or is disallowed if transactions are protected."
        else:
            context['has_transactions'] = False
        context['cancel_url'] = reverse_lazy('tracker:account_list')
        return context

# --- Category Views ---
class CategoryListView(LoginRequiredMixin, ListView): 
    model = Category
    template_name = 'tracker/category_list.html'
    context_object_name = 'categories'
    paginate_by = 15

    def get_queryset(self):
        return Category.objects.all().order_by('name')

category_list_view = CategoryListView.as_view()

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'tracker/category_form.html' 
    success_url = reverse_lazy('tracker:category_list') 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Add New Category"
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' created successfully.")
        return super().form_valid(form)
category_create_view = CategoryCreateView.as_view()

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'tracker/category_form.html' 
    success_url = reverse_lazy('tracker:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Edit Category: {self.object.name}"
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' updated successfully.")
        return super().form_valid(form)
category_update_view = CategoryUpdateView.as_view()

class CategoryDeleteView(LoginRequiredMixin, DeleteView): 
    model = Category
    template_name = 'tracker/category_confirm_delete.html' 
    success_url = reverse_lazy('tracker:category_list')
    context_object_name = 'category' 

    def post(self, request, *args, **kwargs):
        try:
            category_name = self.get_object().name
            response = super().post(request, *args, **kwargs)
            messages.success(request, f"Category '{category_name}' deleted successfully.")
            return response
        except ProtectedError: 
            messages.error(request, f"Cannot delete category '{self.get_object().name}' because it has associated transactions. Please reassign or delete those transactions first.")
            return redirect('tracker:category_list')
        except Exception as e: 
            messages.error(request, f"An error occurred while trying to delete the category: {e}")
            return redirect('tracker:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_message'] = f"Are you sure you want to delete the category '{self.object.name}'?"
        if Transaction.objects.filter(category=self.object).exists():
            context['has_transactions'] = True 
            context['delete_message'] += " This category is currently assigned to some transactions. If you delete it, those transactions will become uncategorized."
        else:
            context['has_transactions'] = False
        context['cancel_url'] = reverse_lazy('tracker:category_list')
        return context

# CSV Import Views (no changes for this request)
@login_required
def import_csv_step1_view(request):
    if request.method == 'POST':
        form = CSVImportStep1Form(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            temp_csv_dir = os.path.join(settings.MEDIA_ROOT, 'temp_csv')
            os.makedirs(temp_csv_dir, exist_ok=True)
            fs = FileSystemStorage(location=temp_csv_dir)
            ext = os.path.splitext(csv_file.name)[1].lower()
            if ext != '.csv':
                messages.error(request, "Invalid file type. Please upload a .csv file.")
                return render(request, 'tracker/import_csv_step1.html', {'form': form})
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            filename = fs.save(unique_filename, csv_file)
            uploaded_file_path = fs.path(filename)
            request.session['csv_import_file_path'] = uploaded_file_path
            request.session['csv_amount_decimal_separator'] = form.cleaned_data['amount_decimal_separator']
            request.session['csv_balance_decimal_separator'] = form.cleaned_data.get('balance_decimal_separator') or form.cleaned_data['amount_decimal_separator']
            request.session['csv_date_format'] = form.cleaned_data['date_format']
            messages.info(request, f"File '{csv_file.name}' uploaded. Please map columns.")
            return redirect('tracker:import_csv_step2_mapping')
    else:
        form = CSVImportStep1Form()
    return render(request, 'tracker/import_csv_step1.html', {'form': form})

@login_required
def import_csv_step2_mapping_view(request):
    uploaded_file_path = request.session.get('csv_import_file_path')
    if not uploaded_file_path or not os.path.exists(uploaded_file_path):
        messages.error(request, "No CSV file found or session expired. Please upload again.")
        return redirect('tracker:import_csv_step1')
    try:
        df_sample = pd.read_csv(uploaded_file_path, nrows=5, sep=None, engine='python', skipinitialspace=True, dtype=str)
        csv_headers = df_sample.columns.tolist()
        sample_rows = df_sample.head(3).to_dict(orient='records')
    except Exception as e:
        messages.error(request, f"Error reading CSV headers: {e}. Ensure it's a valid CSV.")
        if os.path.exists(uploaded_file_path): os.remove(uploaded_file_path)
        request.session.pop('csv_import_file_path', None)
        return redirect('tracker:import_csv_step1')
    if request.method == 'POST':
        form = CSVImportHeaderMappingForm(csv_headers, request.POST)
        if form.is_valid():
            request.session['csv_header_mapping'] = form.cleaned_data
            messages.info(request, "Header mapping saved. Please review and confirm import.")
            return redirect('tracker:import_csv_step3_preview')
    else:
        form = CSVImportHeaderMappingForm(csv_headers)
    return render(request, 'tracker/import_csv_step2_mapping.html', {'form': form, 'csv_headers': csv_headers, 'sample_rows': sample_rows, 'filename': os.path.basename(uploaded_file_path)})

@login_required
def import_csv_step3_preview_view(request):
    uploaded_file_path = request.session.get('csv_import_file_path')
    header_mapping = request.session.get('csv_header_mapping')
    amount_decimal_separator = request.session.get('csv_amount_decimal_separator', '.')
    balance_decimal_separator = request.session.get('csv_balance_decimal_separator') or amount_decimal_separator
    date_format = request.session.get('csv_date_format', '%Y-%m-%d')
    if not all([uploaded_file_path, header_mapping]):
        messages.error(request, "Import session data missing. Please start over.")
        return redirect('tracker:import_csv_step1')
    if not os.path.exists(uploaded_file_path):
        messages.error(request, "Uploaded CSV file not found. Please upload again.")
        request.session.pop('csv_import_file_path', None)
        return redirect('tracker:import_csv_step1')
    preview_data, errors, parsed_rows_for_session = [], [], []
    MAX_PREVIEW_ROWS = 20
    try:
        df = pd.read_csv(uploaded_file_path, sep=None, engine='python', skipinitialspace=True, dtype=str)
        model_to_csv_header = {k: header_mapping.get(v) for k, v in {'date': 'date_column', 'account_name': 'account_column', 'title': 'title_column', 'description': 'description_column', 'amount': 'amount_column', 'category_name': 'category_column', 'balance': 'balance_column'}.items()}
        for index, row_series in df.iterrows():
            row = row_series.to_dict() 
            parsed_row, row_errors, display_row = {}, [], {}
            date_str = str(row.get(model_to_csv_header['date'], '')).strip()
            if date_str:
                try: parsed_date = pd.to_datetime(date_str, format=date_format).strftime('%Y-%m-%d'); parsed_row['date'] = parsed_date; display_row['date'] = parsed_date
                except ValueError: row_errors.append(f"R{index+2}: Invalid date '{date_str}'. Expected '{date_format}'."); display_row['date'] = date_str 
            else: row_errors.append(f"R{index+2}: Date missing."); display_row['date'] = "Missing"
            amount_str_raw = row.get(model_to_csv_header['amount'], ''); amount_str = str(amount_str_raw if amount_str_raw is not None else '').strip()
            if amount_str:
                cleaned_amount_decimal = clean_decimal(amount_str, amount_decimal_separator)
                if cleaned_amount_decimal is not None: parsed_row['amount'] = str(cleaned_amount_decimal); display_row['amount'] = cleaned_amount_decimal 
                else: row_errors.append(f"R{index+2}: Invalid amount '{amount_str}'."); display_row['amount'] = amount_str 
            else: row_errors.append(f"R{index+2}: Amount missing."); display_row['amount'] = "Missing"
            balance_csv_header = model_to_csv_header.get('balance'); display_row['balance_after_transaction'] = None; parsed_row['balance_after_transaction'] = None 
            if balance_csv_header and row.get(balance_csv_header) is not None:
                balance_str_raw = row.get(balance_csv_header, ''); balance_str = str(balance_str_raw if balance_str_raw is not None else '').strip()
                if balance_str:
                    cleaned_balance_decimal = clean_decimal(balance_str, balance_decimal_separator)
                    if cleaned_balance_decimal is not None: parsed_row['balance_after_transaction'] = str(cleaned_balance_decimal); display_row['balance_after_transaction'] = cleaned_balance_decimal 
                    else: row_errors.append(f"R{index+2}: Invalid balance '{balance_str}'."); display_row['balance_after_transaction'] = balance_str 
            title_val = str(row.get(model_to_csv_header['title'], '')).strip(); parsed_row['title'] = title_val; display_row['title'] = title_val
            if not title_val: row_errors.append(f"R{index+2}: Title missing.")
            description_csv_header = model_to_csv_header.get('description'); desc_val = str(row.get(description_csv_header, '')).strip() if description_csv_header else ""; parsed_row['description'] = desc_val; display_row['description'] = desc_val
            acc_name_val = str(row.get(model_to_csv_header['account_name'], '')).strip(); parsed_row['account_name'] = acc_name_val; display_row['account_name'] = acc_name_val
            if not acc_name_val: row_errors.append(f"R{index+2}: Account name missing.")
            cat_name_val = str(row.get(model_to_csv_header['category_name'], '')).strip(); parsed_row['category_name'] = cat_name_val; display_row['category_name'] = cat_name_val
            if not cat_name_val: row_errors.append(f"R{index+2}: Category name missing.")
            if row_errors: errors.extend(row_errors)
            if index < MAX_PREVIEW_ROWS: preview_data.append({**display_row, 'original_row_index': index + 2, 'has_errors': bool(row_errors)})
            if not row_errors: parsed_rows_for_session.append(parsed_row) 
        request.session['parsed_csv_data_for_import'] = parsed_rows_for_session
        if errors and not request.POST: messages.warning(request, "Review issues. Error-free rows will import.")
        elif not parsed_rows_for_session and not errors: messages.warning(request, "No data parsed or all rows had errors. Check file/mapping."); 
        if not df.empty and not preview_data and not errors and not parsed_rows_for_session : return redirect('tracker:import_csv_step2_mapping')
    except Exception as e:
        messages.error(request, f"Error processing CSV for preview: {e}")
        if uploaded_file_path and os.path.exists(uploaded_file_path): os.remove(uploaded_file_path)
        for key in ['csv_import_file_path', 'csv_header_mapping', 'csv_amount_decimal_separator', 'csv_balance_decimal_separator', 'csv_date_format', 'parsed_csv_data_for_import']: request.session.pop(key, None)
        return redirect('tracker:import_csv_step1')
    return render(request, 'tracker/import_csv_step3_preview.html', {'preview_data': preview_data, 'total_parsed_rows': len(parsed_rows_for_session), 'total_csv_rows': len(df) if 'df' in locals() else 0, 'errors': errors[:10], 'has_more_errors': len(errors) > 10, 'filename': os.path.basename(uploaded_file_path)})

@login_required
def process_csv_import_view(request):
    if request.method != 'POST': return HttpResponseBadRequest("POST request required.")
    parsed_data_from_session = request.session.get('parsed_csv_data_for_import')
    uploaded_file_path = request.session.get('csv_import_file_path')
    if not parsed_data_from_session: messages.error(request, "No data to import or session expired."); return redirect('tracker:import_csv_step1')
    imported_count, skipped_count = 0, 0; created_accounts, created_categories = set(), set()
    for row_data_str in parsed_data_from_session:
        try:
            amount_decimal = Decimal(row_data_str['amount']); balance_decimal = Decimal(row_data_str['balance_after_transaction']) if row_data_str.get('balance_after_transaction') else None
            account, acc_created = Account.objects.get_or_create(name__iexact=row_data_str['account_name'], defaults={'name': row_data_str['account_name']}); 
            if acc_created: created_accounts.add(account.name)
            category, cat_created = Category.objects.get_or_create(name__iexact=row_data_str['category_name'], defaults={'name': row_data_str['category_name']}); 
            if cat_created: created_categories.add(category.name)
            Transaction.objects.create(date=row_data_str['date'], account=account, title=row_data_str['title'], description=row_data_str.get('description', ''), amount=amount_decimal, category=category, balance_after_transaction=balance_decimal, is_zakatable=False )
            imported_count += 1
        except Exception as e: print(f"Error importing row {row_data_str}: {e}"); skipped_count += 1
    if uploaded_file_path and os.path.exists(uploaded_file_path):
        try: os.remove(uploaded_file_path)
        except OSError as e: print(f"Error deleting temp file {uploaded_file_path}: {e}")
    for key in ['csv_import_file_path', 'csv_header_mapping', 'csv_amount_decimal_separator', 'csv_balance_decimal_separator', 'csv_date_format', 'parsed_csv_data_for_import']: request.session.pop(key, None)
    messages.success(request, f"Successfully imported {imported_count} transactions.")
    if skipped_count > 0: messages.warning(request, f"Skipped {skipped_count} transactions due to errors during final import.")
    if created_accounts: messages.info(request, f"New accounts created: {', '.join(created_accounts)}.")
    if created_categories: messages.info(request, f"New categories created: {', '.join(created_categories)}.")
    return redirect('tracker:transaction_list')

# --- Loan Views ---
class LoanListView(LoginRequiredMixin, ListView):
    model = Loan
    template_name = 'tracker/loan_list.html'
    context_object_name = 'loans'
    paginate_by = 10
    def get_queryset(self):
        return Loan.objects.all().order_by('-created_at')

class LoanDetailView(LoginRequiredMixin, DetailView):
    model = Loan
    template_name = 'tracker/loan_detail.html'
    context_object_name = 'loan'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan = self.get_object()
        context['operations'] = loan.operations.all().order_by('-date', '-created_at')
        context['operation_form'] = LoanOperationForm(initial={'loan': loan})
        context['total_amount'] = loan.total_amount
        return context
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = LoanOperationForm(request.POST)
        if form.is_valid():
            operation = form.save(commit=False)
            operation.loan = self.object
            operation.save()
            messages.success(request, f"Operation '{operation.get_operation_type_display()} - {operation.amount}€' added to '{self.object.title}'.")
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            context = self.get_context_data()
            context['operation_form'] = form
            messages.error(request, "Error adding operation. Please check the form.")
            return self.render_to_response(context)

class LoanCreateView(LoginRequiredMixin, CreateView):
    model = Loan
    form_class = LoanForm
    template_name = 'tracker/loan_form.html'
    def get_success_url(self):
        messages.success(self.request, f"Loan tracker '{self.object.title}' created successfully.")
        return reverse('tracker:loan_detail', kwargs={'pk': self.object.pk})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Create New Loan Tracker"
        return context

class LoanUpdateView(LoginRequiredMixin, UpdateView):
    model = Loan
    form_class = LoanForm
    template_name = 'tracker/loan_form.html'
    def get_success_url(self):
        messages.success(self.request, f"Loan tracker '{self.object.title}' updated successfully.")
        return reverse('tracker:loan_detail', kwargs={'pk': self.object.pk})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Edit Loan Tracker: {self.object.title}"
        return context

class LoanDeleteView(LoginRequiredMixin, DeleteView):
    model = Loan
    template_name = 'tracker/loan_confirm_delete.html'
    success_url = reverse_lazy('tracker:loan_list')
    context_object_name = 'object'
    def post(self, request, *args, **kwargs):
        loan_title = self.get_object().title
        response = super().post(request, *args, **kwargs)
        messages.success(request, f"Loan tracker '{loan_title}' and all its operations deleted successfully.")
        return response
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_message'] = f"Are you sure you want to delete the loan tracker '{self.object.title}'? This will also delete all associated operations."
        context['cancel_url'] = self.object.get_absolute_url() if hasattr(self.object, 'get_absolute_url') else reverse_lazy('tracker:loan_list')
        return context

class LoanOperationUpdateView(LoginRequiredMixin, UpdateView):
    model = LoanOperation
    form_class = LoanOperationForm
    template_name = 'tracker/loan_operation_form.html'
    def get_success_url(self):
        messages.success(self.request, "Loan operation updated successfully.")
        return reverse('tracker:loan_detail', kwargs={'pk': self.object.loan.pk})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Edit Operation for '{self.object.loan.title}'"
        return context

class LoanOperationDeleteView(LoginRequiredMixin, DeleteView):
    model = LoanOperation
    template_name = 'tracker/loan_confirm_delete.html'
    context_object_name = 'object'
    def get_success_url(self):
        loan_pk = self.object.loan.pk
        messages.success(self.request, "Loan operation deleted successfully.")
        return reverse('tracker:loan_detail', kwargs={'pk': loan_pk})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_message'] = f"Are you sure you want to delete this operation ({self.object.get_operation_type_display()} of {self.object.amount}€ on {self.object.date}) for loan '{self.object.loan.title}'?"
        context['cancel_url'] = reverse('tracker:loan_detail', kwargs={'pk': self.object.loan.pk})
        return context
