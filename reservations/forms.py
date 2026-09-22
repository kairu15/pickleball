from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime, time
from .models import Reservation, CancellationRequest
from courts.models import Court
from equipment.models import Equipment


MATCH_FORMAT_CHOICES = (
    ('singles', 'Singles'),
    ('doubles', 'Doubles'),
    ('mixed_doubles', 'Mixed Doubles'),
)

GAME_TYPE_CHOICES = (
    ('friendly', 'Friendly'),
    ('ranked', 'Ranked'),
    ('practice', 'Practice'),
)

SCORING_FORMAT_CHOICES = (
    ('11', '11 Points (Standard)'),
    ('15', '15 Points (Extended)'),
    ('21', '21 Points (Extended)'),
    ('best_of_3', 'Best of 3 Games'),
)


class ReservationForm(forms.ModelForm):
    equipment_items = forms.ModelMultipleChoiceField(
        queryset=Equipment.objects.filter(quantity_available__gt=0, is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    time_slot = forms.CharField(
        required=True,
        widget=forms.HiddenInput()
    )

    # Player selection fields (not saved directly to model - used via session)
    team2_player1_search = forms.CharField(required=False, widget=forms.HiddenInput())
    team1_player2_search = forms.CharField(required=False, widget=forms.HiddenInput())
    team2_player2_search = forms.CharField(required=False, widget=forms.HiddenInput())
    
    # Guest player name fields
    guest_team1_p2 = forms.CharField(required=False, widget=forms.HiddenInput())
    guest_team2_p1 = forms.CharField(required=False, widget=forms.HiddenInput())
    guest_team2_p2 = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Reservation
        fields = [
            'court', 'date', 'start_time', 'end_time', 'notes',
            'match_name', 'match_format', 'game_type', 'scoring_format',
            'points_per_game', 'games_to_win', 'win_by_two'
        ]
        widgets = {
            'court': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.HiddenInput(),
            'end_time': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Add any notes or special requests (e.g. bring your own paddle, celebration setup, or arrival instructions)...'
            }),
            'match_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Friendly Match'}),
            'match_format': forms.Select(attrs={'class': 'form-select'}, choices=MATCH_FORMAT_CHOICES),
            'game_type': forms.Select(attrs={'class': 'form-select'}, choices=GAME_TYPE_CHOICES),
            'scoring_format': forms.Select(attrs={'class': 'form-select'}, choices=SCORING_FORMAT_CHOICES),
            'points_per_game': forms.NumberInput(attrs={'class': 'form-control', 'min': 7, 'max': 21}),
            'games_to_win': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'win_by_two': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['court'].queryset = Court.objects.filter(is_active=True)
        # Make all match settings fields not required since they're set by admin
        self.fields['match_name'].required = False
        self.fields['match_format'].required = False
        self.fields['game_type'].required = False
        self.fields['scoring_format'].required = False
        self.fields['points_per_game'].required = False
        self.fields['games_to_win'].required = False
        self.fields['win_by_two'].required = False
        # start_time and end_time are populated from time_slot in clean(), not from POST data directly
        self.fields['start_time'].required = False
        self.fields['end_time'].required = False
        # Set default values
        self.fields['points_per_game'].initial = 11
        self.fields['games_to_win'].initial = 2
        self.fields['win_by_two'].initial = True
        self.fields['match_format'].initial = 'singles'
        self.fields['game_type'].initial = 'friendly'
        self.fields['scoring_format'].initial = '11'
        
        # If editing an existing reservation, pre-populate time_slot from instance
        if self.instance and self.instance.pk and self.instance.start_time and self.instance.end_time:
            self.fields['time_slot'].initial = f"{self.instance.start_time.strftime('%H:%M')}-{self.instance.end_time.strftime('%H:%M')}"
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        court = cleaned_data.get('court')
        time_slot = cleaned_data.get('time_slot')

        # Parse time_slot and set start_time and end_time
        if time_slot:
            try:
                from datetime import datetime, time as dt_time
                start_str, end_str = time_slot.split('-')
                start_hour, start_min = map(int, start_str.split(':'))
                end_hour, end_min = map(int, end_str.split(':'))
                start_time = dt_time(start_hour, start_min)
                end_time = dt_time(end_hour, end_min)
                cleaned_data['start_time'] = start_time
                cleaned_data['end_time'] = end_time
            except (ValueError, AttributeError):
                raise ValidationError("Invalid time slot selected.")

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if date and start_time and end_time:
            # Check if date is in the future
            from datetime import datetime
            selected_datetime = datetime.combine(date, start_time)
            if selected_datetime < datetime.now():
                raise ValidationError("Reservation date and time must be in the future.")

            # Check if end time is after start time
            if end_time <= start_time:
                raise ValidationError("End time must be after start time.")

            # Check minimum duration (30 minutes)
            start = datetime.combine(date, start_time)
            end = datetime.combine(date, end_time)
            duration = (end - start).total_seconds() / 60
            if duration < 30:
                raise ValidationError("Minimum reservation duration is 30 minutes.")

        if court and date and start_time and end_time:
            # Check for overlapping reservations
            overlapping = Reservation.objects.filter(
                court=court,
                date=date,
                status__in=['confirmed', 'pending']
            ).exclude(
                pk=self.instance.pk if self.instance.pk else None
            ).exclude(
                start_time__gte=end_time
            ).exclude(
                end_time__lte=start_time
            )

            if overlapping.exists():
                raise ValidationError("This court is not available for the selected time slot.")

        return cleaned_data


class ReservationApprovalForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class CancellationRequestForm(forms.ModelForm):
    REASON_CHOICES = CancellationRequest.REASON_CATEGORY_CHOICES

    reason_category = forms.ChoiceField(
        choices=REASON_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    custom_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Please specify your reason...',
            'style': 'min-height: 85px; resize: vertical; border-radius: 10px;'
        })
    )

    class Meta:
        model = CancellationRequest
        fields = ['reason', 'reason_category', 'refund_method', 'gcash_number', 'account_name', 'paypal_email']
        widgets = {
            'reason': forms.HiddenInput(),
            'refund_method': forms.RadioSelect(choices=CancellationRequest.REFUND_METHOD_CHOICES),
            'gcash_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09XXXXXXXXX'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'paypal_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reason'].required = False
        self.fields['refund_method'].required = True
        self.fields['gcash_number'].required = False
        self.fields['account_name'].required = False
        self.fields['paypal_email'].required = False

        # Pre-populate from instance if editing
        if self.instance and self.instance.pk and self.instance.reason_category:
            self.fields['reason_category'].initial = self.instance.reason_category
            if self.instance.reason_category == 'other':
                self.fields['custom_reason'].initial = self.instance.reason

    def clean(self):
        cleaned_data = super().clean()
        reason_category = cleaned_data.get('reason_category')
        custom_reason = cleaned_data.get('custom_reason', '')

        # Validate reason fields
        if reason_category:
            if reason_category == 'other':
                if not custom_reason or not custom_reason.strip():
                    self.add_error('custom_reason', 'Please provide a reason for cancellation.')
                else:
                    cleaned_data['reason'] = custom_reason.strip()
            else:
                # Store the human-readable display value of the selected choice
                reason_display = dict(self.REASON_CHOICES).get(reason_category, reason_category)
                cleaned_data['reason'] = reason_display
        else:
            self.add_error('reason_category', 'Please select a reason for cancellation.')

        # Validate refund fields
        refund_method = cleaned_data.get('refund_method')
        gcash_number = cleaned_data.get('gcash_number')
        account_name = cleaned_data.get('account_name')
        paypal_email = cleaned_data.get('paypal_email')

        if refund_method == 'gcash':
            if not gcash_number:
                self.add_error('gcash_number', 'GCash mobile number is required for GCash refunds.')
            if not account_name:
                self.add_error('account_name', 'Account name is required for GCash refunds.')

        if refund_method == 'paypal':
            if not paypal_email:
                self.add_error('paypal_email', 'PayPal email is required for PayPal refunds.')

        return cleaned_data


class AdminReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'user',
            'court',
            'date',
            'start_time',
            'end_time',
            'status',
            'hourly_rate',
            'equipment_fee',
            'notes',
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'court': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'equipment_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Add any notes or special requests (e.g. bring your own paddle, celebration setup, or arrival instructions)...'
            }),
        }

    def __init__(self, *args, **kwargs):
        from accounts.models import User
        from courts.models import Court
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(is_active=True)
        self.fields['court'].queryset = Court.objects.filter(is_active=True)
