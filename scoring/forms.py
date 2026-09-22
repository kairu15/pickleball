from django import forms
from accounts.models import User
from .models import Match, Game, MatchSettings


class MatchSetupForm(forms.ModelForm):
    FORMAT_CHOICES = (
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

    format = forms.ChoiceField(choices=FORMAT_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    game_type = forms.ChoiceField(choices=GAME_TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    scoring_format = forms.ChoiceField(choices=SCORING_FORMAT_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    # Team 1 player selection
    team1_player1 = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select player-select', 'data-team': '1', 'data-player': '1'}),
        label='Team 1 - Player 1'
    )
    team1_player2 = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select player-select', 'data-team': '1', 'data-player': '2'}),
        label='Team 1 - Player 2'
    )

    # Team 2 player selection
    team2_player1 = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select player-select', 'data-team': '2', 'data-player': '1'}),
        label='Team 2 - Player 1'
    )
    team2_player2 = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select player-select', 'data-team': '2', 'data-player': '2'}),
        label='Team 2 - Player 2'
    )

    # Guest player fields (populated via JS)
    guest_team1_p1 = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'class': 'guest-input', 'data-team': '1', 'data-player': '1'}))
    guest_team1_p2 = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'class': 'guest-input', 'data-team': '1', 'data-player': '2'}))
    guest_team2_p1 = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'class': 'guest-input', 'data-team': '2', 'data-player': '1'}))
    guest_team2_p2 = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'class': 'guest-input', 'data-team': '2', 'data-player': '2'}))

    # Team name fields
    team1_name = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Team 1 Name (optional)'
    }))
    team2_name = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Team 2 Name (optional)'
    }))

    class Meta:
        model = Match
        fields = ['format', 'game_type', 'scoring_format', 'games_to_win', 'points_per_game', 'win_by_two']
        widgets = {
            'games_to_win': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'points_per_game': forms.NumberInput(attrs={'class': 'form-control', 'min': 7, 'max': 21}),
            'win_by_two': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        match_format = cleaned_data.get('format')
        team1_p1 = cleaned_data.get('team1_player1')
        team1_p2 = cleaned_data.get('team1_player2')
        team2_p1 = cleaned_data.get('team2_player1')
        team2_p2 = cleaned_data.get('team2_player2')
        guest_t1_p1 = cleaned_data.get('guest_team1_p1')
        guest_t1_p2 = cleaned_data.get('guest_team1_p2')
        guest_t2_p1 = cleaned_data.get('guest_team2_p1')
        guest_t2_p2 = cleaned_data.get('guest_team2_p2')

        # Validate required players based on format
        if match_format == 'singles':
            if not team1_p1 and not guest_t1_p1:
                self.add_error('team1_player1', 'Team 1 Player 1 is required.')
            if not team2_p1 and not guest_t2_p1:
                self.add_error('team2_player1', 'Team 2 Player 1 is required.')
        elif match_format in ('doubles', 'mixed_doubles'):
            if not team1_p1 and not guest_t1_p1:
                self.add_error('team1_player1', 'Team 1 Player 1 is required.')
            if not team1_p2 and not guest_t1_p2:
                self.add_error('team1_player2', 'Team 1 Player 2 is required.')
            if not team2_p1 and not guest_t2_p1:
                self.add_error('team2_player1', 'Team 2 Player 1 is required.')
            if not team2_p2 and not guest_t2_p2:
                self.add_error('team2_player2', 'Team 2 Player 2 is required.')

        # Prevent duplicate player assignments
        selected_users = []
        for p in [team1_p1, team1_p2, team2_p1, team2_p2]:
            if p:
                if p in selected_users:
                    self.add_error(None, f'Player "{p.get_full_name() or p.username}" is assigned to multiple slots. Each player can only be in one position.')
                selected_users.append(p)

        return cleaned_data


class ScoreUpdateForm(forms.Form):
    team1_score = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={
        'class': 'form-control score-input',
        'min': 0
    }))
    team2_score = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={
        'class': 'form-control score-input',
        'min': 0
    }))


class MatchSettingsForm(forms.ModelForm):
    class Meta:
        model = MatchSettings
        fields = ['name', 'format', 'game_type', 'scoring_format', 'games_to_win', 'points_per_game', 'win_by_two', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'format': forms.Select(attrs={'class': 'form-select'}),
            'game_type': forms.Select(attrs={'class': 'form-select'}),
            'scoring_format': forms.Select(attrs={'class': 'form-select'}),
            'games_to_win': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'points_per_game': forms.NumberInput(attrs={'class': 'form-control', 'min': 7, 'max': 21}),
            'win_by_two': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
