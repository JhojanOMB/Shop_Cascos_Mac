# configuracion/forms.py
from django import forms
from django.conf import settings
from .tailwind_colors import TAILWIND_BG_CHOICES, TAILWIND_TEXT_CHOICES

class UISettingsForm(forms.Form):
    sidebar_bg = forms.ChoiceField(
        label='Color de fondo del menú lateral',
        choices=TAILWIND_BG_CHOICES,
        initial=settings.UI_COLORS['sidebar_bg'],
        widget=forms.Select(attrs={'class': 'mt-1 block w-full'})
    )
    sidebar_text = forms.ChoiceField(
        label='Color de texto del menú lateral',
        choices=TAILWIND_TEXT_CHOICES,
        initial=settings.UI_COLORS['sidebar_text'],
        widget=forms.Select(attrs={'class': 'mt-1 block w-full'})
    )
    sidebar_hover = forms.ChoiceField(
        label='Color de hover del menú lateral',
        choices=TAILWIND_BG_CHOICES,
        initial=settings.UI_COLORS['sidebar_hover'],
        widget=forms.Select(attrs={'class': 'mt-1 block w-full'})
    )
    navbar_bg = forms.ChoiceField(
        label='Color de fondo del navbar',
        choices=TAILWIND_BG_CHOICES,
        initial=settings.UI_COLORS['navbar_bg'],
        widget=forms.Select(attrs={'class': 'mt-1 block w-full'})
    )
    navbar_text = forms.ChoiceField(
        label='Color de texto del navbar',
        choices=TAILWIND_TEXT_CHOICES,
        initial=settings.UI_COLORS['navbar_text'],
        widget=forms.Select(attrs={'class': 'mt-1 block w-full'})
    )
