
from django import forms
from .models import Account, Transaction, Loan, LoanOperation, Category
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


# Common Tailwind CSS classes for form inputs
common_input_classes = 'mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'
common_checkbox_classes = 'h-5 w-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
common_button_classes = 'px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 border border-transparent rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out'
common_cancel_button_classes = 'px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out'


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': common_input_classes, 'placeholder': 'e.g., Boursorama Pro'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': common_input_classes, 'placeholder': 'e.g., Groceries'}),
        }

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'account', 'title', 'description', 'amount', 'category', 'balance_after_transaction', 'is_zakatable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': common_input_classes}),
            'account': forms.Select(attrs={'class': common_input_classes}),
            'title': forms.TextInput(attrs={'class': common_input_classes}),
            'description': forms.Textarea(attrs={'class': common_input_classes, 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': common_input_classes, 'step': '0.01'}),
            'category': forms.Select(attrs={'class': common_input_classes}),
            'balance_after_transaction': forms.NumberInput(attrs={'class': common_input_classes, 'step': '0.01', 'placeholder': 'Optional'}),
            'is_zakatable': forms.CheckboxInput(attrs={'class': common_checkbox_classes}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = Account.objects.all()
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].required = False
        self.fields['balance_after_transaction'].required = False


class CSVImportStep1Form(forms.Form):
    csv_file = forms.FileField(
        label="Upload CSV File", 
        help_text="Select the CSV file to import transactions from.", 
        widget=forms.ClearableFileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer', 'accept': '.csv'})
    )
    amount_decimal_separator = forms.ChoiceField(
        choices=[('.', 'Dot (.) for decimals'), (',', 'Comma (,) for decimals')],
        label="Decimal Separator in Amount Column",
        widget=forms.RadioSelect(attrs={'class': 'form-radio h-4 w-4 text-indigo-600 border-gray-300 focus:ring-indigo-500'}),
        initial='.'
    )
    balance_decimal_separator = forms.ChoiceField(
        choices=[('.', 'Dot (.) for decimals'), (',', 'Comma (,) for decimals')],
        label="Decimal Separator in Balance Column (if applicable)",
        widget=forms.RadioSelect(attrs={'class': 'form-radio h-4 w-4 text-indigo-600 border-gray-300 focus:ring-indigo-500'}),
        initial='.',
        required=False,
        help_text="Use if your balance column has a different decimal format than the amount column."
    )
    date_format = forms.CharField(
        label="Date Format in CSV",
        initial="%Y-%m-%d",
        help_text="Specify the date format (e.g., %Y-%m-%d, %d/%m/%Y). <a href='https://strftime.org/' target='_blank' class='text-indigo-600 hover:underline'>strftime codes</a>.",
        widget=forms.TextInput(attrs={'class': common_input_classes, 'placeholder': '%Y-%m-%d'})
    )

class CSVImportHeaderMappingForm(forms.Form):
    def __init__(self, csv_headers, *args, **kwargs):
        super().__init__(*args, **kwargs)
        header_choices = [('', '--- Select Column ---')] + [(header, header) for header in csv_headers]
        optional_header_choices = [('', '--- Skip this field ---')] + [(header, header) for header in csv_headers]
        
        widget_attrs = {'class': common_input_classes}

        self.fields['date_column'] = forms.ChoiceField(label="Transaction Date", choices=header_choices, widget=forms.Select(attrs=widget_attrs))
        self.fields['account_column'] = forms.ChoiceField(label="Account Name", choices=header_choices, help_text="New accounts will be created if they don't exist.", widget=forms.Select(attrs=widget_attrs))
        self.fields['title_column'] = forms.ChoiceField(label="Title/Payee", choices=header_choices, widget=forms.Select(attrs=widget_attrs))
        self.fields['description_column'] = forms.ChoiceField(label="Description", choices=optional_header_choices, required=False, widget=forms.Select(attrs=widget_attrs))
        self.fields['amount_column'] = forms.ChoiceField(label="Amount", choices=header_choices, widget=forms.Select(attrs=widget_attrs))
        self.fields['category_column'] = forms.ChoiceField(label="Category Name", choices=header_choices, help_text="New categories will be created if they don't exist.", widget=forms.Select(attrs=widget_attrs))
        self.fields['balance_column'] = forms.ChoiceField(label="Balance After Transaction", choices=optional_header_choices, required=False, widget=forms.Select(attrs=widget_attrs))


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'class': common_input_classes, 'placeholder': 'e.g., Loan from Bank X'}),
        }

class LoanOperationForm(forms.ModelForm):
    class Meta:
        model = LoanOperation
        fields = ['date', 'operation_type', 'amount', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': common_input_classes}),
            'operation_type': forms.Select(attrs={'class': common_input_classes}),
            'amount': forms.NumberInput(attrs={'class': common_input_classes, 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': common_input_classes, 'placeholder': 'e.g., Monthly repayment'}),
        }


class StaffUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': common_input_classes, 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': common_input_classes, 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': common_input_classes, 'placeholder': 'Confirm Password'})

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        if commit:
            user.save()
        return user
