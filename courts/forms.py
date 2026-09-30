from django import forms

from .models import Court, Site, CourtMaintenanceBlock


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ['name', 'description', 'address', 'latitude', 'longitude', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g. 14.5547'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'e.g. 121.0244'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CourtForm(forms.ModelForm):
    class Meta:
        model = Court
        fields = [
            'name',
            'site',
            'court_type',
            'status',
            'hourly_rate',
            'description',
            'image',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'site': forms.Select(attrs={'class': 'form-select'}),
            'court_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['site'].queryset = Site.objects.filter(is_active=True).order_by('name')


class MaintenanceBlockForm(forms.ModelForm):
    """Create or edit a maintenance window / closure for a court."""

    class Meta:
        model = CourtMaintenanceBlock
        fields = ['court', 'block_type', 'reason', 'start_datetime', 'end_datetime']
        widgets = {
            'start_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M',
            ),
            'end_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('start_datetime', 'end_datetime'):
            self.fields[field_name].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['court'].queryset = Court.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_datetime')
        end = cleaned.get('end_datetime')
        if start and end and end <= start:
            raise forms.ValidationError('End date/time must be after start date/time.')
        return cleaned
