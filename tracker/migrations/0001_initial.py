# Generated by Django 4.2.21 on 2025-05-11 16:20

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the account (e.g., Boursorama, Revolut, Cash)', max_length=100, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Category name (e.g., Groceries, Salary, Utilities)', max_length=100, unique=True)),
            ],
            options={
                'verbose_name_plural': 'Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text="User-defined title for this loan tracker (e.g., 'Loan to John Doe', 'Car Loan Repayments')", max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now, help_text='Date of the transaction (YYYY-MM-DD)')),
                ('title', models.CharField(help_text='Short title or payee for the transaction', max_length=200)),
                ('description', models.TextField(blank=True, help_text='Optional longer description', null=True)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Amount of the transaction. Positive for income, negative for expenses.', max_digits=10)),
                ('balance_after_transaction', models.DecimalField(blank=True, decimal_places=2, help_text='Account balance after this transaction (from CSV)', max_digits=10, null=True)),
                ('is_zakatable', models.BooleanField(default=False, help_text='Check if this transaction amount is subject to Zakat calculation')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(help_text='Account for this transaction', on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='tracker.account')),
                ('category', models.ForeignKey(blank=True, help_text='Category of the transaction', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='tracker.category')),
            ],
            options={
                'ordering': ['-date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LoanOperation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now, help_text='Date of the loan operation (YYYY-MM-DD)')),
                ('operation_type', models.CharField(choices=[('Send', 'Send Money'), ('Receive', 'Receive Money')], help_text='Type of operation: Send or Receive', max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Amount of money involved in this operation (always positive)', max_digits=10)),
                ('description', models.CharField(blank=True, help_text='Optional short description for the operation', max_length=200, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('loan', models.ForeignKey(help_text='The loan group this operation belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='operations', to='tracker.loan')),
            ],
            options={
                'ordering': ['date', 'created_at'],
            },
        ),
    ]
