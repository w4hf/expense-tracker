# tracker/models.py
from django.db import models
from django.conf import settings 
from django.utils import timezone
from django.urls import reverse # For get_absolute_url
from decimal import Decimal # <--- IMPORT DECIMAL HERE
from hijri_converter import convert

# Model for Bank Accounts or financial sources
class Account(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Name of the account (e.g., Boursorama, Revolut, Cash)")
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True) 

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

# Model for Categories of transactions
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Category name (e.g., Groceries, Salary, Utilities)")
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True) 

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

# Model for individual Transactions
class Transaction(models.Model):
    date = models.DateField(default=timezone.now, help_text="Date of the transaction (YYYY-MM-DD)")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transactions", help_text="Account for this transaction")
    title = models.CharField(max_length=200, help_text="Short title or payee for the transaction")
    description = models.TextField(blank=True, null=True, help_text="Optional longer description")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount of the transaction. Positive for income, negative for expenses.")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions", help_text="Category of the transaction")
    balance_after_transaction = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Account balance after this transaction (from CSV)")
    is_zakatable = models.BooleanField(default=False, help_text="Check if this transaction amount is subject to Zakat calculation")
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} - {self.title} - {self.amount}"

    class Meta:
        ordering = ['-date', '-created_at'] 

# Model for Loan Tables (groups of loan operations)
class Loan(models.Model):
    title = models.CharField(max_length=150, help_text="User-defined title for this loan tracker (e.g., 'Loan to John Doe', 'Car Loan Repayments')")
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def total_amount(self):
        # Sums amounts: positive for 'Receive', negative for 'Send'
        total = Decimal('0.00') # Initialize as Decimal
        for op in self.operations.all(): # Ensure operations is the related_name
            if op.operation_type == LoanOperation.RECEIVE:
                total += op.amount
            elif op.operation_type == LoanOperation.SEND:
                total -= op.amount 
        return total

    def get_absolute_url(self):
        return reverse('tracker:loan_detail', kwargs={'pk': self.pk})

    class Meta:
        ordering = ['-created_at']


class ZakatYear(models.Model):
    hijri_year = models.PositiveIntegerField(unique=True, default=1446, help_text="The Hijri year for Zakat calculation (e.g., 1446)")
    nisab_amount = models.DecimalField(max_digits=10, decimal_places=2, default=5900.00, help_text="The Nisab amount for this year in your currency (e.g., 5000.00)")
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) # Add for multi-user apps

    def __str__(self):
        return f"Zakat for year {self.hijri_year}H"

    def get_absolute_url(self):
        return reverse('tracker:zakat_detail', kwargs={'pk': self.pk})

    def get_gregorian_range(self):
        """
        Calculates the start and end Gregorian dates for the Hijri year.
        """
        try:
            start_date = convert.Hijri(self.hijri_year, 1, 1).to_gregorian()
            # To get the end date, we find the start of the next year and subtract one day
            next_year_start_date = convert.Hijri(self.hijri_year + 1, 1, 1).to_gregorian()
            end_date = next_year_start_date - timezone.timedelta(days=1)
            return start_date, end_date
        except Exception:
            # Handle potential conversion errors for very old or future years if the library has limits
            return None, None
    
    class Meta:
        ordering = ['-hijri_year']

# Model for individual Loan Operations within a Loan table
class LoanOperation(models.Model):
    SEND = 'Send'
    RECEIVE = 'Receive'
    OPERATION_CHOICES = [
        (SEND, 'Send Money'),
        (RECEIVE, 'Receive Money'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="operations", help_text="The loan group this operation belongs to")
    date = models.DateField(default=timezone.now, help_text="Date of the loan operation (YYYY-MM-DD)")
    operation_type = models.CharField(max_length=10, choices=OPERATION_CHOICES, help_text="Type of operation: Send or Receive")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount of money involved in this operation (always positive)")
    description = models.CharField(max_length=200, blank=True, null=True, help_text="Optional short description for the operation")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.loan.title} - {self.operation_type} - {self.amount} on {self.date}"

    class Meta:
        ordering = ['date', 'created_at']
