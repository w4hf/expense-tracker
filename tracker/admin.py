from django.contrib import admin
from .models import Account, Category, Transaction, Loan, LoanOperation

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'account', 'title', 'amount', 'category', 'balance_after_transaction', 'is_zakatable')
    list_filter = ('date', 'account', 'category', 'is_zakatable')
    search_fields = ('title', 'description', 'category__name', 'account__name')
    list_editable = ('is_zakatable',) # Allows editing zakatable directly in the list view
    date_hierarchy = 'date'
    fieldsets = (
        (None, {
            'fields': ('date', 'account', 'title', 'description', 'amount', 'category')
        }),
        ('Import Details & Zakat', {
            'fields': ('balance_after_transaction', 'is_zakatable'),
            'classes': ('collapse',), # Collapsible section
        }),
    )

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'total_amount')
    search_fields = ('title',)

@admin.register(LoanOperation)
class LoanOperationAdmin(admin.ModelAdmin):
    list_display = ('loan', 'date', 'operation_type', 'amount', 'description')
    list_filter = ('loan', 'date', 'operation_type')
    search_fields = ('loan__title', 'description')