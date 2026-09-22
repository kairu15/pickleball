from django import forms
from django.utils import timezone
from .models import Tournament, Registration, Match, Team


class TournamentForm(forms.ModelForm):
    """Form for creating and editing tournaments"""
    
    class Meta:
        model = Tournament
        fields = [
            'name', 'description', 'category', 'format', 'skill_level',
            'registration_start', 'registration_end', 'tournament_start', 'tournament_end',
            'max_participants', 'min_participants', 'players_per_group',
            'points_per_win', 'points_per_loss', 'auto_assign_teams', 'prize_pool'
        ]
        widgets = {
            'registration_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'registration_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'tournament_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'tournament_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tournament Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tournament description...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'format': forms.Select(attrs={'class': 'form-select'}),
            'skill_level': forms.Select(attrs={'class': 'form-select'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 2}),
            'min_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 2}),
            'players_per_group': forms.NumberInput(attrs={'class': 'form-control', 'min': 2}),
            'points_per_win': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'points_per_loss': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'prize_pool': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'auto_assign_teams': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate dates
        reg_start = cleaned_data.get('registration_start')
        reg_end = cleaned_data.get('registration_end')
        tourney_start = cleaned_data.get('tournament_start')
        tourney_end = cleaned_data.get('tournament_end')
        
        if reg_start and reg_end and reg_start >= reg_end:
            self.add_error('registration_end', 'Registration end must be after registration start.')
        
        if reg_end and tourney_start and reg_end >= tourney_start:
            self.add_error('tournament_start', 'Tournament start must be after registration end.')
        
        if tourney_start and tourney_end and tourney_start >= tourney_end:
            self.add_error('tournament_end', 'Tournament end must be after tournament start.')
        
        # Validate participants
        min_p = cleaned_data.get('min_participants')
        max_p = cleaned_data.get('max_participants')
        
        if min_p and max_p and min_p > max_p:
            self.add_error('max_participants', 'Max participants must be greater than min participants.')
        
        return cleaned_data


class RegistrationForm(forms.ModelForm):
    """Form for players to register for tournaments"""
    
    class Meta:
        model = Registration
        fields = ['skill_level', 'gender']
        widgets = {
            'skill_level': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
        }


class RegistrationReviewForm(forms.ModelForm):
    """Form for admin/staff to review registrations"""
    
    class Meta:
        model = Registration
        fields = ['status', 'admin_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class MatchScoreForm(forms.ModelForm):
    """Form for updating match scores"""
    
    class Meta:
        model = Match
        fields = ['score1', 'score2', 'winner', 'winner_team', 'status', 'notes']
        widgets = {
            'score1': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'score2': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'winner': forms.Select(attrs={'class': 'form-select'}),
            'winner_team': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        match = kwargs.get('instance')

        if match:
            # Limit winner choices to match participants
            if match.tournament.category == 'singles':
                from accounts.models import User
                approved_user_ids = match.tournament.registrations.filter(
                    status='approved'
                ).values_list('user_id', flat=True)
                self.fields['winner'].queryset = User.objects.filter(id__in=approved_user_ids)
                self.fields['winner_team'].widget = forms.HiddenInput()
            else:
                self.fields['winner'].widget = forms.HiddenInput()
                self.fields['winner_team'].queryset = match.tournament.teams.all()


class MatchScheduleForm(forms.ModelForm):
    """Form for scheduling matches"""
    
    class Meta:
        model = Match
        fields = ['court', 'scheduled_date', 'scheduled_time', 'duration_minutes', 'umpire']
        widgets = {
            'court': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 15}),
            'umpire': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        tournament = kwargs.pop('tournament', None)
        super().__init__(*args, **kwargs)
        
        if tournament:
            # Limit court choices to available courts
            from courts.models import Court
            self.fields['court'].queryset = Court.objects.filter(is_active=True)


class BulkScheduleForm(forms.Form):
    """Form for bulk scheduling matches"""
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Start Date"
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label="Daily Start Time"
    )
    matches_per_day = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=4,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Matches per Day"
    )
    match_duration = forms.IntegerField(
        min_value=15,
        initial=60,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Match Duration (minutes)"
    )
    court_assignment = forms.ChoiceField(
        choices=[
            ('auto', 'Auto-assign Courts'),
            ('round_robin', 'Round Robin Courts'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='auto'
    )


class TournamentStatusForm(forms.ModelForm):
    """Form for changing tournament status"""
    
    class Meta:
        model = Tournament
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class TeamForm(forms.ModelForm):
    """Form for creating/editing teams"""
    
    class Meta:
        model = Team
        fields = ['name', 'player1', 'player2', 'seed']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Team Name'}),
            'player1': forms.Select(attrs={'class': 'form-select'}),
            'player2': forms.Select(attrs={'class': 'form-select'}),
            'seed': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
    
    def __init__(self, *args, **kwargs):
        tournament = kwargs.pop('tournament', None)
        super().__init__(*args, **kwargs)

        if tournament:
            # Limit player choices to approved registrations
            from accounts.models import User
            approved_user_ids = tournament.registrations.filter(
                status='approved'
            ).values_list('user_id', flat=True)

            approved_users = User.objects.filter(id__in=approved_user_ids)

            self.fields['player1'].queryset = approved_users
            self.fields['player2'].queryset = approved_users
